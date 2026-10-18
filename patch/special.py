"""Streams with their own layout: title-screen character intro (1A#0), ending (1F#0), shop (17#4).
Each is rebuilt in its decompressed form and recompressed into its original slot."""
import pickle, os
from pmlz import decompress, compress, compress_opt
from build import char_code, lorom

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
STREAMS = {(s[0], s[1]): s for s in pickle.load(open(os.path.join(ROOT, 'out', 'streams.pkl'), 'rb'))}

def msgs_for(R, I, o, key):
    ids = {int(r['off'], 16): r['id'] for r in R.rows if r['sk'] == key}
    return [(a, b, ids.get(a)) for a, b, m in I.messages(o)]

def recompress_into(rom, key, o):
    s = STREAMS[key]
    c = compress(bytes(o), bytes(rom[s[2]:s[2]+2]))
    slot = s[3] - s[2]
    if len(c) > slot: c = compress_opt(bytes(o), bytes(rom[s[2]:s[2]+2]))
    if len(c) <= slot:
        rom[s[2]:s[2]+len(c)] = c
        return len(c), slot
    # does not fit: move it into the unused tail of the same bank and repoint the bank's stream table
    bank = key[0]; b0 = bank * 0x8000
    end = FREE.get(bank)
    if end is None:
        end = b0 + 0x8000
        while rom[end-1] in (0x00, 0xFF): end -= 1
        end += 16
    assert end + len(c) <= b0 + 0x8000, '%02X#%d: no room' % key
    rom[end:end+len(c)] = c
    rom[b0 + 2*key[1]:b0 + 2*key[1] + 2] = (0x8000 + end - b0).to_bytes(2, 'little')
    FREE[bank] = end + len(c)
    return len(c), slot
FREE = {}

def enc(s):
    return bytes(char_code(c) for c in s)

import re
def rewrap(t, width):
    """re-flow plain text boxes (no control tokens inside lines) to a new width"""
    out = []
    for part in re.split(r'([▼■])', t):
        if part in ('▼', '■') or not part: out.append(part); continue
        if max(len(l) for l in part.split('⏎')) <= width: out.append(part); continue
        words = part.replace('⏎', ' ').split(' ')
        lines = ['']
        for w in words:
            if not w: continue
            if lines[-1] and len(lines[-1]) + 1 + len(w) > width: lines.append(w)
            else: lines[-1] = (lines[-1] + ' ' + w) if lines[-1] else w
        out.append('⏎'.join(lines))
    return ''.join(out)

def place(rom, bank, addr, blk):
    if addr + len(blk) > 0x10000: bank += 1; addr = 0x8000
    off = lorom(bank, addr); rom[off:off+len(blk)] = blk
    return bank, addr

# ------------------------------------------------------------------ 1A#0: title intro + area names
AREAS = ['Port Miine', 'Jungle', 'Ancient Caves', 'Gades Ruins', 'Hagel Island', 'Castle Alcazar']

def do_1A0(rom, R, I, bank, addr, en):
    key = (0x1A, 0); s = STREAMS[key]
    o, _ = decompress(bytes(rom), s[2]); o = bytearray(o)
    BASE = 0x2000; TBL, N, REG = 0x1A38, 8, (0x189C, 0x1A38)
    msgs = msgs_for(R, I, bytes(o), '1A#0')
    en = dict(en)
    for a, b, mid in msgs:
        if mid and a >= 0x1888 and mid in en: en[mid] = rewrap(en[mid], 26)
    probe, _ = I.build_text_block(bytes(o), '1A#0', msgs, en, 0, base=BASE, table=TBL, n_ents=N, region=REG)
    if addr + len(probe) > 0x10000: bank += 1; addr = 0x8000
    blk, warn = I.build_text_block(bytes(o), '1A#0', msgs, en, addr, base=BASE, table=TBL, n_ents=N, region=REG)
    bank, addr = place(rom, bank, addr, blk)
    # message starter: 8B A9 7E 48 AB 8D 36 07 C2 30 8A 18 69 38 3A
    i = o.find(bytes.fromhex('8ba97e48ab8d3607c2308a1869383a'))
    assert i >= 0
    o[i+2] = bank
    o[i+13:i+15] = addr.to_bytes(2, 'little')
    # area names: rewritten into the space the intro text no longer needs (still in $7E)
    p = REG[0]; ents = []
    for name in AREAS:
        ents.append(BASE + p); b = enc(name) + b'\x20\xff'; o[p:p+len(b)] = b; p += len(b)
    o[p:REG[1]] = bytes(REG[1] - p)
    for k, v in enumerate(ents): o[0x127F + 2*k:0x127F + 2*k + 2] = v.to_bytes(2, 'little')
    o[0x1245:0x1276] = bytes(0x1276 - 0x1245)        # old JP names (unused now)
    # continue list: keep the leading zero of the minutes ("1:00", not "1: 0")
    import build as _B
    j = o.find(bytes.fromhex('ad06078f29327e')); assert j > 0
    t = _B.SYMS['MinFixTitle']
    o[j:j+7] = bytes([0x22, t & 0xFF, (t >> 8) & 0xFF, t >> 16, 0xEA, 0xEA, 0xEA])
    n, slot = recompress_into(rom, key, o)
    line = '1A#0   -> $%02X:%04X %5d bytes, stream recompressed %d/%d, %d warnings %s' % (bank, addr, len(blk), n, slot, len(warn), warn)
    return bank, addr + len(blk), line

