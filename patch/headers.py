"""Shop header sprites (stream 03#1, 4bpp, tiles at 0x1800): redraw the Japanese labels in English."""
from font_en import G
DUP = (0, 3, 6)                 # rows doubled to stretch the 7-row capitals to 10 rows

def label_pixels(text, width):
    """-> 16 rows x width colour indices (0 clear, 15 outline, 7 fill, 3 light edge)"""
    rows = 16; core = [[0] * width for _ in range(rows)]
    glyph_rows = []
    for r in range(7):
        glyph_rows.append(r)
        if r in DUP: glyph_rows.append(r)
    bold = len(text) * 7 - 1 + 2 <= width
    adv = 7 if bold else 6; total = len(text) * adv - 1
    x0 = max(1, (width - total) // 2); y0 = 1
    for i, ch in enumerate(text):
        g = G[ch]
        for yy, r in enumerate(glyph_rows):
            for x in range(5):
                if g[r][x] == '#':
                    X = x0 + i * adv + x; Y = y0 + yy
                    if 0 <= X < width: core[Y][X] = 1
                    if bold and 0 <= X + 1 < width: core[Y][X + 1] = 1
    out = [[0] * width for _ in range(rows)]
    for y in range(rows):
        for x in range(width):
            if core[y][x]:
                out[y][x] = 3 if (x == 0 or not core[y][x-1]) else 7
            elif any(0 <= y+dy < rows and 0 <= x+dx < width and core[y+dy][x+dx]
                     for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                out[y][x] = 15
    return out

def put(o, tile_row, col0, pix):
    """write a 16-row pixel block into 4bpp tiles (sheet 16 tiles wide)"""
    width = len(pix[0])
    for tc in range(width // 8):
        for half in (0, 1):
            t = (tile_row + half) * 16 + col0 + tc; off = t * 32
            for y in range(8):
                p = [0, 0, 0, 0]
                for x in range(8):
                    c = pix[half * 8 + y][tc * 8 + x]
                    for k in range(4):
                        if c >> k & 1: p[k] |= 0x80 >> x
                o[off + 2*y] = p[0]; o[off + 2*y + 1] = p[1]; o[off + 16 + 2*y] = p[2]; o[off + 17 + 2*y] = p[3]

LABELS = [(12, 0, 32, 'BUY'), (12, 4, 32, 'CASH'), (12, 8, 32, 'HEAL'),
          (14, 0, 32, 'KEYS'), (14, 4, 32, 'SAVE'), (14, 8, 32, 'SPEED')]

def apply(o):
    for row, col, w, text in LABELS:
        put(o, row, col, label_pixels(text, w))
