import sys, os, subprocess, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from pmlz import decompress, compress
from font_en import cell, G, logo_cells
import shutil
ASAR = os.environ.get('ASAR') or shutil.which('asar') or 'asar'          # Asar 1.91 (github.com/RPGHacker/asar)
SRC = os.environ.get('PM_ROM') or os.path.join(HERE, '..', 'rom', 'Popful Mail (Japan).sfc')

def lorom(bank, addr): return bank * 0x8000 + (addr & 0x7FFF)

# English character -> byte code (ASCII, but space/! moved off the control codes)
def char_code(ch):
    if ch == ' ': return 0x00
    if ch == '!': return 0x01
    if ch == '・': return 0x80
    if ch == '―': return 0x81
    if ch == '♪': return 0x82
    if ch == '◐': return 0x83          # Blacky's brand mark, left half
    if ch == '◑': return 0x84          # right half
    if ch in '—–': return ord('-')
    if ch in '‘’': return ord("'")
    if ch in '“”': return ord('"')
    o = ord(ch)
    if 0x22 <= o <= 0x7E: return o
    raise KeyError(ch)

def tile_bytes(rows8):        # 8 rows of 8 values (0-3) -> 16 bytes 2bpp planar
    out = bytearray()
    for r in rows8:
        p0 = p1 = 0
        for x, v in enumerate(r):
            p0 |= (v & 1) << (7 - x); p1 |= ((v >> 1) & 1) << (7 - x)
        out += bytes([p0, p1])
    return bytes(out)

def build_font(rom):
    font, _ = decompress(rom, 0x075F1D)
    font = bytearray(font)
    def put(code, ch):
        c = cell(ch)
        o = ((code & 0xF8) << 6) | ((code & 7) << 5)
        font[o:o+16] = tile_bytes(c[0:8])
        font[o+0x100:o+0x110] = tile_bytes(c[8:16])
        # blank the right column so stray halves never show
        font[o+16:o+32] = bytes(16); font[o+0x110:o+0x120] = bytes(16)
    for ch in G:
        try: put(char_code(ch), ch)
        except KeyError: pass
    for d in range(10): put(0x10 + d, str(d))     # digits used by the number printer
    for code, c in zip((0x83, 0x84), logo_cells()):
        o = ((code & 0xF8) << 6) | ((code & 7) << 5)
        font[o:o+16] = tile_bytes(c[0:8]); font[o+0x100:o+0x110] = tile_bytes(c[8:16])
        font[o+16:o+32] = bytes(16); font[o+0x110:o+0x120] = bytes(16)
    return bytes(font)

def main(out_path):
    rom = bytearray(open(SRC, 'rb').read())
    rom += bytes(0x200000 - len(rom))             # 2 MB LoROM
    rom[0x7FD7] = 0x0B
    open(out_path, 'wb').write(rom)
    sym = out_path + '.sym'
    r = subprocess.run([ASAR, '--symbols=wla', '--symbols-path=' + sym, os.path.join(HERE, 'engine.asm'), out_path],
                       capture_output=True, text=True)
    if r.returncode: print(r.stdout, r.stderr); raise SystemExit('asar failed')
    syms = {}
    for line in open(sym):
        m = re.match(r'([0-9a-fA-F]{2}):([0-9a-fA-F]{4}) (\S+)', line.strip())
        if m: syms[m.group(3)] = (int(m.group(1), 16) << 16) | int(m.group(2), 16)
    rom = bytearray(open(out_path, 'rb').read())

    # --- font -> $21:8002 (pointer word at $21:8000)
    font_c = compress(build_font(bytes(rom)), rom[0x075F1D:0x075F1F])
    base = lorom(0x21, 0x8000)
    rom[base:base+2] = (0x8002).to_bytes(2, 'little'); rom[base+2:base+2+len(font_c)] = font_c
    assert rom[0xC2CB-0x8000+0] == 0xA9 and rom[0xC2CB-0x8000+1] == 0x0E
    rom[0x42CC] = 0x21                                     # LDA #$0E -> #$21
    assert rom[0x42D1:0x42D5] == bytes.fromhex('af12800e')
    rom[0x42D1:0x42D5] = bytes.fromhex('af008021')         # LDA $0E8012 -> $218000

    # --- resident text code 13#9: message starter -> JSL MsgStart
    o, end = decompress(bytes(rom), 0x09E4CD); o = bytearray(o)
    assert o[0x37:0x37+10] == bytes.fromhex('0aaa8ba97e48ab8d3607')
    ms = syms['MsgStart']
    o[0x37:0x51] = bytes([0x22, ms & 0xFF, (ms >> 8) & 0xFF, ms >> 16]) + bytes([0xEA] * 22)
    c = compress(bytes(o), rom[0x09E4CD:0x09E4CF])
    slot = end - 0x09E4CD
    print('13#9 recompressed %d bytes (slot %d)' % (len(c), slot))
    assert len(c) <= slot, '13#9 does not fit'
    rom[0x09E4CD:0x09E4CD+len(c)] = c
    open(out_path, 'wb').write(rom)
    return syms