# ------------------------------------------------------------------ 1F#0: ending
def do_1F0(rom, R, I, bank, addr, en):
    key = (0x1F, 0); s = STREAMS[key]
    o, _ = decompress(bytes(rom), s[2]); o = bytearray(o)
    BASE = 0x2000; TBL, N, REG = 0x138F, 15, (0x10ED, 0x138F)    # 15 entries: 0x0E is the closing laugh
    msgs = msgs_for(R, I, bytes(o), '1F#0')
    probe, _ = I.build_text_block(bytes(o), '1F#0', msgs, en, 0, base=BASE, table=TBL, n_ents=N, region=REG)
    if addr + len(probe) > 0x10000: bank += 1; addr = 0x8000
    blk, warn = I.build_text_block(bytes(o), '1F#0', msgs, en, addr, base=BASE, table=TBL, n_ents=N, region=REG)
    bank, addr = place(rom, bank, addr, blk)
    # starter: 8B A9 7E 8D 36 07 48 AB C2 31 8A 69 8F 33
    i = o.find(bytes.fromhex('8ba97e8d360748abc2318a698f33'))
    assert i >= 0
    o[i+2] = bank
    o[i+12:i+14] = addr.to_bytes(2, 'little')
    o[REG[0]:REG[1]] = bytes(REG[1] - REG[0])
    n, slot = recompress_into(rom, key, o)
    line = '1F#0   -> $%02X:%04X %5d bytes, stream recompressed %d/%d, %d warnings %s' % (bank, addr, len(blk), n, slot, len(warn), warn)
    return bank, addr + len(blk), line

