"""Popful Mail (SFC) profile for the snestest play-tester.

Everything game-specific lives here: RAM addresses, legal code banks, how to switch the active
hero, how to open an arbitrary message, the text box geometry and colours, warp points, and the
static checks of the English build.

Jobs (run by snestest.runner):
  job_message((mid, ch))           show message `mid` with hero `ch` active, page through every box
  job_explore((area, sub, ch, policy, rom_tag))   warp into an area and play with a scripted policy
  job_state((path, ch, policy))    start from a user's snes9x save state and play
"""
import os, sys, json, pickle, re, zlib, hashlib
import numpy as np
from PIL import Image

SP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))   # repo root
JP_ROM = os.environ.get('PM_ROM') or SP + '/rom/Popful Mail (Japan).sfc'
WORK = SP + '/playtest/work'
sys.path.insert(0, SP + '/playtest'); sys.path.insert(0, SP + '/tools'); sys.path.insert(0, SP + '/patch')
from snestest.emu import SNES
from snestest import detect

# ---------------------------------------------------------------- RAM map (work RAM offsets)
AREA, CHAR, PARTY, LOC = 0x200, 0x202, 0x203, 0x20A     # area 0 Port Miine .. 5 Castle Alcazar
HP = 0x490
TEXT_PTR = 0x734                                       # 3 bytes: lo, hi, bank of the text being read
MSG_OPEN = 0x652                                       # 0x20 while a message window is open, else 0
SCENE = 0x240                                          # $0240 index, $0241 bank of the loaded scene stream
WARP_SUB = 0x16FA                                      # read by the warp stub (test ROM only)
HEROES = ['Mail', 'Tatto', 'Gaw']

def valid_pc(pc):
    bank, addr = pc >> 16, pc & 0xFFFF
    if bank in (0x7E, 0x7F): return True               # overlays and scene code run from work RAM
    b = bank & 0x7F
    if b <= 0x3F: return addr >= 0x8000                  # 2 MB LoROM (this game never runs code from low RAM)
    return False

# ---------------------------------------------------------------- text box (field window)
BOX_BORDER = (17, (200, 140, 72))   # the window's top border: row, colour
def box_drawn(f):
    """a message window is on screen (the window flag is also set by boxless and closing windows; checking
    a frame without the window measured the status bar as text)"""
    y, c = BOX_BORDER
    return (np.abs(f[y].astype(int) - c).sum(1) < 30).mean() > 0.8
BOX = (8, 18, 248, 93)          # where text may be drawn: 30 letters x 8 px from x=8; name row + 3 lines
AREA_SCAN = (0, 18, 256, 93)    # where we look for text pixels (includes the frame, to catch overflow)
PALETTE = [('white', (248, 252, 248)), ('green', (0, 220, 56)), ('yellow', (232, 180, 0)),
           ('red', (248, 56, 56)), ('orange', (248, 136, 0))]
ALIGN = {'green': 'centre', 'white': 'left', 'red': 'left'}   # yellow: names (left) and item pickups (centred), not checked
IGNORE = [(234, 80, 252, 95)]      # the blinking 'more' arrow, bottom right
# font in work RAM at $7F:8000: English letters use codes $00-$87 (offsets below +$2200); anything above is
# a kana/kanji glyph, i.e. untranslated text being drawn
FOREIGN_GLYPHS = (0x18000 + 0x2200, 0x20000)
TEXT_READ_IGNORE = {0x0092F7}       # LZ decompressor: its back-references read the block it is unpacking

# ---------------------------------------------------------------- preparation (main process, once per build)
def crc(path): return '%08X' % zlib.crc32(open(path, 'rb').read())

