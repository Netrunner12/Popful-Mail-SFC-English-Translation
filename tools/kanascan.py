"""Find tiles in any stream that look like the game's own Japanese glyphs (dialogue font tiles and
menu-font kana), as a hint of Japanese text drawn into graphics."""
import sys, pickle, json, collections
import numpy as np
sys.path.insert(0, 'tools')
from pmlz import decompress
rom = open(sys.argv[1], 'rb').read()
S = pickle.load(open('out/streams.pkl', 'rb'))
def tiles(o, bpp):
    sz = 8 * bpp; n = len(o) // sz
    out = np.zeros((n, 8, 8), np.uint8)
    a = np.frombuffer(o[:n * sz], np.uint8).reshape(n, sz)
    for p in range(bpp):
        base = (p // 2) * 16; sh = p % 2
        rows = a[:, base + sh:base + 16:2]
        for c in range(8): out[:, :, c] |= ((rows >> (7 - c)) & 1).astype(np.uint8) << p
    return out
def bits(m): return np.packbits(m.reshape(-1, 64), axis=1).view('>u8').ravel()
ref = []
f = open('out/font_page0.bin', 'rb').read(); t = tiles(f, 2)
ref += [m for m in (t != 0)]
o, _ = decompress(rom, [s for s in S if (s[0], s[1]) == (2, 0)][0][2]); t = tiles(bytes(o), 2)
ref += [m for m in (t[0x80:] != 0)]
R = np.array([m for m in ref if 10 <= m.sum() <= 40])
Rb = bits(R)
Rb = np.unique(Rb)
print('reference glyph tiles', len(Rb), file=sys.stderr)
pc = np.array([bin(i).count('1') for i in range(256)], np.uint8)
def ham(a, B):
    x = np.bitwise_xor(a, B)
    return pc[x.view(np.uint8).reshape(-1, 8)].sum(1)
res = {}
set_ = set(Rb.tolist())
for s in S:
    key = '%02X#%d' % (s[0], s[1])
    if key in ('02#0',): continue
    try: o, _ = decompress(rom, s[2]); o = bytes(o)
    except Exception: continue
    best = collections.Counter()
    for bpp in (2, 4):
        t = tiles(o, bpp)
        for i, tt in enumerate(t):
            cols = set(np.unique(tt)) - {0}
            masks = [tt != 0] + ([tt == v for v in cols] if len(cols) > 1 else [])
            for m in masks:
                if not 10 <= m.sum() <= 40: continue
                mb = bits(m[None])[0]
                if int(mb) in set_: best[(bpp, 'exact')] += 1; break
                if ham(np.array([mb], '>u8'), Rb).min() <= 2: best[(bpp, 'near')] += 1; break
    if best: res[key] = dict((('%dbpp-%s' % k), v) for k, v in best.items())
for k in sorted(res, key=lambda k: -sum(res[k].values())): print(k, res[k])