# ------------------------------------------------------------------ 17#4: shops, save, options
def do_174(rom, R, I, bank, addr, en):
    key = (0x17, 4); s = STREAMS[key]
    o, _ = decompress(bytes(rom), s[2]); o = bytearray(o)
    BASE = 0x2000; TBL, N, REG = 0x1280, 6, (0x128C, 0x190F)
    SUB = [(0x15C3, 32), (0x186B, 26), (0x1901, 7)]          # message tables inside the region
    # message list for this stream is given explicitly (the generic splitter mis-cuts several of them)
    def menu(cells, width):
        """cells: (slot, text) -> 30-letter line with each text starting at its 16-px cell"""
        line = [' '] * 30
        for slot, t in cells:
            for k, ch in enumerate(t): line[2*slot + k] = ch
        return ''.join(line).rstrip()
    EXTRA_EN = {
        'S12B9': '⏎<18:04><1A>Will that be all right?■',
        'S1374': '<1A>Treatment will cost⏎<19>ヂ長） gold.⏎<1B><18:04><1B>Is that all right?■',
        'S1497': '§' + menu([(1, 'Buy'), (4, 'Cash'), (7, 'Heal'), (10, 'Opts'), (13, 'Exit')], 30) + '■',
        'S14AF': '§' + menu([(1, 'Keys'), (5, 'Save'), (9, 'Speed'), (13, 'Back')], 30) + '■',
        'S161B': '<1A><18:04>Anything else ya need?■',
        'S1635': '⏎<18:04><1A>That it?■',
        'S17DF': '§' + menu([(1, 'Buy'), (4, 'Cash'), (7, 'Heal'), (10, 'Opts'), (13, 'Exit')], 30) + '■',
        'S17F7': '§' + menu([(1, 'Keys'), (5, 'Save'), (9, 'Speed'), (13, 'Back')], 30) + '■',
        'S14D4': '§<1A>Set the message speed.<1B>⏎⏎' + menu([(3, 'Fast'), (7, '・'), (9, 'Normal')], 30) + '■',
        'S1820': '§<1A>Set the message speed.⏎⏎<1B>' + menu([(3, 'Fast'), (7, '・'), (9, 'Normal')], 30) + '■',
    }
    heur = {a: mid for a, b, mid in msgs_for(R, I, bytes(o), '17#4')}
    starts = sorted(set(a for a in heur if 0x128C <= a < 0x190F and a not in (0x11CC, 0x15C3, 0x186B, 0x12BE, 0x1394, 0x14B0, 0x162B, 0x163A, 0x14D4, 0x1820, 0x17F8))
                    | {0x128C, 0x1603, 0x189F, 0x12B9, 0x1374, 0x1497, 0x14AF, 0x161B, 0x1635, 0x17DF, 0x17F7, 0x14D4, 0x1820})
    ends = {0x15A7: 0x15C3, 0x185F: 0x186B, 0x18F4: 0x1901}
    en = dict(en)
    en['M1955'] = en['M1955'].replace('⟦KEEP⟧', ''); en['M1986'] = en['M1986'].replace('⟦KEEP⟧', '')
    en['M2010'] = en['M2010'].replace('⟦KEEP⟧', '')
    named = {0x128C: 'M1955', 0x1603: 'M1986', 0x189F: 'M2010'}
    msgs = []
    for i, a in enumerate(starts):
        b = ends.get(a, starts[i+1] if i + 1 < len(starts) else 0x1901)
        mid = named.get(a) or ('S%04X' % a if ('S%04X' % a) in EXTRA_EN else heur.get(a))
        msgs.append((a, b, mid))
    en.update(EXTRA_EN)
    for a, b, mid in msgs: assert mid in en, (hex(a), mid)
    extra = [q + 2*k for q, n in SUB for k in range(n)]
    probe, _ = I.build_text_block(bytes(o), '17#4', msgs, en, 0, base=BASE, table=TBL, n_ents=N, region=REG, extra_ptrs=extra)
    if addr + len(probe) > 0x10000: bank += 1; addr = 0x8000
    blk, warn = I.build_text_block(bytes(o), '17#4', msgs, en, addr, base=BASE, table=TBL, n_ents=N, region=REG, extra_ptrs=extra)
    bank, addr = place(rom, bank, addr, blk)
    # starter: 8B A9 7E 48 AB 8D 36 07 C2 30 AD 25 09 29 FF 00 0A A8 B9 80 32
    i = o.find(bytes.fromhex('8ba97e48ab8d3607c230ad250929ff000aa8b98032'))
    assert i >= 0
    o[i+2] = bank
    o[i+19:i+21] = addr.to_bytes(2, 'little')
    # save-slot names: LDA $7E3901,X
    j = o.find(bytes.fromhex('c220bf01397e8d3407e220'))
    assert j >= 0
    slot_tbl = I.LAST_MAP[0x1901]
    # the list is drawn without going through the starter, so $0736 must be set too: call a stub in bank $20
    stub = bytes([0xC2, 0x20, 0xBF, slot_tbl & 0xFF, slot_tbl >> 8, bank, 0x8D, 0x34, 0x07, 0xE2, 0x20,
                  0xA9, bank, 0x8D, 0x36, 0x07, 0x6B])
    so = lorom(0x20, 0xF000)
    assert all(b in (0, 0xFF) for b in rom[so:so+len(stub)])
    rom[so:so+len(stub)] = stub
    o[j:j+11] = bytes([0x22, 0x00, 0xF0, 0x20]) + bytes([0xEA] * 7)
    o[REG[0]:REG[1]] = bytes(REG[1] - REG[0])
    n, slot = recompress_into(rom, key, o)
    line = '17#4   -> $%02X:%04X %5d bytes, stream recompressed %d/%d, %d warnings %s' % (bank, addr, len(blk), n, slot, len(warn), warn)
    return bank, addr + len(blk), line

# ------------------------------------------------------------------ 15#7: item / equipment / skill names (8x8 menu font)
ITEMS = {0: 'SHORT SWD', 1: 'LONGSWORD', 2: 'FALCHION', 3: 'FLAME SWD', 4: 'LGT SABER',
         5: 'LEATHER', 6: 'CHAINMAIL', 7: 'PLATEMAIL', 8: 'MITHRIL', 9: 'GOLD MAIL',
         10: 'WOOD SHLD', 11: 'BUCKLER', 12: 'BIG SHLD', 13: 'MITH SHLD', 14: 'GOLD SHLD',
         16: 'FIRE L1', 17: 'ICE L1', 18: 'HOP L1', 19: 'BOMB L1',
         21: 'RED ROBE', 22: 'BLUE ROBE', 23: 'YELLOWROBE', 24: 'SILV ROBE', 25: 'GOLD ROBE',
         26: 'BRONZ MIR', 27: 'METAL MIR', 28: 'PLAT MIR', 29: 'MITH MIR', 30: 'GOLD MIR',
         32: 'FIREBALL', 33: 'GAW CHAIN', 34: 'TAILWHIP', 35: 'FIRE BRTH', 36: 'GAW BASH',
         64: 'FIRE L2', 65: 'FIRE L3', 66: 'ICE L2', 67: 'ICE L3', 68: 'HOP L2', 69: 'HOP L3',
         70: 'BOMB L2', 71: 'BOMB L3', 72: 'ORANGE', 73: 'CHERRY', 74: 'APPLE', 75: 'ELIXIR'}