def prepare(rom_path):
    """Build the per-build base states and message metadata; returns the init args for workers."""
    os.makedirs(WORK, exist_ok=True)
    tag = crc(rom_path); d = os.path.join(WORK, tag); os.makedirs(d, exist_ok=True)
    rom = open(rom_path, 'rb').read()
    host = os.path.join(d, 'npc_box.bin')
    if not os.path.exists(host):
        e = SNES(rom)
        for i in range(60):                                       # title, new game, intro
            e.run(50); e.tap('START' if i % 3 == 0 else 'A')
        for i in range(40): e.run(30, ['RIGHT'])
        for k in range(80): e.tap('A', 4, 56)                     # through the tavern talk, to free play
        for k in range(5): e.run(10, ['RIGHT'])                   # in front of Sisty the Mage
        e.run(20); e.run(6, ['UP']); e.run(80)
        assert e.wram()[MSG_OPEN] == 0x20, 'could not open the host conversation'
        open(host, 'wb').write(e.save())
    ent = os.path.join(d, 'entries.json')
    if not os.path.exists(ent):
        json.dump(sorted(table_entries(rom_path)), open(ent, 'w'))
    meta = os.path.join(d, 'meta.json')
    if not os.path.exists(meta):
        import importlib, io, contextlib
        cwd = os.getcwd(); os.chdir(SP)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                dr = importlib.import_module('dryrun')
        finally: os.chdir(cwd)
        M = {}
        for k, v in dr.wrapped.items():
            M[k] = {'text': v,
                    'colours': bool(re.search(r'[«»‹]|<0[012]>', v)),
                    'indent': bool(re.search(r'(^|⏎)§? +\S|<18:|⇥|〔', v)) or '<1A>' in v,
                    'branch': '<10:' in v, 'scene': dr._SK.get(k)}
        json.dump(M, open(meta, 'w'))
    return (rom_path, host, meta, d)

def table_entries(rom_path):
    """ids of messages the game starts by table index (as opposed to text reached by jumps)"""
    from pmlz import decompress
    N = open(rom_path, 'rb').read(); msgs = json.load(open(rom_path + '.msgs.json'))
    at = {}
    for k, v in msgs.items(): at.setdefault(v, k)
    lorom = lambda b, a: (b & 0x7F) * 0x8000 + (a & 0x7FFF)
    st = {(s[0], s[1]): s for s in pickle.load(open(SP + '/out/streams.pkl', 'rb'))}
    d = lorom(0x20, 0xC000); out = set()
    while N[d] != 0xFF:
        key = (N[d], N[d + 1]); lst = N[d + 2] | N[d + 3] << 8; d += 4
        ram = bytearray(decompress(N, st[key][2])[0]) + bytes(0x400); p = lorom(0x20, lst)
        while True:
            dst = N[p] | N[p + 1] << 8
            if dst == 0xFFFF: break
            n = N[p + 2]; ram[dst - 0xC000:dst - 0xC000 + n] = N[p + 3:p + 3 + n]; p += 3 + n
        t = ram[3] | ram[4] << 8; b = ram[5]
        for i in range(512):
            q = lorom(b, t + 2 * i)
            v = b << 16 | N[q] | N[q + 1] << 8
            if v in at: out.add(at[v])
    return out

# ---------------------------------------------------------------- worker state
G = {}
def init_worker(rom_path, host, meta, outdir):
    G['rom'] = open(rom_path, 'rb').read(); G['host'] = open(host, 'rb').read()
    G['meta'] = json.load(open(meta)); G['msgs'] = json.load(open(rom_path + '.msgs.json'))
    G['by_addr'] = {}
    for k, v in G['msgs'].items(): G['by_addr'].setdefault(v, k)
    G['out'] = outdir; G['e'] = SNES(G['rom']); _index_starts()
    G['entries'] = set(json.load(open(os.path.join(os.path.dirname(meta), 'entries.json'))))
    os.makedirs(os.path.join(outdir, 'shots'), exist_ok=True)

def owner(addr):
    """message whose text contains this address (nearest start at or before it, same bank)"""
    import bisect
    L = G['starts'].get(addr >> 16)
    if not L: return None
    i = bisect.bisect_right(L, (addr & 0xFFFF, '~')) - 1
    return L[i][1] if i >= 0 else None

def _index_starts():
    G['starts'] = {}
    for k, v in G['msgs'].items(): G['starts'].setdefault(v >> 16, []).append((v & 0xFFFF, k))
    for b in G['starts']: G['starts'][b].sort()

def ptr(e):
    b = e.wram(TEXT_PTR + 3)[TEXT_PTR:TEXT_PTR + 3]; return b[2] << 16 | b[1] << 8 | b[0]

def shot(e, name, crop=(0, 0, 256, 112)):
    p = os.path.join(G['out'], 'shots', name + '.png')
    Image.fromarray(e.frame).crop(crop).save(p); return p

_PAL = np.array([c for _, c in PALETTE], np.int32)
def text_mask(f):
    """which pixels of the text area are text (arrow corner excluded): stable once the text is drawn"""
    x0, y0, x1, y1 = AREA_SCAN
    a = f[y0:y1, x0:232].astype(np.int32)
    d = ((a[:, :, None, :] - _PAL[None, None]) ** 2).sum(-1).min(-1)
    return d <= 3600

