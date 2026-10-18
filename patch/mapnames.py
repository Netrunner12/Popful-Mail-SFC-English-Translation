"""World-map name bubbles: sprite frames 14-19 of stream 16#4 spell the destination names with
16x16 glyph sprites from 14#7 (4bpp, OBJ tiles at VRAM $C000).  Each frame is 11 columns x 3 rows
of 8x8 sprite tiles stored column by column (row 0 is always empty, rows 1-2 are the top and
bottom halves of the lettering).  The English names are drawn with an original proportional
pixel font into the tiles those frames used, and the frames are pointed at the new tiles."""

NAMES = ['Port Miine', 'Jungle', 'Ancient Caves', 'Gades Ruins', 'Hagel Island', 'Castle Alcazar']
FRAMES = [14, 15, 16, 17, 18, 19]          # frame index in 16#4 for each name above

# glyph rows: 10 rows; row 0 = cap top, row 7 = baseline, rows 8-9 = descender
F = {
'A': ['..##..', '.#..#.', '#....#', '#....#', '######', '#....#', '#....#', '#....#'],
'C': ['.####.', '#....#', '#.....', '#.....', '#.....', '#.....', '#....#', '.####.'],
'G': ['.####.', '#....#', '#.....', '#.....', '#..###', '#....#', '#....#', '.####.'],
'H': ['#....#', '#....#', '#....#', '######', '#....#', '#....#', '#....#', '#....#'],
'I': ['###', '.#.', '.#.', '.#.', '.#.', '.#.', '.#.', '###'],
'J': ['...###', '....#.', '....#.', '....#.', '....#.', '#...#.', '#...#.', '.###..'],
'M': ['#.....#', '##...##', '#.#.#.#', '#..#..#', '#.....#', '#.....#', '#.....#', '#.....#'],
'P': ['#####.', '#....#', '#....#', '#####.', '#.....', '#.....', '#.....', '#.....'],
'R': ['#####.', '#....#', '#....#', '#####.', '#..#..', '#...#.', '#....#', '#....#'],
'a': ['', '', '.###.', '....#', '.####', '#...#', '#...#', '.####'],
'c': ['', '', '.###.', '#...#', '#....', '#....', '#...#', '.###.'],
'd': ['....#', '....#', '.####', '#...#', '#...#', '#...#', '#...#', '.####'],
'e': ['', '', '.###.', '#...#', '#####', '#....', '#...#', '.###.'],
'g': ['', '', '.####', '#...#', '#...#', '#...#', '.####', '....#', '#...#', '.###.'],
'i': ['#', '', '#', '#', '#', '#', '#', '#'],
'l': ['#', '#', '#', '#', '#', '#', '#', '#'],
'n': ['', '', '####.', '#...#', '#...#', '#...#', '#...#', '#...#'],
'o': ['', '', '.###.', '#...#', '#...#', '#...#', '#...#', '.###.'],
'r': ['', '', '#.##', '##..', '#...', '#...', '#...', '#...'],
's': ['', '', '.####', '#....', '.###.', '....#', '....#', '####.'],
't': ['.#..', '.#..', '####', '.#..', '.#..', '.#..', '.#..', '..##'],
'u': ['', '', '#...#', '#...#', '#...#', '#...#', '#...#', '.####'],
'v': ['', '', '#...#', '#...#', '#...#', '.#.#.', '.#.#.', '..#..'],
'z': ['', '', '#####', '...#.', '..#..', '.#...', '#....', '#####'],
' ': ['...'],
}
TOP = 3                  # cap top row inside the 16-pixel cell
SHADE = [3, 3, 3, 4, 4, 4, 5, 5, 6, 6]     # body colour by glyph row (light to dark, like the original)

def render(name):
    """-> 16 x W list of colour indices"""
    cols = []
    for ch in name:
        g = F[ch]; w = max(len(r) for r in g)
        for x in range(w):
            col = [0] * 16
            for y, row in enumerate(g):
                if x < len(row) and row[x] == '#': col[TOP + y] = SHADE[y]
            cols.append(col)
        cols.append([0] * 16)                 # 1-pixel letter gap
    cols.pop()
    W = len(cols)
    img = [[cols[x][y] for x in range(W)] for y in range(16)]
    # outline like the original glyphs: colour 9 on the left of and below each stroke
    out = [[0] + row[:] for row in img]          # one extra column on the left for the edge
    W2 = W + 1
    for y in range(16):
        for x in range(W):
            if not img[y][x]: continue
            X = x + 1
            if out[y][X - 1] == 0: out[y][X - 1] = 9
            if y + 1 < 16 and out[y + 1][X] == 0: out[y + 1][X] = 9
    return out

def tile_bytes(px):      # 8x8 colour indices -> 32 bytes 4bpp
    b = bytearray(32)
    for r in range(8):
        for c in range(8):
            v = px[r][c]
            for p in range(4):
                if v >> p & 1: b[(p // 2) * 16 + 2 * r + (p & 1)] |= 0x80 >> c
    return bytes(b)

def apply(gfx, frames_stream):
    """gfx: bytearray of 14#7, frames_stream: bytearray of 16#4 (both modified in place)"""
    o = frames_stream
    w = lambda i: o[i] | o[i + 1] << 8
    nfr = w(0) // 2
    ptr = [w(2 * k) for k in range(nfr)]
    def tiles_of(k):
        p = ptr[k]; cols, rows = w(p), w(p + 2)
        if cols * rows > 400: return []
        return [w(p + 8 + 2 * i) for i in range(cols * rows)]
    mine = set(); others = set()
    for k in range(nfr):
        ts = {t & 0x1FF for t in tiles_of(k) if not t & 0x8000}
        (mine if k in FRAMES else others).update(ts)
    pool = sorted(mine - others)
    attr = {}
    for k in FRAMES:
        for t in tiles_of(k):
            if not t & 0x8000: attr.setdefault(k, t & 0xFE00)
    used = 0
    for name, k in zip(NAMES, FRAMES):
        p = ptr[k]; cols, rows = w(p), w(p + 2)
        assert (cols, rows) == (11, 3)
        img = render(name); W = len(img[0])
        assert W <= 80, (name, W)
        x0 = (80 - W) // 2
        canvas = [[0] * 80 for _ in range(16)]
        for y in range(16):
            for x in range(W): canvas[y][x0 + x] = img[y][x]
        words = [0xFFFF] * 3                                  # column 0: empty
        for c in range(10):
            col = []
            for half in (0, 1):
                px = [row[8 * c:8 * c + 8] for row in canvas[8 * half:8 * half + 8]]
                if not any(any(r) for r in px): col.append(0xFFFF); continue
                t = pool[used]; used += 1
                gfx[32 * t:32 * t + 32] = tile_bytes(px)
                col.append(attr[k] | t)
            words += [0xFFFF] + col
        for i, v in enumerate(words): o[p + 8 + 2 * i:p + 10 + 2 * i] = v.to_bytes(2, 'little')
    return used, len(pool)

if __name__ == '__main__':
    for n in NAMES:
        img = render(n); print(n, len(img[0]))
        for row in img[2:15]: print(''.join('.' if not v else ('#' if v < 9 else ('s' if v == 9 else 'h')) for v in row))