for _i in range(10): ITEMS[37 + _i] = ITEMS[5 + _i]          # second copy of the armour/shield names

def small_enc(s):
    out = bytearray()
    for c in s:
        if c == ' ': out.append(0x20)
        elif c.isdigit(): out.append(0x10 + int(c))
        else: out.append(0x21 + ord(c) - ord('A'))
    return bytes(out)

def do_157(rom):
    key = (0x15, 7); s = STREAMS[key]
    o, _ = decompress(bytes(rom), s[2]); o = bytes(o)
    n = (o[0] | o[1] << 8) // 2
    ptrs = [o[2*i] | o[2*i+1] << 8 for i in range(n)]
    out = bytearray(2 * n); placed = {}; datas = {}
    for i, p in enumerate(ptrs):
        if i in ITEMS:
            datas[i] = small_enc(ITEMS[i]) + b'\x00'
        else:
            e = o.index(0, p) if p < len(o) else p
            datas[i] = o[p:e+1]
    # longest first, and a name that ends another name ("...MAIL") points into it
    for i in sorted(datas, key=lambda i: (-len(datas[i]), i)):
        data = datas[i]
        if data not in placed:
            host = next((d for d in placed if len(d) > len(data) and d.endswith(data)), None)
            if host is not None: placed[data] = placed[host] + len(host) - len(data)
            else: placed[data] = len(out); out += data
        out[2*i:2*i+2] = placed[data].to_bytes(2, 'little')
    assert len(out) <= len(o), (len(out), len(o))
    out += bytes(len(o) - len(out))
    c, slot = recompress_into(rom, key, out)
    return '15#7   item names: %d of %d bytes used, stream recompressed %d/%d' % (len(out.rstrip(b'\0')), len(o), c, slot)

# ------------------------------------------------------------------ status screen character names (menu font)
def do_names(rom):
    """names were 3-glyph strings at $00:F691/95/99 (pointer table inside stream 17#1).
    English names go to free space at $00:FF30 and the three pointers are patched in place."""
    names = [small_enc(n) + b'\x00' for n in ('MAIL', 'TATTO', 'GAW')]
    base = 0xFF30; off = base - 0x8000
    assert all(b == 0x00 for b in rom[off:off+32])          # zero padding before the header
    ptrs = []; p = base
    for b in names:
        rom[p - 0x8000:p - 0x8000 + len(b)] = b; ptrs.append(p); p += len(b)
    key = (0x17, 1); s = STREAMS[key]
    before, _ = decompress(bytes(rom), s[2])
    old = bytes.fromhex('91f695f699f6')
    i = rom.find(old, s[2], s[3]); assert i > 0
    rom[i:i+6] = b''.join(q.to_bytes(2, 'little') for q in ptrs)
    after, _ = decompress(bytes(rom), s[2])
    j = bytes(before).find(old)
    assert bytes(after[:j]) == bytes(before[:j]) and bytes(after[j+6:]) == bytes(before[j+6:])
    return 'status names -> $00:%04X, pointers patched in 17#1' % base

# ------------------------------------------------------------------ status screen name box (01#16 frame tilemap)
def do_weaponlabel(rom):
    """the status screen's equipment labels are English in the original (SWORD/ARMOR/SHIELD), but the
    same SWORD label is shown for Tatto's rods and Gaw's weapons; use the neutral WEAPON (same width)."""
    key = (0x01, 17); o, _ = decompress(bytes(rom), STREAMS[key][2]); o = bytearray(o)
    row = [o[2*(15*32+c)] for c in range(32)]
    i = bytes(row).find(small_enc('SWORD') + b'\x00\x1a')
    assert i >= 0, bytes(row).hex()
    for k, b in enumerate(small_enc('SWORD') + b'\x00\x1a'):
        o[2*(15*32+i+k)] = b; o[2*(15*32+i+k)+1] = 0x20       # all white (the space slot was yellow)
    n, slot = recompress_into(rom, key, o)
    # the label is redrawn per character (SWORD / M. ROD / ATTACK) by StatusLabel, hooked in 17#3
    key3 = (0x17, 3); o3, _ = decompress(bytes(rom), STREAMS[key3][2]); o3 = bytearray(o3)
    # STZ $0731 / LDA $0202 / ASL / ADC #$0A / STA $0730 / LDA $0736 / PHA / LDA #0 / STA $0736 /
    # LDA #4 / LDY #$31 / JSL $00F1A4  ->  LDA $0736 / PHA / JSL StatusLabel / NOP x21 (compresses smaller)
    pat = bytes.fromhex('9c3107ad02020a690a8d3007ad360748a9008d3607a904a03122a4f100')
    j = o3.find(pat); assert j > 0 and o3.count(pat) == 1
    import build as _B
    t = _B.SYMS['StatusLabel']
    o3[j:j+len(pat)] = bytes.fromhex('ad360748') + bytes([0x22, t & 0xFF, (t >> 8) & 0xFF, t >> 16]) + b'\xea' * (len(pat) - 8)
    n3, slot3 = recompress_into(rom, key3, o3)
    return '01#17  equipment label per character (row 15 white), recompressed %d/%d; 17#3 hook %d/%d' % (n, slot, n3, slot3)

