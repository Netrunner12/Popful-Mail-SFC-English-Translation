"""Headless SNES emulator for automated play-testing (snes9x libretro core, driven through ctypes).

Generic: nothing in this file knows about a particular game.

    e = SNES(rom_bytes)
    e.run(60)                    # 60 frames, no buttons
    e.run(4, ['A'])              # hold A for 4 frames
    e.tap('START')               # press and release, then wait a little
    e.wram()[0x200]              # read work RAM (128 KB)
    e.poke(0x734, b'\\x00\\x80')  # write work RAM
    e.pc()                       # current 24-bit program counter
    st = e.save(); e.load(st)    # savestates (libretro format)
    e.load_snes9x_state(path)    # a .000-.009 / .frz file from desktop snes9x (gzip or raw)
    e.set_sram(bytes)            # battery save (.srm) before boot
    with e.watch_writes(0x734, 0x737) as w: e.run(100)   # w.hits = [(addr, pc, byte), ...]
"""
import ctypes as C, gzip, os, tempfile
import numpy as np

CORE = os.environ.get('SNES_CORE', 'snes9x_libretro.so')          # snes9x libretro core built with ../snes9x_debug.patch
RUN_DIR = '/tmp/snestest'                                       # fixed in snes9x_debug.patch
os.makedirs(RUN_DIR, exist_ok=True)
WATCH_LOG = RUN_DIR + '/watch_%d.log'   # where the patched core writes watch hits (per process)
RWATCH_LOG = RUN_DIR + '/rwatch_%d.log'
BTN = {'B': 0, 'Y': 1, 'SELECT': 2, 'START': 3, 'UP': 4, 'DOWN': 5, 'LEFT': 6, 'RIGHT': 7,
       'A': 8, 'X': 9, 'L': 10, 'R': 11}

class _GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]

_ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
_VID = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
_AUD = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
_AUDB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
_POLL = C.CFUNCTYPE(None)
_INP = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class SNES:
    def __init__(self, rom_bytes, sram=None):
        L = self.lib = C.CDLL(CORE)
        self.frame = np.zeros((224, 256, 3), np.uint8)
        self.pressed = set()
        self.frames_run = 0
        sysdir = self._sysdir = C.c_char_p(os.path.dirname(WATCH_LOG).encode())

        def env(cmd, data):
            if cmd == 10: return True                                     # pixel format: RGB565 is the default
            if cmd in (9, 31): C.cast(data, C.POINTER(C.c_char_p))[0] = sysdir.value; return True
            if cmd == 3: C.cast(data, C.POINTER(C.c_bool))[0] = True; return True
            return False

        def vid(data, w, h, pitch):
            if not data: return
            a = np.frombuffer(C.string_at(data, pitch * h), dtype=np.uint16).reshape(h, pitch // 2)[:, :w]
            self.frame = np.stack([((a >> 11) & 31) << 3, ((a >> 5) & 63) << 2, (a & 31) << 3], -1).astype(np.uint8)

        self._cbs = [_ENV(env), _VID(vid), _AUD(lambda l, r: None), _AUDB(lambda d, f: f), _POLL(lambda: None),
                     _INP(lambda port, dev, idx, i: 1 if (port == 0 and i in self.pressed) else 0)]
        L.retro_set_environment(self._cbs[0]); L.retro_set_video_refresh(self._cbs[1])
        L.retro_set_audio_sample(self._cbs[2]); L.retro_set_audio_sample_batch(self._cbs[3])
        L.retro_set_input_poll(self._cbs[4]); L.retro_set_input_state(self._cbs[5])
        L.retro_init()
        self._rom = C.create_string_buffer(rom_bytes, len(rom_bytes))
        gi = _GameInfo(b'game.sfc', C.cast(self._rom, C.c_void_p), len(rom_bytes), None)
        assert L.retro_load_game(C.byref(gi)), 'core refused the ROM'
        for f in ('retro_get_memory_data', ): getattr(L, f).restype = C.c_void_p
        L.retro_get_memory_size.restype = C.c_size_t
        L.retro_serialize_size.restype = C.c_size_t
        L.retro_unserialize.restype = C.c_bool
        L.dbg_pc.restype = C.c_uint
        if sram is not None: self.set_sram(sram)

    # ---- running
    def run(self, n=1, buttons=()):
        self.pressed = {BTN[b] for b in buttons}
        for _ in range(n): self.lib.retro_run()
        self.pressed = set(); self.frames_run += n

    def tap(self, b, hold=4, after=10):
        self.run(hold, [b]); self.run(after)

    # ---- memory
    def _mem(self, kind):
        p = self.lib.retro_get_memory_data(kind); n = self.lib.retro_get_memory_size(kind)
        return p, n
    def wram(self, n=None):
        p, size = self._mem(2); return C.string_at(p, n or size)
    def vram(self):
        p, size = self._mem(3); return C.string_at(p, size)
    def poke(self, addr, data):
        p, _ = self._mem(2); data = bytes(data); C.memmove(p + addr, data, len(data))
    def sram(self):
        p, size = self._mem(0); return C.string_at(p, size)
    def set_sram(self, data):
        p, size = self._mem(0); C.memmove(p, bytes(data), min(size, len(data)))

    # ---- CPU
    def pc(self): return self.lib.dbg_pc()
    def reg(self, i): return self.lib.dbg_reg(i)          # 0 A 1 X 2 Y 3 S 4 P 5 DB 6 D

    # ---- states
    def save(self):
        n = self.lib.retro_serialize_size(); b = C.create_string_buffer(n)
        self.lib.retro_serialize(b, n); return b.raw
    def load(self, raw):
        b = C.create_string_buffer(raw, len(raw))
        if not self.lib.retro_unserialize(b, len(raw)): raise ValueError('state rejected')
    def load_snes9x_state(self, path):
        raw = open(path, 'rb').read()
        if raw[:2] == b'\x1f\x8b': raw = gzip.decompress(raw)          # desktop snes9x gzips its states
        assert raw.startswith(b'#!s9xsnp'), 'not a snes9x snapshot'
        self.load(raw); self.run(1)

    # ---- execution trace (needs the patched core): the last up-to-65536 instruction addresses
    def trace(self, on=True, valid_pc=None):
        """record executed addresses; with valid_pc, recording freezes at the first instruction in a bank
        that holds no code, so the record ends exactly where the game went off the rails"""
        if valid_pc:
            m = bytes(1 if (valid_pc(b << 16 | 0x8000) or valid_pc(b << 16 | 0x0100)) else 0 for b in range(256))
            self._valid_pc = valid_pc
            self.lib.dbg_trace_valid_banks(m)
        else:
            self.lib.dbg_trace_valid_banks(bytes([1]) * 256)
        self.lib.dbg_trace_enable(1 if on else 0)
    def trace_frozen(self): return self.lib.dbg_trace_state() == 2
    def trace_tail(self, n=4096):
        buf = (C.c_uint * n)(); k = self.lib.dbg_trace_read(buf, n); return list(buf[:k])

    # ---- watchpoints (need the patched core).  The core appends hits to a log file it keeps open,
    # so a watch remembers the file size when it starts and reads only what was added.
    class _Watch:
        def __init__(self, e, lo, hi, kind):
            self.e, self.lo, self.hi, self.kind, self.hits = e, lo, hi, kind, []
            self.log = (WATCH_LOG if kind == 'w' else RWATCH_LOG) % os.getpid()
        def _size(self): return os.path.getsize(self.log) if os.path.exists(self.log) else 0
        def __enter__(self):
            self.start = self._size()
            (self.e.lib.dbg_set_watch if self.kind == 'w' else self.e.lib.dbg_set_rwatch)(self.lo, self.hi)
            return self
        def poll(self):
            """hits added since the last poll: [(wram offset, pc, value or None)]"""
            (self.e.lib.dbg_flush if self.kind == 'w' else self.e.lib.dbg_rflush)()
            new = []
            if os.path.exists(self.log):
                with open(self.log) as f:
                    f.seek(self.start); data = f.read(); self.start += len(data)
                for line in data.splitlines():
                    p = line.split()
                    if len(p) >= 2:
                        new.append((int(p[0], 16) & 0x1FFFF, int(p[1], 16), int(p[2], 16) if len(p) > 2 else None))
            self.hits += new
            return new
        def __exit__(self, *a):
            self.poll()
            (self.e.lib.dbg_set_watch if self.kind == 'w' else self.e.lib.dbg_set_rwatch)(0xFFFFFFFF, 0)
    def watch_writes(self, lo, hi): return SNES._Watch(self, lo, hi, 'w')
    def watch_reads(self, lo, hi): return SNES._Watch(self, lo, hi, 'r')


def discover_flag(make_emu, start, enter, leave, trials=3, size=0x2000):
    """Find RAM bytes that are equal before `enter` and after `leave`, and different in between, for
    every trial.  Generic way to locate 'a menu / message / battle is active' flags.
    make_emu() -> SNES, start(e, k) prepares trial k, enter(e) / leave(e) drive the game."""
    snaps = []
    for k in range(trials):
        e = make_emu(); start(e, k)
        a = np.frombuffer(e.wram(size), np.uint8).copy(); enter(e)
        b = np.frombuffer(e.wram(size), np.uint8).copy(); leave(e)
        c = np.frombuffer(e.wram(size), np.uint8).copy(); snaps.append((a, b, c))
    return [i for i in range(size) if all(a[i] == c[i] != b[i] for a, b, c in snaps)]
