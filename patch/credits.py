"""Staff credits: replace the kanji name graphics with romanized names (given name first).
Pages are 32x32 tilemaps in streams 1F#1..1F#8; glyph tiles (2bpp) in stream 1E#4."""
from font_en import G

# (page, top row) -> name.  Readings marked * could not be confirmed from a published source.
NAMES = {
    (1, 4): 'Jun Mizushima', (1, 22): 'Hideyuki Shiota', (1, 29): 'Jun Mizushima',
    (2, 2): 'Mayuko Suzuki', (2, 18): 'Yuichi Shiota', (2, 23): 'Mayuko Suzuki', (2, 28): 'Norihiro Sawada',
    (3, 1): 'Kazuo Nakamura', (3, 6): 'Yuichi Takashita', (3, 30): 'Mieko Ishikawa',
    (4, 3): 'Atsushi Shirakawa', (4, 8): 'Hirofumi Matsuoka', (4, 13): 'Takahiro Tsunashima',   # *
    (4, 18): 'Masaru Nakajima', (4, 23): 'Naoki Kaneda',                                         # *
    (5, 8): 'Yoshinobu Nakahara', (5, 20): 'Noriyoshi Akiba', (5, 24): 'Toshikuni Matsumae',     # *
    (5, 28): 'Tadashi Hayakawa',                                                                 # *
    (6, 9): 'Yoshio Kiya', (6, 14): 'Shinji Yamazaki',
    (7, 0): 'Masayuki Kato',
    (8, 10): 'POPFUL MAIL',
}
BLANK = 0x2037
# SCENARIO: the original spaces its three names 7 and 5 rows apart; every other group uses 5
MOVE = {(1, 29): (1, 27), (2, 2): (2, 0)}
STRETCH = (0, 2, 4, 6)          # glyph rows drawn twice: 9 rows -> 13 rows