def do_namebox(rom):
    """'NAME:' + a 5-letter name (TATTO) needs 10 columns; the frame box (rows 3-5, cols 11-21)
    has 9 inside.  Move its right edge from column 21 to 22 and fill column 21 with the interior."""
    key = (0x01, 16); o, _ = decompress(bytes(rom), STREAMS[key][2]); o = bytearray(o)
    def get(r, c): return o[2*(r*32+c)] | o[2*(r*32+c)+1] << 8
    def put(r, c, v): o[2*(r*32+c):2*(r*32+c)+2] = v.to_bytes(2, 'little')
    assert [get(r, 21) for r in (3, 4, 5)] == [0x440B, 0x441B, 0x442B]
    assert [get(r, 22) for r in (4, 5)] == [0x080A, 0x080A]
    for r in (3, 4, 5):
        put(r, 22, get(r, 21)); put(r, 21, get(r, 20))
    n, slot = recompress_into(rom, key, o)
    return '01#16  status name box widened by one column, recompressed %d/%d' % (n, slot)

# ------------------------------------------------------------------ status screen item counter (17#3 code)
def do_counter(rom):
    """the status screen writes the count digit to $0783 and the counter kana (menu font $93, 'ko')
    to $0784 (LDA #$93 / STA $0784 / STZ $0785).  Store a terminator instead so counts read 'ORANGE 1'."""
    key = (0x17, 3); s = STREAMS[key]
    o, _ = decompress(bytes(rom), s[2]); o = bytearray(o)
    pat = bytes.fromhex('8d8307a9938d8407')
    i = o.find(pat); assert i > 0 and o.find(pat, i + 1) < 0
    o[i + 4] = 0x00
    j = o.find(bytes.fromhex('ad06078fcd267e')); assert j > 0
    import build as _B
    t = _B.SYMS['MinFixSave']
    o[j:j+7] = bytes([0x22, t & 0xFF, (t >> 8) & 0xFF, t >> 16, 0xEA, 0xEA, 0xEA])
    n, slot = recompress_into(rom, key, o)
    return '17#3   status item counter kana removed, save-list minutes zero-padded, recompressed %d/%d' % (n, slot)

# ------------------------------------------------------------------ HUD enemy-HP label (02#0 glyphs $6D-$6E)
FOE = ['####.####.####',
       '#....#..#.#...',
       '#....#..#.#...',
       '###..#..#.###.',
       '#....#..#.#...',
       '#....#..#.#...',
       '#....####.####']
def do_hudlabel(rom):
    """the third HUD bar is labelled with two menu-font tiles ($6D,$6E: 'teki' = enemy) drawn in
    colour 2 with a colour-1 outline, like the HP/MP letters.  Redraw them as FOE."""
    key = (0x02, 0); s = STREAMS[key]
    o, _ = decompress(bytes(rom), s[2]); o = bytearray(o)
    W = 16; px = [[0] * W for _ in range(8)]
    for r, row in enumerate(FOE):
        for c, ch in enumerate(row):
            if ch == '#': px[r + 1][c + 1] = 2
    for r in range(8):
        for c in range(W):
            if px[r][c] == 0 and any(0 <= r + dr < 8 and 0 <= c + dc < W and px[r + dr][c + dc] == 2
                                     for dr in (-1, 0, 1) for dc in (-1, 0, 1)):
                px[r][c] = 1
    for t in range(2):
        b = bytearray(16)
        for r in range(8):
            for c in range(8):
                v = px[r][8 * t + c]
                b[2 * r] |= (v & 1) << (7 - c); b[2 * r + 1] |= (v >> 1) << (7 - c)
        o[(0x6D + t) * 16:(0x6E + t) * 16] = b
    n, slot = recompress_into(rom, key, o)
    return '02#0   HUD enemy label redrawn as FOE, recompressed %d/%d' % (n, slot)

