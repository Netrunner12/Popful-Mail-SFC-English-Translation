def decompress(rom, pos, maxout=0x20000):
    """Popful Mail (SFC) LZ decompressor, ported from $00:9206. Returns (data, end_pos)."""
    out = bytearray(); src = pos + 2   # 2-byte header skipped
    last_src = 0; last_len = 0
    def rd():
        nonlocal src
        b = rom[src]; src += 1; return b
    while True:
        b = rd()
        if b == 0: break
        hi = b >> 4
        if hi <= 1:                         # 01-1F literal
            out += rom[src:src+b]; src += b; last_len = b
        elif hi <= 3:                       # 20-3F long literal
            n = ((b & 0x1F) << 8) | rd()
            out += rom[src:src+n]; src += n
            if n & 1: last_len = 1
        elif hi == 4:                       # 40-4F short RLE
            n = (b & 0xF) + 4; v = rd(); out += bytes([v]) * n; last_len = n
        elif hi == 5:                       # 50-5F long RLE
            n = (((b & 0xF) << 8) | rd()) + 4; v = rd(); out += bytes([v]) * n
            last_len = n & 0xFF
        elif hi <= 7:                       # 60-7F continue previous copy
            last_src += last_len; n = b & 0x1F
            for i in range(n): out.append(out[last_src + i])
            last_len = n
        else:                               # 80-FF back-reference
            n = 4 + ((b >> 5) & 3); off = ((b & 0x1F) << 8) | rd()
            s = len(out) - off; last_src = s
            for i in range(n): out.append(out[s + i])
            last_len = n
        if len(out) > maxout: raise ValueError('too long')
    return bytes(out), src


def compress(data, header=b'\x00\x00'):
    """Compressor for the Popful Mail SFC LZ format (inverse of decompress)."""
    n = len(data); out = bytearray(header); lit = bytearray(); i = 0
    table = {}
    def flush():
        nonlocal lit
        while lit:
            if len(lit) <= 0x1F:
                out.append(len(lit)); out.extend(lit); lit = bytearray()
            else:
                k = min(len(lit), 0x1FFF)
                out.append(0x20 | (k >> 8)); out.append(k & 0xFF); out.extend(lit[:k]); lit = lit[k:]
    def find(i):
        best_len, best_off = 0, 0
        if i + 4 > n: return 0, 0
        key = bytes(data[i:i+3])
        for j in reversed(table.get(key, [])[-64:]):
            off = i - j
            if off > 0x1FFF: break
            l = 0
            while i + l < n and data[j + l] == data[i + l] and l < 0x3FF:
                l += 1
            if l > best_len: best_len, best_off = l, off
        return best_len, best_off
    def add(pos):
        if pos + 3 <= n: table.setdefault(bytes(data[pos:pos+3]), []).append(pos)
    while i < n:
        # run-length
        r = 1
        while i + r < n and data[i + r] == data[i] and r < 0xFFF + 4: r += 1
        ml, mo = find(i)
        if r >= 4 and r >= ml:
            flush()
            if r <= 19: out += bytes([0x40 | (r - 4), data[i]])
            else: k = r - 4; out += bytes([0x50 | (k >> 8), k & 0xFF, data[i]])
            for p in range(i, i + r): add(p)
            i += r; continue
        if ml >= 4:
            flush()
            first = min(ml, 7)
            out += bytes([0x80 | ((first - 4) << 5) | (mo >> 8), mo & 0xFF])
            rem = ml - first
            while rem > 0:
                c = min(rem, 0x1F); out.append(0x60 | c); rem -= c
            for p in range(i, i + ml): add(p)
            i += ml; continue
        lit.append(data[i]); add(i); i += 1
    flush(); out.append(0)
    return bytes(out)

def compress_opt(data, header=b'\x00\x00', window=512, skip_runs=False):
    """Optimal-parse version of compress() (dynamic programming over byte costs); slower, a little smaller."""
    n = len(data); INF = 1 << 30
    # longest match for every position (candidates from a 3-byte hash, up to `window` most recent)
    table = {}; best = [(0, 0)] * n
    run = [1] * (n + 1)
    for i in range(n - 2, -1, -1):
        run[i] = run[i + 1] + 1 if data[i] == data[i + 1] else 1
    for i in range(n):
        if i + 4 <= n and not (skip_runs and run[i] >= 64):   # skip_runs: no slow match search inside long runs of one byte
            key = bytes(data[i:i+3]); bl, bo = 0, 0
            for j in reversed(table.get(key, [])[-window:]):
                off = i - j
                if off > 0x1FFF: break
                l = 0
                while i + l < n and data[j + l] == data[i + l] and l < 0x3FF: l += 1
                if l > bl: bl, bo = l, off
            best[i] = (bl, bo)
        if i + 3 <= n: table.setdefault(bytes(data[i:i+3]), []).append(i)
    def mcost(l): return 2 + (max(0, l - 7) + 30) // 31
    cost = [INF] * (n + 1); cost[n] = 1; choice = [None] * (n + 1)
    for i in range(n - 1, -1, -1):
        c = INF; ch = None
        for L in range(1, min(0x1F, n - i) + 1):                 # short literal run
            v = 1 + L + cost[i + L]
            if v < c: c, ch = v, ('L', L)
        if n - i > 0x1F:                                         # long literal run (only as a fallback)
            L = min(0x1FFF, n - i); v = 2 + L + cost[i + L]
            if v < c: c, ch = v, ('L', L)
        r = min(run[i], 0xFFF + 4)
        if r >= 4:
            for L in (r,) if r > 19 else range(4, r + 1):
                v = (2 if L <= 19 else 3) + cost[i + L]
                if v < c: c, ch = v, ('R', L)
        ml, mo = best[i]
        for L in range(4, ml + 1):
            v = mcost(L) + cost[i + L]
            if v < c: c, ch = v, ('M', L, mo)
        cost[i] = c; choice[i] = ch
    out = bytearray(header); i = 0
    while i < n:
        ch = choice[i]
        if ch[0] == 'L':
            L = ch[1]
            if L <= 0x1F: out.append(L)
            else: out.append(0x20 | (L >> 8)); out.append(L & 0xFF)
            out += data[i:i+L]; i += L
        elif ch[0] == 'R':
            L = ch[1]
            if L <= 19: out += bytes([0x40 | (L - 4), data[i]])
            else: k = L - 4; out += bytes([0x50 | (k >> 8), k & 0xFF, data[i]])
            i += L
        else:
            L, mo = ch[1], ch[2]; first = min(L, 7)
            out += bytes([0x80 | ((first - 4) << 5) | (mo >> 8), mo & 0xFF])
            rem = L - first
            while rem > 0:
                c = min(rem, 0x1F); out.append(0x60 | c); rem -= c
            i += L
    out.append(0)
    return bytes(out)