def glyph16(ch):
    """8x16 cell, colours: 3 outline, 1 upper stroke, 2 lower stroke (matches the kanji)"""
    core = [[0] * 8 for _ in range(16)]
    rows = []
    for r in range(9):
        rows.append(r)
        if r in STRETCH: rows.append(r)
    g = G[ch]
    for yy, r in enumerate(rows):
        for x in range(5):
            if g[r][x] == '#': core[1 + yy][1 + x] = 1
    out = [[0] * 8 for _ in range(16)]
    for y in range(16):
        for x in range(8):
            if core[y][x]: out[y][x] = 1 if y < 8 else 2
            elif any(0 <= y + dy < 16 and 0 <= x + dx < 8 and core[y + dy][x + dx]
                     for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                out[y][x] = 3
    return out

def tile_bytes(px):
    b = bytearray(16)
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            lo |= (px[y][x] & 1) << (7 - x); hi |= (px[y][x] >> 1 & 1) << (7 - x)
        b[2*y] = lo; b[2*y+1] = hi
    return bytes(b)

def apply(pages, glyphs):
    """pages: dict k -> bytearray tilemap (1024 words); glyphs: bytearray 1E#4"""
    import struct
    W = {k: list(struct.unpack('<1024H', bytes(v))) for k, v in pages.items()}
    replaced = set(); used_elsewhere = set()
    cells = {}
    for (k, r), name in NAMES.items():
        for rr in (r, r + 1):
            row = W[k][rr*32:rr*32+32]
            cs = [c for c in range(32) if row[c] != BLANK and (row[c] >> 10 & 7) == 0]
            cells[(k, rr)] = cs
            for c in cs: replaced.add(row[c] & 0x3FF)
    for k in W:
        for i, w in enumerate(W[k]):
            r, c = divmod(i, 32)
            mine = any((k, r) == key and c in cs for key, cs in cells.items())
            if not mine: used_elsewhere.add(w & 0x3FF)
    free = sorted(replaced - used_elsewhere)
    chars = sorted(set(''.join(NAMES.values()).replace(' ', '')))
    assert 2 * len(chars) <= len(free), (len(chars), len(free))
    alloc = {}
    for i, ch in enumerate(chars):
        t, b = free[2*i], free[2*i+1]
        g = glyph16(ch)
        glyphs[t*16:t*16+16] = tile_bytes(g[:8]); glyphs[b*16:b*16+16] = tile_bytes(g[8:])
        alloc[ch] = (t, b)
    for (k, r), name in NAMES.items():
        c0 = min(cells[(k, r)])
        old = set(cells[(k, r)]) | set(cells[(k, r + 1)])
        for c in old: W[k][r*32+c] = BLANK; W[k][(r+1)*32+c] = BLANK
        if name == 'POPFUL MAIL': c0 = (32 - len(name)) // 2
        assert c0 + len(name) <= 32, name
        k2, r2 = MOVE.get((k, r), (k, r))
        for i, ch in enumerate(name):
            if ch == ' ': continue
            t, b = alloc[ch]
            W[k2][r2*32 + c0 + i] = 0x2000 | t; W[k2][(r2+1)*32 + c0 + i] = 0x2000 | b
    retitle(W, glyphs, free[2 * len(chars):])
    for k in W: pages[k][:] = struct.pack('<1024H', *W[k])
    return len(chars), len(free)

# ---- headings are the original English artwork (italic outlined letters). DIRECT and PRODUCE are
# re-spelled DIRECTION / PRODUCTION with letters cut from the existing headings.  The letters touch, so
# each is cut out between two slanted lines: (x at the top row, x at the bottom row), relative to the
# heading's leftmost pixel.
# letters taken whole (they stand apart from their neighbours): letter -> (page, heading row, x of the
# letter's leftmost pixel relative to the heading's)
SOURCES = {'N': (8, 16, 0), 'I': (8, 16, 10), 'O': (1, 18, 56), 'T': (5, 16, 65)}   # NIHON, SCENARIO, THANKS
# letters whose fill stands apart though their outline touches the neighbour: (page, row, x of the fill)
FILL_SOURCES = {'M': (1, 0, 49)}          # the M of PROGRAM
# letters fused to both neighbours: cut out row by row, columns [left, right) relative to the heading;
# the outline is then closed where the cut went through a shared edge
CUT_SOURCES = {
    'G': (1, 0, [26, 26, 25, 25, 25, 25, 25, 25, 25, 25, 24, 24, 24, 25, 25, 25],      # PROGRAM
                [33, 33, 33, 33, 33, 33, 34, 34, 34, 33, 33, 33, 33, 33, 32, 32]),
}
# PRODUCE: the E touches the C; pixels from this column on (per row, relative) are the E and go
TRIM = {(6, 28): [49] * 6 + [48] * 6 + [49, 46, 48, 48]}
HEADINGS = {(6, 5): 'ION', (6, 28): 'TION', (2, 14): 'S',    # letters appended (ART & GRAPHIC -> GRAPHICS)
            (1, 0): 'MING'}                                   # PROGRAM -> PROGRAMMING
# drawn in the headings' style (2-px strokes, white over lavender with a dithered middle, 1-px orange
# outline, italic slant): the S of GRAPHICS (chosen over the S cut from SCENARIO)
DRAWN = {'S': ['  ####  ', ' ###### ', '###  ###', '##    ##', '###     ', ' ####   ', '  ####  ',
               '    ### ', '     ###', '##    ##', '###  ###', ' ###### ', '  ####  ']}

def _drawn(core):
    px = {}
    for i, row in enumerate(core):
        y = 2 + i; sh = round((14 - y) / 3)
        for x, ch in enumerate(row):
            if ch == '#':
                v = 1 if y < 8 else 2 if y > 10 else (1 if (x + y) % 2 else 2)
                px[(y, x + sh + 1)] = v
    for (y, x) in list(px):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                q = (y + dy, x + dx)
                if q not in px and 0 <= q[0] < 16: px[q] = 3
    m = min(x for _, x in px)
    return {(y, x - m): v for (y, x), v in px.items()}

def _px(glyphs, w):
    t = w & 0x3FF; b = glyphs[t*16:t*16+16]; hf = w >> 14 & 1; vf = w >> 15 & 1
    px = [[((b[2*y] >> (7 - x)) & 1) | (((b[2*y+1] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(8)]
    if vf: px = px[::-1]
    if hf: px = [row[::-1] for row in px]
    return px

def _heading(W, glyphs, k, r):
    """bitmap 16 x 256 of the heading on rows r, r+1, its cells, its tile attribute and leftmost pixel"""
    bm = [[0] * 256 for _ in range(16)]; cells = []; attr = None
    for rr in (r, r + 1):
        for c in range(32):
            w = W[k][rr*32+c]
            if w == BLANK: continue                      # (the last column of a heading can use palette 0)
            cells.append((rr, c)); attr = attr or (w & 0x3C00)
            px = _px(glyphs, w)
            for y in range(8):
                for x in range(8): bm[(rr - r) * 8 + y][c * 8 + x] = px[y][x]
    x0 = min(x for y in range(16) for x in range(256) if bm[y][x])
    return bm, cells, attr, x0

def _components(bm):
    seen = set(); out = []
    for y in range(16):
        for x in range(256):
            if bm[y][x] and (y, x) not in seen:
                st = [(y, x)]; seen.add((y, x)); c = set()
                while st:
                    a, b = st.pop(); c.add((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        q = (a + da, b + db)
                        if 0 <= q[0] < 16 and 0 <= q[1] < 256 and bm[q[0]][q[1]] and q not in seen:
                            seen.add(q); st.append(q)
                out.append(c)
    return out

def retitle(W, glyphs, free):
    shapes = {}
    for ch, (k, r, dx) in SOURCES.items():
        bm, _, _, x0 = _heading(W, glyphs, k, r)
        comp = next(c for c in _components(bm) if min(x for _, x in c) == x0 + dx)
        a = x0 + dx; shapes[ch] = {(y, x - a): bm[y][x] for y, x in comp}
    for ch, core in DRAWN.items(): shapes[ch] = _drawn(core)
    for ch, (k, r, L, R) in CUT_SOURCES.items():
        bm, _, _, x0 = _heading(W, glyphs, k, r)
        px = {(y, x): bm[y][x0 + x] for y in range(16) for x in range(L[y], R[y]) if bm[y][x0 + x]}
        for (y, x), v in list(px.items()):
            if v in (1, 2):
                for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    q = (y + dy, x + dx)
                    if 0 <= q[0] < 16 and q not in px: px[q] = 3
        a = min(x for _, x in px); shapes[ch] = {(y, x - a): v for (y, x), v in px.items()}
    for ch, (k, r, dx) in FILL_SOURCES.items():
        bm, _, _, x0 = _heading(W, glyphs, k, r)
        fill = [[v if v in (1, 2) else 0 for v in row] for row in bm]
        comp = next(c for c in _components(fill) if min(x for _, x in c) == x0 + dx)
        px = {(y, x): bm[y][x] for y, x in comp}
        for (y, x) in list(comp):                     # with its outline
            for dy in (-1, 0, 1):
                for ddx in (-1, 0, 1):
                    q = (y + dy, x + ddx)
                    if 0 <= q[0] < 16 and q not in px and bm[q[0]][q[1]] == 3: px[q] = 3
        a = min(x for _, x in px); shapes[ch] = {(y, x - a): v for (y, x), v in px.items()}
    pool = list(free); made = {}
    for key, extra in HEADINGS.items():
        k, r = key
        bm, cells, attr, x0 = _heading(W, glyphs, k, r)
        if key in TRIM:
            for y in range(16):
                for x in range(x0 + TRIM[key][y], 256): bm[y][x] = 0
        for rr, c in cells: W[k][rr*32+c] = BLANK
        for ch in extra:
            # fit the letter against the heading row by row (italic letters overlap column-wise): the
            # closest rows touch outline to outline, as the original letters do
            sh = shapes[ch]; x = 0
            for y in range(16):
                right = [xx for xx in range(256) if bm[y][xx]]; left = [dx for (yy, dx) in sh if yy == y]
                if right and left: x = max(x, right[-1] - min(left))
            for (y, dx), v in sh.items():
                if v and (bm[y][x + dx] in (0, 3) or v != 3): bm[y][x + dx] = v
            x += max(dx for (_, dx) in sh) + 1
        assert x < 256, key
        for rr in (0, 1):
            for c in range(x0 // 8, (x + 7) // 8):
                px = [row[c*8:c*8+8] for row in bm[rr*8:rr*8+8]]
                if not any(any(row) for row in px): continue
                tb = tile_bytes(px)
                if tb not in made:
                    t = pool.pop(0); glyphs[t*16:t*16+16] = tb; made[tb] = t
                W[k][(r + rr)*32 + c] = attr | made[tb]