# ------------------------------------------------------------------ text embedded in resident code streams
EMB_BASE = 0xF400                    # free space in bank $20 for the new strings and tables
def _patch_code(o, old, new):
    i = o.find(old); assert i >= 0 and o.find(old, i + 1) < 0, old.hex()
    o[i:i + len(old)] = new

def do_embedded(rom):
    """three strings that live inside code streams and are reached through hardcoded $7E pointers:
    13#9  'sobi shimasu ka?' prompt after receiving armour/weapons (dialogue font, $0734/$0736 = $7E:BDBD)
    17#3  Monster Card screen title (menu font via $00:F1A4, table $7E:2F46)
    17#0  dwarf contest HUD names (menu font via $00:F1A4, table $7E:28A9: MAIL / oyaji / START? / blank / PAUSE)
    Each caller now points at a copy in bank $20."""
    out = []; addr = EMB_BASE
    def put(b):
        nonlocal addr
        o = lorom(0x20, addr); assert all(x == 0 for x in rom[o:o + len(b)]), '%04X not free' % addr
        rom[o:o + len(b)] = b; a = addr; addr += len(b); return a
    # 13#9 equip prompt
    a = put(enc('Equip it?') + bytes([0x20, 0xFF]))
    key = (0x13, 9); o, _ = decompress(bytes(rom), STREAMS[key][2]); o = bytearray(o)
    _patch_code(o, bytes.fromhex('a97e8d3607a9bd8d3507a9bd8d3407'),
                bytes.fromhex('a9208d3607a9%02x8d3507a9%02x8d3407' % (a >> 8, a & 0xFF)))
    n, slot = recompress_into(rom, key, o); out.append('13#9 equip prompt %d/%d' % (n, slot))
    # 17#3 monster card title
    sa = put(small_enc('MON CARD') + b'\x00')       # 12 cells to the DEF column: MONSTER CARD runs into it
    ta = put(sa.to_bytes(2, 'little'))
    key = (0x17, 3); o, _ = decompress(bytes(rom), STREAMS[key][2]); o = bytearray(o)
    _patch_code(o, bytes.fromhex('a92f8d3307a9468d3207a97e8d3607'),
                bytes.fromhex('a9%02x8d3307a9%02x8d3207a9208d3607' % (ta >> 8, ta & 0xFF)))
    n, slot = recompress_into(rom, key, o); out.append('17#3 card title %d/%d' % (n, slot))
    # 17#0 dwarf contest names: copy the table, translating entry 1
    key = (0x17, 0); o, _ = decompress(bytes(rom), STREAMS[key][2]); o = bytearray(o)
    tab = 0x8A9; strs = []
    for i in range(5):
        p = (o[tab + 2 * i] | o[tab + 2 * i + 1] << 8) - 0x2000
        strs.append(bytes(o[p:o.index(0, p)]))
    assert strs[1] == bytes.fromhex('7d7e7f'), strs
    strs[1] = small_enc('DWARF')
    ptrs = [put(x + b'\x00') for x in strs]
    ta = put(b''.join(q.to_bytes(2, 'little') for q in ptrs))
    _patch_code(o, bytes.fromhex('a97e8d3607c220a9a9288d3207'),
                bytes.fromhex('a9208d3607c220a9%02x%02x8d3207' % (ta & 0xFF, ta >> 8)))
    # the dwarf's name is drawn at column $12, right against his hearts (col $16); 'DWARF' is
    # 5 letters, so start it at column $10 to leave a space like MAIL's
    _patch_code(o, bytes.fromhex('a012ee3007ee3007'), bytes.fromhex('a010ee3007ee3007'))
    n, slot = recompress_into(rom, key, o); out.append('17#0 contest names %d/%d' % (n, slot))
    return 'embedded text: ' + ', '.join(out) + ' (bank $20 %04X-%04X)' % (EMB_BASE, addr)