def wait_stable(e, health, limit=420, still=16):
    """run until the picture stops changing (text fully drawn) or the message closes"""
    prev = None; same = 0; n = 0
    while n < limit:
        e.run(4); n += 4
        if health.sample(e, e.frames_run): return 'crash'
        small = text_mask(e.frame)
        same = same + 4 if prev is not None and np.array_equal(small, prev) else 0
        prev = small
        if e.wram(MSG_OPEN + 1)[MSG_OPEN] == 0: return 'closed'
        if same >= still: return 'stable'
    return 'timeout'

# ---------------------------------------------------------------- job: one message, one hero
def box_info(addr):
    """read the text bytes of one box from the ROM (from its first byte to the next box/end mark):
    does it indent on purpose (20 18), change colour (20 00/01/02), branch by hero (20 10, n ways)?"""
    r = G['rom']; a = addr; info = {'indent': False, 'colour': False, 'branch': None}
    lorom = lambda x: ((x >> 16) & 0x7F) * 0x8000 + (x & 0x7FFF)
    for _ in range(400):
        b = r[lorom(a)]
        if b == 0x21: a += 2; continue
        if b != 0x20: a += 1; continue
        c = r[lorom(a + 1)]
        if c in (0x0C, 0xFF, 0x0D): break
        if c == 0x18: info['indent'] = True
        if c in (0x00, 0x01, 0x02): info['colour'] = True
        if c == 0x10:
            p0 = r[lorom(a + 2)] | r[lorom(a + 3)] << 8
            info['branch'] = (p0 - ((a + 4) & 0xFFFF)) // 2 + 1; break
        if c == 0x12:
            a += 2
            while r[lorom(a)] != 0x20: a += 1
            a += 1; continue
        a += 2 + {0x13: 1, 0x18: 1, 0x11: 1, 0x1C: 4, 0x1D: 2, 0x14: 4, 0x15: 2, 0x16: 2, 0x0E: 2, 0x19: 3}.get(c, 0)
    return info

# text that only works inside its own menu code (shop / title / name entry overlays at $7E:2000):
# shown out of context it reads whatever the street scene has there, so it is not swept here
CONTEXT_ONLY = {'17#4', '1A#0', '1F#0'}
def context_only(mid, meta):
    return meta.get(mid, {}).get('scene') in CONTEXT_ONLY or mid.startswith('S')

def job_message(job):
    mid, ch = job
    e = G['e']; e.load(G['host'])
    e.poke(CHAR, [ch]); e.poke(PARTY, [3])
    a = G['msgs'][mid]; m = G['meta'].get(mid, {})
    e.poke(TEXT_PTR, [a & 0xFF, a >> 8 & 0xFF, a >> 16])
    health = detect.Health(valid_pc, bad_pc_frames=8, black_frames=400, frozen_frames=10 ** 9)
    e.trace(True, valid_pc)
    glyphs = detect.GlyphMonitor(e, FOREIGN_GLYPHS)
    issues = []; shots = {}; boxes = 0; ptrs = []
    e.run(4, ['A']); visited = []
    cur = mid; nxt = mid; start = a; nstart = a; recent = []
    for box in range(90):
        cur = nxt; start = nstart                      # message this box's text starts in (jumped-to text counts too)
        bi = box_info(start)
        if bi['branch'] and ch >= bi['branch']:
            issues.append({'kind': 'hero_not_offered', 'severity': 'info',
                           'detail': '%s branches %d ways only: %s cannot be here in a real game (box %d)' % (cur, bi['branch'], HEROES[ch], box + 1)})
            break
        if box and cur != mid and cur in G['entries']: break   # moved on to another started message: its own job
        st = wait_stable(e, health)
        if st == 'crash': break
        if st == 'closed': break
        visited.append(cur)
        m = G['meta'].get(cur, {})
        boxes += 1; ptrs.append('%06X' % ptr(e))
        iss, lines = detect.check_box(e.frame, BOX, PALETTE, lambda c: ALIGN.get(c), area=AREA_SCAN, ignore=IGNORE,
                                      allow_mixed=bi['colour'] or m.get('colours', False),
                                      allow_indent=bi['indent'] or (box == 0 and m.get('indent', False)),
                                      max_lines=4)
        if iss:
            name = '%s_%s_b%d' % (mid, HEROES[ch], box + 1)
            p = shot(e, name)
            for i in iss: i['shot'] = p; i['detail'] += ' (box %d%s)' % (box + 1, '' if cur == mid else ', text of ' + cur)
            issues += iss; shots[name] = p
        if st == 'timeout':
            issues.append({'kind': 'never_settles', 'severity': 'medium', 'detail': 'box %d kept changing for 7 s' % (box + 1)})
        glyphs.poll(e, e.frames_run, lambda e_: shot(e_, '%s_%s_jptext' % (mid, HEROES[ch])))
        nstart = ptr(e); nxt = owner(nstart) or cur    # while waiting, the pointer sits at the next box's first byte
        recent = (recent + [nstart])[-4:]
        if len(recent) == 4 and len(set(recent)) == 1:
            issues.append({'kind': 'stuck', 'severity': 'high', 'detail': 'text stopped advancing at %06X (box %d)' % (nstart, box + 1),
                           'shot': shot(e, '%s_%s_stuck' % (mid, HEROES[ch]))}); break
        e.run(4, ['A'])
    else:
        issues.append({'kind': 'very_long', 'severity': 'info', 'detail': 'still going after 90 boxes'})
    for i in health.issues:
        i['shot'] = shot(e, '%s_%s_%s' % (mid, HEROES[ch], i['kind'])); issues.append(i)
    glyphs.close(); issues += glyphs.issues
    return {'job': job, 'title': '%s as %s (%s)' % (mid, HEROES[ch], m.get('scene')), 'issues': issues,
            'shots': shots, 'boxes': boxes, 'visited': visited}