if __name__ == '__main__':
    print({k: hex(v) for k, v in main(sys.argv[1]).items()})


STARTER = re.compile(rb'\x8b\xa9\x7e\x48\xab\x8d\x36\x07\xc2\x31([\x8a\x98])\x6d\x03\xc0\xaa\xbd\x00\x00\x8d\x34\x07\xe2\x30\xab')

def ram_patches(o, bank, addr, syms):
    """list of (offset_in_stream, bytes) applied in WRAM after the stream is decompressed"""
    P = [(3, bytes([addr & 0xFF, addr >> 8, bank]))]
    for m in STARTER.finditer(o):
        tgt = syms['MsgStartX' if m.group(1) == b'\x8a' else 'MsgStartY']
        P.append((m.start(), bytes([0x22, tgt & 0xFF, (tgt >> 8) & 0xFF, tgt >> 16]) + bytes([0xEA] * 20)))
    # starter with the table address hardcoded: 8B A9 7E 8D 36 07 48 AB BD lo hi 8D 34 07 BD lo+1 hi 8D 35 07
    t = (o[3] | o[4] << 8)
    pat = bytes([0x8B, 0xA9, 0x7E, 0x8D, 0x36, 0x07, 0x48, 0xAB, 0xBD, t & 0xFF, t >> 8, 0x8D, 0x34, 0x07,
                 0xBD, (t + 1) & 0xFF, (t + 1) >> 8, 0x8D, 0x35, 0x07])
    k = o.find(pat)
    while k >= 0:
        P.append((k + 2, bytes([bank])))
        P.append((k + 9, bytes([addr & 0xFF, addr >> 8])))
        P.append((k + 15, bytes([(addr + 1) & 0xFF, (addr + 1) >> 8])))
        k = o.find(pat, k + 1)
    return P

SCROLL_COLS = 30               # letters across the story scroll (8px each; lines start at x=8, like the original)

def scroll_patches(rom, syms, wrapped):
    """Castle Alcazar story scroll (17#7): write the English text (M2118) to $28:D000 and return the RAM
    patches that copy ScrollLine over the unused Japanese text and jump to it from $CC30."""
    t = wrapped['M2118'].lstrip('§').rstrip('■▼')
    data = bytearray()
    for line in t.split('⏎'):
        line = line.strip()
        assert len(line) <= 30, line
        pad = SCROLL_COLS - len(line)                              # centred, like the original's indents;
        lead = (pad + (line[-1] in '.,!?\'"')) // 2               # odd padding rounds right after narrow punctuation
        line = ' ' * lead + line
        data += bytes(char_code(c) for c in line) + b'\xfe'
    data[-1] = 0xFF
    o = lorom(0x28, 0xD000); assert not any(rom[o + 1:o + len(data) + 16])
    rom[o:o + len(data)] = data
    a, b = syms['ScrollLine'], syms['ScrollEnd']
    assert a == 0x7ED800 and b - a < 0x1A6E - 0x1800, hex(b - a)
    code = bytes(rom[lorom(0x28, 0xC000):lorom(0x28, 0xC000) + (b - a)])
    P = [(0x0C30, bytes([0x4C, 0x00, 0xD8]))]
    for k in range(0, len(code), 200):
        P.append((0x1800 + k, code[k:k + 200]))
    return P