# ------------------------------------------------------------------ in-game save list area names (17#3)
def do_savelist(rom):
    """17#3 draws each save slot's area with the text engine from a pointer table at $7E:26BA
    (entries 0-5 = area names, 6 = '???????', 7 = the play-time buffer at $26CA).  The Japanese
    names are in a 58-byte gap; the English names go after the resident code 13#9 (decompressed to
    $7E:B000, free RAM from $BDD4 to the scene stream at $C000) and entries 0-5 are repointed."""
    k13 = (0x13, 9); o13, _ = decompress(bytes(rom), STREAMS[k13][2]); o13 = bytearray(o13)
    base = 0xB000 + len(o13)
    ptrs = []
    for name in AREAS:
        ptrs.append(0xB000 + len(o13)); o13 += enc(name) + b'\x20\xff'
    assert 0xB000 + len(o13) <= 0xC000
    k17 = (0x17, 3); o17, _ = decompress(bytes(rom), STREAMS[k17][2]); o17 = bytearray(o17)
    tab = 0x6BA
    old = [o17[tab + 2*i] | o17[tab + 2*i + 1] << 8 for i in range(8)]
    assert old[0] == 0x2680 and old[7] == 0x26CA, [hex(x) for x in old]
    for i, q in enumerate(ptrs): o17[tab + 2*i:tab + 2*i + 2] = q.to_bytes(2, 'little')
    # 13#9 no longer fits in bank $13: move it to bank $28 and repoint its only loader ($00:C212:
    # A9 13 85 02 A9 7E 85 05 C2 20 AF 12 80 13 = LDA #$13 / ... / LDA $138012)
    ld = 0x4212
    assert bytes(rom[ld:ld + 14]) == bytes.fromhex('a9138502a97e8505c220af128013')
    c = compress_opt(bytes(o13), bytes(rom[STREAMS[k13][2]:STREAMS[k13][2] + 2]))
    dst = lorom(0x28, 0x8002)
    assert all(b == 0 for b in rom[lorom(0x28, 0x8000):dst + len(c)])
    rom[lorom(0x28, 0x8000):lorom(0x28, 0x8000) + 2] = (0x8002).to_bytes(2, 'little')
    rom[dst:dst + len(c)] = c
    rom[ld + 1] = 0x28
    rom[ld + 10:ld + 14] = bytes([0xAF, 0x00, 0x80, 0x28])
    n2, s2 = recompress_into(rom, k17, o17)
    return 'save list names -> $7E:%04X; 13#9 moved to $28:8002 (%d bytes); 17#3 %d/%d' % (base, len(c), n2, s2)

# ------------------------------------------------------------------ world-map name bubbles (14#7 glyph sprites, 16#4 frames)
def do_mapnames(rom):
    import mapnames as M
    g, _ = decompress(bytes(rom), STREAMS[(0x14, 7)][2]); g = bytearray(g)
    f, _ = decompress(bytes(rom), STREAMS[(0x16, 4)][2]); f = bytearray(f)
    used, pool = M.apply(g, f)
    n1, s1 = recompress_into(rom, (0x14, 7), g)
    n2, s2 = recompress_into(rom, (0x16, 4), f)
    return 'map names: %d of %d glyph tiles, 14#7 %d/%d, 16#4 %d/%d' % (used, pool, n1, s1, n2, s2)

# ------------------------------------------------------------------ 03#1: shop header sprites
def do_headers(rom):
    import headers as H
    key = (0x03, 1); s = STREAMS[key]
    o, _ = decompress(bytes(rom), s[2]); o = bytearray(o)
    H.apply(o)
    n, slot = recompress_into(rom, key, o)
    return '03#1   shop header sprites redrawn, recompressed %d/%d' % (n, slot)

# ------------------------------------------------------------------ staff credits (1E#4 glyphs, 1F#1-8 pages)
def do_credits(rom):
    """The ending decompresses credit pages 1F#1..1F#9 back to back from one start pointer, so the
    rebuilt pages (bigger than the originals) go as one block into bank $27 and the loader in 1F#0
    is pointed there."""
    import credits as C
    pages = {}
    for k in range(1, 9):
        o, _ = decompress(bytes(rom), STREAMS[(0x1F, k)][2]); pages[k] = bytearray(o)
    g, _ = decompress(bytes(rom), STREAMS[(0x1E, 4)][2]); g = bytearray(g)
    nch, nfree = C.apply(pages, g)
    gi = recompress_into(rom, (0x1E, 4), g)
    BANK = 0x27; base = lorom(BANK, 0x8000)
    assert all(b == 0 for b in rom[base:base + 0x4000])
    blobs = []
    for k in range(1, 9):
        s = STREAMS[(0x1F, k)]
        blobs.append(compress_opt(bytes(pages[k]), bytes(rom[s[2]:s[2]+2])))
    s9 = STREAMS[(0x1F, 9)]; blobs.append(bytes(rom[s9[2]:s9[3]]))
    addr = 0x8000 + 2 * len(blobs); table = bytearray(); data = bytearray()
    for b in blobs:
        table += addr.to_bytes(2, 'little'); data += b; addr += len(b)
    rom[base:base + len(table) + len(data)] = table + data
    # check the chain decompresses back to the pages
    p = base + len(table)
    for k in range(1, 9):
        o, end = decompress(bytes(rom), p); assert bytes(o) == bytes(pages[k]), k; p = end
    # repoint the loader and the long-pointer list in the ending stream
    key = (0x1F, 0); s = STREAMS[key]
    o, _ = decompress(bytes(rom), s[2]); o = bytearray(o)
    i = o.find(bytes.fromhex('a91f8502c220af02801f')); assert i >= 0
    o[i+1] = BANK; o[i+6:i+10] = bytes([0xAF, 0x00, 0x80, BANK])
    for k in range(1, 9):
        pat = bytes([2*k, 0x80, 0x1F]); j = o.find(pat, 0xE00)
        while j >= 0:
            o[j:j+3] = bytes([(2*(k-1)) & 0xFF, 0x80, BANK]); j = o.find(pat, j + 3)
    recompress_into(rom, key, o)
    return 'credits: %d letters in %d freed tiles; 1E#4 %d/%d; pages -> $%02X:8000 (%d bytes)' % (
        nch, nfree, gi[0], gi[1], BANK, len(table) + len(data))