# ---------------------------------------------------------------- job: warp into an area and play
POLICIES = {
    'walk': lambda t: (['RIGHT'] if (t // 2400) % 2 == 0 else ['LEFT']) + (['Y'] if t % 12 < 3 else []) + (['B'] if t % 200 in range(100, 104) else []) + (['UP'] if t % 240 in range(150, 156) else []) + (['A'] if t % 30 < 3 else []),
    'talk': lambda t: (['UP'] if t % 90 < 4 else []) + (['A'] if t % 20 < 3 else []) + (['RIGHT'] if t % 400 < 40 else []) + (['LEFT'] if 200 <= t % 400 < 240 else []),
    'menu': lambda t: (['START'] if t % 600 == 0 else []) + (['L'] if t % 600 == 60 else []) + (['R'] if t % 600 in (200, 320) else []) + (['START'] if t % 600 in (450, 520) else []) + (['RIGHT', 'Y'] if 530 <= t % 600 < 590 else []),
}

def location_exists(e):
    """is what the warp loaded a real place?  Scene code starts with a JMP, and the scene dispatches on the
    location number through a table (LDA $020A : ASL : TAX : JMP ($tttt,X)); an entry outside the scene's
    code means the scene has no such location (13#0 has 8: a warp to 'location 8' jumped to $0620)"""
    m = e.wram(0x10000)
    if m[0xC000] != 0x4C: return False
    k = m.find(bytes([0xAD, 0x0A, 0x02, 0x0A, 0xAA, 0x7C]), 0xC000, 0xC100)
    if k < 0: return True
    tab = m[k + 6] | m[k + 7] << 8; n = m[0x20A]
    return 0xC000 <= (m[tab + 2 * n] | m[tab + 2 * n + 1] << 8)

def job_explore(job):
    area, sub, ch, policy, frames, rom_key = job
    e = SNES(G['roms'][rom_key])
    e.load(G['world'])
    o13 = G['13#9'][rom_key]; e.poke(0xB000, o13)
    if rom_key == 'en': e.poke(0x769, bytes.fromhex('30ff35ff3bff'))
    if G.get('save_block'): e.poke(0x200, G['save_block'])
    e.poke(AREA, [area]); e.poke(WARP_SUB, [sub + 1]); e.poke(CHAR, [ch]); e.poke(PARTY, [3]); e.run(2)
    e.run(4, ['START'])
    health = detect.Health(valid_pc, bad_pc_frames=20, black_frames=900, frozen_frames=1800)
    pol = POLICIES[policy]; seen = []; issues = []; shots = {}; last = None; pending = []
    e.trace(True, valid_pc); scene_prev = None; loaded = None
    glyphs = detect.TextReadMonitor(e, text_region, ignore_pcs=TEXT_READ_IGNORE, judge=reads_as_text) if (rom_key == 'en' or os.environ.get('PM_MONITOR_JP')) else None
    for t in range(frames):
        e.run(1, pol(t))
        if glyphs and t % 30 == 0:
            glyphs.poll(e, t, lambda e_: shot(e_, 'ex_%d_%d_%s_%s_jptext' % (area, sub, HEROES[ch], policy), (0, 0, 256, 224)))
        if t % 30 == 0: e.poke(HP, [99])
        w = e.wram(0x800)
        if rom_key == 'en' and (w[0x241], w[0x240]) != loaded and t > 2:
            # the base state was saved by an older build: when the warp lands in the scene that was already
            # in RAM, the game does not reload it and the old build's message-table address stays (a false
            # 'crash' after the Port Miine dwarf contest, 2026-10-17)
            loaded = (w[0x241], w[0x240]); refresh_ram_code(e)
        if w[LOC] != scene_prev or t == 90:         # a location was entered (or the warp target settled): real?
            scene_prev = w[LOC]
            if t > 2 and not location_exists(e) and e.wram(0x400)[0x241] != 0:
                issues.append({'kind': 'invalid_location', 'severity': 'info',
                               'detail': 'location %d in %02X#%d does not exist (warp artefact; the game never goes here)'
                                         % (w[LOC], w[0x241], w[0x240])})
                break
        if health.sample(e, t): break
        a = ptr(e)
        if a != last and a in G['by_addr']:
            seen.append(G['by_addr'][a]); pending.append((t + 120, G['by_addr'][a]))
        last = a
        while pending and pending[0][0] <= t:
            _, mid = pending.pop(0)
            if e.wram(MSG_OPEN + 1)[MSG_OPEN] and rom_key == 'en' and not context_only(mid, G['meta']) and box_drawn(e.frame):
                m = G['meta'].get(mid, {})
                iss, _ = detect.check_box(e.frame, BOX, PALETTE, lambda c: ALIGN.get(c), area=AREA_SCAN, ignore=IGNORE, allow_mixed=m.get('colours', False),
                                          allow_indent=m.get('indent', False), max_lines=4)
                if iss:
                    p = shot(e, 'ex_%d_%d_%s_%s_%s' % (area, sub, HEROES[ch], policy, mid))
                    for i in iss: i['shot'] = p; i['detail'] = mid + ': ' + i['detail']
                    issues += iss
    for i in health.issues:
        i['shot'] = shot(e, 'ex_%d_%d_%s_%s_%s_%s' % (area, sub, HEROES[ch], policy, rom_key, i['kind']), (0, 0, 256, 224)); issues.append(i)
    if glyphs: glyphs.close(); issues += glyphs.issues
    sc = e.wram(0x242)
    return {'job': job, 'title': 'area %d/%d as %s, %s (%s ROM)' % (area, sub, HEROES[ch], policy, rom_key),
            'issues': issues, 'shots': shots, 'messages': seen, 'scene': '%02X#%d' % (sc[0x241], sc[0x240])}

def init_explore(rom_path, meta, outdir, save_srm=None):
    """worker init for exploration: needs warp builds of the English and the original ROM"""
    from pmlz import decompress
    G['meta'] = json.load(open(meta)); G['msgs'] = json.load(open(rom_path + '.msgs.json'))
    G['by_addr'] = {}
    for k, v in G['msgs'].items(): G['by_addr'].setdefault(v, k)
    G['out'] = outdir; os.makedirs(os.path.join(outdir, 'shots'), exist_ok=True); _index_starts()
    G['roms'] = {'en': make_warp(open(rom_path, 'rb').read()), 'jp': make_warp(open(JP_ROM, 'rb').read() + bytes(0x100000))}
    G['13#9'] = {}
    for k, r in G['roms'].items():
        src = 0x28 * 0x8000 + 2 if r[0x4213] == 0x28 else 0x09E4CD
        G['13#9'][k] = bytes(decompress(r, src)[0])
    G['world'] = open(os.environ.get('PM_WORLD_STATE', os.path.join(WORK, 'world_state.bin')), 'rb').read()   # an in-game state made with the emulator wrapper (see README)
    G['rom'] = G['roms']['en']                 # refresh_ram_code() brings the base state's RAM blocks up to this build
    G['save_block'] = open(save_srm, 'rb').read()[0:0x3D7] if save_srm else None

def make_warp(rom):
    """test-only ROM: location loads take the sub-area from $16FA, and the hero can jump in mid-air"""
    r = bytearray(rom)
    o = 0x20 * 0x8000 + (0xF300 - 0x8000)
    stub = bytes.fromhex('adfa16f0073a8d0a029cfa16daae00025c278c00')
    assert all(b == 0 for b in r[o:o + len(stub)]); r[o:o + len(stub)] = stub
    assert r[0x0C23:0x0C27] == bytes.fromhex('daae0002'); r[0x0C23:0x0C27] = bytes.fromhex('5c00f320')
    r[0x334A] = 0x00
    return bytes(r)

# ---------------------------------------------------------------- job: user's save state
# code that lives in work RAM, loaded from the ROM at some earlier point: a save state made with an
# older build still carries the old copy, so refresh it from the ROM under test
RAM_CODE = [(0xE000, (0x1F, 27)), (0xB000, (0x13, 9))]

def refresh_ram_code(e):
    from pmlz import decompress
    st = {(s[0], s[1]): s for s in pickle.load(open(SP + '/out/streams.pkl', 'rb'))}
    jp = open(JP_ROM, 'rb').read(); w = e.wram(); done = []
    for addr, key in RAM_CODE:
        if key == (0x13, 9):
            src = 0x28 * 0x8000 + 2 if G['rom'][0x4213] == 0x28 else 0x09E4CD
            new = bytes(decompress(G['rom'], src)[0]); old = bytes(decompress(jp, 0x09E4CD)[0])
        else:
            new = bytes(decompress(G['rom'], st[key][2])[0]); old = bytes(decompress(jp, st[key][2])[0])
        here = w[addr:addr + len(new)]
        if here != new and here[:0x40] in (old[:0x40], new[:0x40]):      # same block, older build
            e.poke(addr, new); done.append('%02X#%d' % key)
    # the loaded scene's RAM patches (message-table address etc.) come from the build that made the state:
    # re-apply this build's patch list for that scene
    R = G['rom']; lorom = lambda b, a: (b & 0x7F) * 0x8000 + (a & 0x7FFF)
    key = (w[0x241], w[0x240]); d = lorom(0x20, 0xC000)
    while R[d] != 0xFF:
        if (R[d], R[d + 1]) == key:
            p = lorom(0x20, R[d + 2] | R[d + 3] << 8)
            while True:
                dst = R[p] | R[p + 1] << 8
                if dst == 0xFFFF: break
                n = R[p + 2]; e.poke(dst, R[p + 3:p + 3 + n]); p += 3 + n
            done.append('scene %02X#%d patches' % key); break
        d += 4
    return done

def job_state(job):
    path, ch, policy, frames = job
    e = SNES(G['rom']); e.load_snes9x_state(path)
    refreshed = refresh_ram_code(e); e.trace(True, valid_pc)
    glyphs = detect.TextReadMonitor(e, text_region, ignore_pcs=TEXT_READ_IGNORE, judge=reads_as_text)
    if ch is not None: e.poke(CHAR, [ch])
    health = detect.Health(valid_pc, bad_pc_frames=20, black_frames=900, frozen_frames=1800)
    pol = POLICIES[policy]; seen = []; last = None; issues = []
    for t in range(frames):
        e.run(1, pol(t))
        if health.sample(e, t): break
        if t % 30 == 0:
            glyphs.poll(e, t, lambda e_: shot(e_, 'st_%s_%s_%s_jptext' % (os.path.basename(path), ch, policy), (0, 0, 256, 224)))
        a = ptr(e)
        if a != last and a in G['by_addr']: seen.append(G['by_addr'][a])
        last = a
    for i in health.issues:
        i['shot'] = shot(e, 'st_%s_%s_%s_%s' % (os.path.basename(path), ch, policy, i['kind']), (0, 0, 256, 224)); issues.append(i)
    glyphs.close(); issues += glyphs.issues
    return {'job': job, 'title': '%s as %s, %s' % (os.path.basename(path), HEROES[ch] if ch is not None else 'saved hero', policy),
            'issues': issues, 'messages': seen, 'refreshed': refreshed}

def init_state(rom_path, meta, outdir):
    G['rom'] = open(rom_path, 'rb').read(); G['meta'] = json.load(open(meta))
    G['msgs'] = json.load(open(rom_path + '.msgs.json')); G['by_addr'] = {}
    for k, v in G['msgs'].items(): G['by_addr'].setdefault(v, k)
    G['out'] = outdir; os.makedirs(os.path.join(outdir, 'shots'), exist_ok=True)

# ---------------------------------------------------------------- static checks of the build
STARTER = re.compile(rb'\x8b\xa9\x7e\x48\xab\x8d\x36\x07\xc2\x31([\x8a\x98])\x6d\x03\xc0\xaa\xbd\x00\x00\x8d\x34\x07\xe2\x30\xab')

def static_checks(rom_path):
    """code-level checks that need no emulation: unpatched copies of the message starter in any
    compressed stream (the Hagel Island crash class), plus the existing text checkers."""
    import subprocess
    from pmlz import decompress
    N = open(rom_path, 'rb').read()
    streams = pickle.load(open(SP + '/out/streams.pkl', 'rb'))
    lorom = lambda b, a: (b & 0x7F) * 0x8000 + (a & 0x7FFF)
    d = lorom(0x20, 0xC000); patched = {}
    while N[d] != 0xFF: patched[(N[d], N[d + 1])] = N[d + 2] | N[d + 3] << 8; d += 4
    issues = []
    for s in streams:
        key = (s[0], s[1])
        try: ram = bytearray(decompress(N, s[2])[0])
        except Exception: continue
        if key in patched:
            p = lorom(0x20, patched[key])
            while True:
                dst = N[p] | N[p + 1] << 8
                if dst == 0xFFFF: break
                n = N[p + 2]; ram[dst - 0xC000:dst - 0xC000 + n] = N[p + 3:p + 3 + n]; p += 3 + n
        for m in STARTER.finditer(bytes(ram)):
            if key == (0x13, 9): continue                  # resident copy: patched at build time, not by this table
            issues.append({'kind': 'unpatched_code', 'severity': 'high',
                           'detail': 'stream %02X#%d +%04X still reads message text from the Japanese location' % (key[0], key[1], m.start())})
    issues += direct_text_reads()
    issues += text_not_in_script()
    out = []
    for cmd in (['python3', SP + '/tools/verify.py', rom_path],
                ['python3', SP + '/tools/selcheck.py', JP_ROM, rom_path],
                ['python3', SP + '/tools/ptrcheck.py', JP_ROM, rom_path, 'flow']):
        r = subprocess.run(cmd, capture_output=True, text=True); out.append(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:])
        if 'verify' in cmd[1]:
            for line in r.stdout.splitlines()[:-1]:
                if line.startswith('M0114 '): continue        # known, harmless (data after the message)
                issues.append({'kind': 'static_text', 'severity': 'medium', 'detail': line})
    return {'job': 'static', 'title': 'static checks', 'issues': issues, 'summary': out}


# code that reads the original text bytes itself (a text "walker": LDA text,X followed by INX), instead of
# going through the message pointer the translation redirects: the story scroll in 17#7 was one.
KNOWN_WALKERS = {('17#7', 0xCC37), ('17#7', 0xCC43), ('17#7', 0xCC57)}   # replaced by ScrollLine (engine.asm)

def direct_text_reads():
    from pmlz import decompress
    import bisect, collections
    O = open(JP_ROM, 'rb').read()
    rows = json.load(open(SP + '/out/src.json', encoding='utf-8'))
    by = collections.defaultdict(list)
    for r in rows: by[r['sk']].append((int(r['off'], 16), r['id']))
    issues = []
    for s in pickle.load(open(SP + '/out/streams.pkl', 'rb')):
        sk = '%02X#%d' % (s[0], s[1])
        if sk not in by: continue
        try: o = bytes(decompress(O, s[2])[0])
        except Exception: continue
        L = sorted(by[sk]); first = L[0][0]; starts = [x[0] for x in L]
        base = 0x2000 if sk in CONTEXT_ONLY else 0xC000
        for i in range(max(0, min(first, len(o)) - 4)):
            op = o[i]
            if op in (0xBD, 0xB9):  n = 3                     # LDA abs,X / abs,Y
            elif op == 0xBF and o[i + 3] == 0x7E: n = 4       # LDA $7Exxxx,X
            else: continue
            a = o[i + 1] | o[i + 2] << 8; off = a - base
            if not (first <= off < len(o)): continue
            if o[i + n] not in (0xE8, 0xC8): continue          # followed by INX / INY: walks through the text
            if sk in CONTEXT_ONLY: continue                    # menu overlays: their text is translated in place
            j = bisect.bisect_right(starts, off) - 1
            known = (sk, base + i) in KNOWN_WALKERS
            issues.append({'kind': 'direct_text_read', 'severity': 'info' if known else 'high',
                           'detail': '%s code at %04X walks the original text at $%04X (inside %s)%s'
                                     % (sk, base + i, a, L[j][1], ' - handled' if known else '')})
    return issues


# ---- where the original text sits in RAM right now (for detect.TextReadMonitor)
_TEXT_RANGES = None
def text_region(e):
    """the loaded scene's original-text area at $7E:C000+ (from out/src.json), or None"""
    global _TEXT_RANGES
    if _TEXT_RANGES is None:
        import collections
        rows = json.load(open(SP + '/out/src.json', encoding='utf-8')); d = collections.defaultdict(list)
        for r in rows: d[r['sk']].append(int(r['off'], 16))
        _TEXT_RANGES = {k: (0xC000 + min(v), 0xC000 + max(v) + 0x80) for k, v in d.items() if k not in CONTEXT_ONLY}
    w = e.wram(0x250)
    sk = '%02X#%d' % (w[0x241], w[0x240])
    r = _TEXT_RANGES.get(sk)
    if not r: return None
    # only once that scene's block is really in RAM (the scene number changes before it is unpacked)
    orig = _scene_bytes(sk); mem = e.wram(0x10000); lo, hi = r[0], min(r[1], 0x10000)
    probe = range(lo, hi, max(1, (hi - lo) // 64))
    same = sum(1 for a in probe if a - 0xC000 < len(orig) and mem[a] == orig[a - 0xC000])
    return (lo, hi, 'scene ' + sk) if same >= 0.7 * len(probe) else None

_SCENES = {}
def _scene_bytes(sk):
    if sk not in _SCENES:
        from pmlz import decompress
        st = {'%02X#%d' % (s[0], s[1]): s for s in pickle.load(open(SP + '/out/streams.pkl', 'rb'))}
        _SCENES[sk] = bytes(decompress(open(JP_ROM, 'rb').read(), st[sk][2])[0])
    return _SCENES[sk]


# ---- original text that is not in the script at all (a display nobody extracted)
def _text_model():
    """(runs, model): the game's decoder and a model of the script, built once"""
    if 'text_model' in G: return G['text_model']
    import re
    from snestest import textscan
    T = {}; exec(open(SP + '/tools/table.py', encoding='utf-8').read(), T); S, D = T['S'], T['D']
    def runs(b):
        i = 0; cur = ''; st = 0
        while i < len(b):
            x = b[i]
            if x == 0x20 and i + 1 < len(b):
                if b[i + 1] in (0xFF, 0x0C): yield st, i + 2, cur; cur = ''; st = i + 2
                i += 2; continue
            if x == 0x21 and i + 1 < len(b) and b[i + 1] in D: cur += D[b[i + 1]]; i += 2; continue
            if x in S: cur += S[x]; i += 1; continue
            if cur: yield st, i, cur
            cur = ''; i += 1; st = i
        if cur: yield st, i, cur
    nat = lambda c: '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff'
    corpus = [re.sub(r'<[^>]*>|[⏎▼■⏸{}\[\]【】〔〕]', '', r['jp'])
              for r in json.load(open(SP + '/out/src.json', encoding='utf-8'))]
    clean = [t for t, r in zip(corpus, json.load(open(SP + '/out/src.json', encoding='utf-8'))) if not r.get('junk')]
    G['text_model'] = (runs, textscan.Model(clean, nat, known=corpus))
    return G['text_model']

def reads_as_text(b):
    """bytes some code read: do they decode to a phrase that reads like the script?"""
    runs, model = _text_model()
    for s, e, t in runs(b):
        core = [c for c in t if model.nat(c)]
        if len(core) >= 4 and model.score(t) >= model.thresh: return True
    return False

def text_not_in_script():
    import re
    from pmlz import decompress
    from snestest import textscan
    runs, model = _text_model()
    covered = {}                                       # script messages and extra messages: (stream, start, end)
    for m in json.load(open(SP + '/out/messages2.json', encoding='utf-8')):
        covered.setdefault('%02X#%d' % (m['bank'], m['idx']), []).append((m['off'], m['end']))
    for line in open(SP + '/patch/extra_msgs.tsv', encoding='utf-8'):
        f = line.rstrip('\n').split('\t')
        if len(f) >= 3 and not line.startswith('#'): covered.setdefault(f[0], []).append((int(f[1], 16), int(f[2], 16)))
    O = open(JP_ROM, 'rb').read(); blocks = []; packed = []
    for st in pickle.load(open(SP + '/out/streams.pkl', 'rb')):
        try: blocks.append(('%02X#%d' % (st[0], st[1]), bytes(decompress(O, st[2])[0])))
        except Exception: continue
        packed.append(st[2])
    blocks.append(('ROM', O))
    hits = textscan.scan(blocks, runs, model)
    issues = []
    for name, s, e, t, sc in hits:
        if any(a <= s < b or a < e <= b for a, b in covered.get(name, [])): continue
        # raw-ROM hits inside a compressed block are the block's literal bytes, already scanned unpacked
        if name == 'ROM' and any(0 <= s - p < 0x8000 for p in packed): continue
        issues.append({'kind': 'text_not_in_script', 'severity': 'high',
                       'detail': '%s %04X-%04X reads like original text but is not in the script: %s' % (name, s, e, t[:40])})
    return issues