# text blocks padded to the size they had in a release, so the blocks after them do not move: emulator
# save states keep the address of the loaded scene's text, and a shift would break them (v0.17: the
# loose-wall line got shorter after the release; states for the ending were made with that release)
KEEP_SIZE = {'17#7': 5157, '05#5': 5728, '05#1': 4430, '13#0': 7189}

PATCH_DIR = 0xC000           # $20:C000
MSGADDR = {}

SYMS = {}
def insert_all(out_path, syms):
    SYMS.update(syms)
    """Insert English text blocks for every standard scene stream (run after main())."""
    import dryrun as R, insert as I
    rom = bytearray(open(out_path, 'rb').read())
    bank, addr = 0x22, 0x8000
    report = []; dir_ents = []; lists = bytearray()
    for s, key, o, msgs in R.stream_jobs():
        blk, warn = I.build_text_block(o, key, msgs, R.wrapped, 0)          # size probe
        if addr + len(blk) > 0x10000: bank += 1; addr = 0x8000
        blk, warn = I.build_text_block(o, key, msgs, R.wrapped, addr)
        if key in KEEP_SIZE and len(blk) < KEEP_SIZE[key]:   # keep later blocks where released save states expect them
            blk = blk + bytes(KEEP_SIZE[key] - len(blk))
        off = lorom(bank, addr); rom[off:off+len(blk)] = blk
        P = ram_patches(o, bank, addr, syms)
        if key == '17#7':                              # story scroll: English line builder over the JP text
            P += scroll_patches(rom, syms, R.wrapped)
        if os.environ.get('PM_TEST_SHOP') and key == '13#0':      # test only: town 'closed' doors open Basso's shop
            P.append((0x421, b'\x4c\x33\xc4'))
        if os.environ.get('PM_TEST_END') and key == '13#0':       # test only: the 'empty house' door starts the ending
            P.append((0x421, b'\x5c\x00\xf1\x20'))
            stub = bytes.fromhex('a9808d62099c1202a91f8502a97e8505c220af00801f8500a9002085' '03e220' '22ea9100' '5c00207e')
            so = lorom(0x20, 0xF100); rom[so:so+len(stub)] = stub
        for k, v in I.LAST_MSGS.items(): MSGADDR[k] = (bank << 16) | v
        dir_ents.append((s[0], s[1], len(lists)))
        for at, b in P:
            lists += (0xC000 + at).to_bytes(2, 'little') + bytes([len(b)]) + b
        lists += b'\xff\xff'
        report.append('%-6s -> $%02X:%04X %5d bytes, %d RAM patches, %d warnings' % (key, bank, addr, len(blk), len(P), len(warn)))
        addr += len(blk)
    import special as SP
    for fn in (SP.do_1A0, SP.do_1F0, SP.do_174):
        bank, addr, line = fn(rom, R, I, bank, addr, R.wrapped); report.append(line)
        for k, v in I.LAST_MSGS.items(): MSGADDR[k] = (bank << 16) | v
    report.append(SP.do_157(rom))
    report.append(SP.do_names(rom))
    report.append(SP.do_namebox(rom))
    report.append(SP.do_weaponlabel(rom))
    report.append(SP.do_counter(rom))
    report.append(SP.do_1F27(rom))
    report.append(SP.do_hudlabel(rom))
    report.append(SP.do_embedded(rom))
    report.append(SP.do_savelist(rom))
    report.append(SP.do_mapnames(rom))
    report.append(SP.do_headers(rom))
    report.append(SP.do_credits(rom))
    if os.environ.get('PM_LOGO') == 'en':                      # alternate release: English title lettering
        report.append(SP.do_logo(rom))
    import json
    json.dump({k: v for k, v in MSGADDR.items() if k}, open(out_path + '.msgs.json', 'w'))
    base = PATCH_DIR + 4 * len(dir_ents) + 1
    d = bytearray()
    for b_, i_, rel in dir_ents: d += bytes([b_, i_]) + (base + rel).to_bytes(2, 'little')
    d += b'\xff'
    blob = d + lists
    assert PATCH_DIR + len(blob) <= 0x10000
    assert syms['SceneLoad'] < 0x20C000
    o0 = lorom(0x20, PATCH_DIR); rom[o0:o0+len(blob)] = blob
    open(out_path, 'wb').write(rom)
    return report