# ------------------------------------------------------------------ event code 1F#27 (loaded at $7E:E000)
def do_1F27(rom):
    """1F#27 is event code loaded at $7E:E000 (not a scene, so it gets no RAM patches) with its own
    copy of the local message starter (bank $7E hardcoded).  Used after the Hagel Island boss
    ('From somewhere, a voice rang out'): with the English text in ROM it read $7E:0000 and crashed.
    Replace the starter with JSL MsgStartX/Y, as is done for the scenes."""
    import build as _B
    key = (0x1F, 27); o, _ = decompress(bytes(rom), STREAMS[key][2]); o = bytearray(o)
    ms = list(_B.STARTER.finditer(bytes(o))); assert len(ms) == 1, len(ms)
    for m in ms:
        t = _B.SYMS['MsgStartX' if m.group(1) == b'\x8a' else 'MsgStartY']
        o[m.start():m.end()] = bytes([0x22, t & 0xFF, (t >> 8) & 0xFF, t >> 16]) + bytes([0xEA] * 20)
    n, slot = recompress_into(rom, key, o)
    return '1F#27  event-code message starter -> MsgStart, recompressed %d/%d' % (n, slot)

# ------------------------------------------------------------------ alternate title logo (English lettering)
def do_logo(rom):
    """Title logo: Mode 7 layer, 8bpp tiles in 1B#5 (256 x 64 bytes), 128x128 tile map in 1B#7 (logo on map
    rows 10-19). patch/logo_en.npy is the 256x80 colour-index picture of the English logo, in the title's own palette."""
    import numpy as np, os
    img = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_en.npy')).astype(np.uint8)
    assert img.shape == (80, 256)
    # VRAM is shared: the high bytes of tiles 0-15 double as the title menu layer's tile map (BG1 at word 0),
    # and 64 / 192 hold tile data that layer uses; those slots keep their original bytes
    SHARED = set(range(16)) | {64, 192}
    o5, _ = decompress(bytes(rom), STREAMS[(0x1B, 5)][2]); chars = bytearray(o5)
    o7, _ = decompress(bytes(rom), STREAMS[(0x1B, 7)][2]); mp = bytearray(o7)
    free = [t for t in range(256) if t not in SHARED]
    for t in free: chars[t*64:t*64+64] = bytes(64)          # old logo tiles are no longer referenced
    tiles = {bytes(64): 0}; used = 0
    for r in range(10):
        for c in range(32):
            t = bytes(img[r*8:r*8+8, c*8:c*8+8].ravel())
            if t not in tiles:
                slot = free[used]; used += 1; tiles[t] = slot; chars[slot*64:slot*64+64] = t
            mp[(10 + r) * 128 + c] = tiles[t]
    assert all(mp[r * 128 + c] == 0 for r in list(range(10)) + list(range(20, 128)) for c in range(128))
    s5 = STREAMS[(0x1B, 5)]                                   # the tiles only fit with the optimal parse
    c = compress_opt(bytes(chars), bytes(rom[s5[2]:s5[2]+2]), skip_runs=True)
    assert len(c) <= s5[3] - s5[2], '1B#5: %d > %d' % (len(c), s5[3] - s5[2])
    rom[s5[2]:s5[2]+len(c)] = c; c1 = (len(c), s5[3] - s5[2])
    c2 = recompress_into(rom, (0x1B, 7), bytes(mp))
    return 'title logo (English): %d tiles; 1B#5 %d/%d, 1B#7 %d/%d' % (used + 1, c1[0], c1[1], c2[0], c2[1])
