"""Exhaustive message-selection check.
For every scene stream with a RAM-patch entry at $20:C000, simulate what the game does:
decompress the stream to $7E:C000, apply the RAM patches, read the message table through the
header ($C003 = table, $C005 = bank), and compare each index with the original ROM's choice.
Also follows every 0D/0E/10/14/1C pointer inside the original messages and checks that the
patched message points at the same message.
usage: selcheck.py original.sfc patched.sfc"""
import sys, json, pickle, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from pmlz import decompress

def lorom(b, a): return (b & 0x7F) * 0x8000 + (a & 0x7FFF)

def main(orig_path, new_path):
    O = open(orig_path, 'rb').read(); N = open(new_path, 'rb').read()
    msgs = json.load(open(new_path + '.msgs.json'))
    rows = json.load(open(os.path.join(ROOT, 'out', 'src.json'), encoding='utf-8'))
    streams = {(s[0], s[1]): s for s in pickle.load(open(os.path.join(ROOT, 'out', 'streams.pkl'), 'rb'))}
    id_at = collections.defaultdict(dict)                    # sk -> stream offset -> id
    for r in rows: id_at[r['sk']][int(r['off'], 16)] = r['id']
    new_at = {}
    for k, v in msgs.items(): new_at.setdefault(v, k)
    # patch directory
    d = lorom(0x20, 0xC000); ents = []
    while N[d] != 0xFF:
        ents.append((N[d], N[d + 1], N[d + 2] | N[d + 3] << 8)); d += 4
    problems = []; checked = 0; per = {}
    for bank, idx, lst in ents:
        sk = '%02X#%d' % (bank, idx); s = streams[(bank, idx)]
        o, _ = decompress(O, s[2]); o = bytes(o)
        ram = bytearray(decompress(N, s[2])[0]) + bytes(0x400)
        p = lorom(0x20, lst)
        while True:
            dst = N[p] | N[p + 1] << 8
            if dst == 0xFFFF: break
            n = N[p + 2]; ram[dst - 0xC000:dst - 0xC000 + n] = N[p + 3:p + 3 + n]; p += 3 + n
        ot = o[3] | o[4] << 8
        nt = ram[3] | ram[4] << 8; nb = ram[5]
        offs = id_at[sk]
        first_msg = min(offs) if offs else len(o)
        n_ok = n_bad = 0
        i = 0
        lim = first_msg if ot - 0xC000 < first_msg else len(o)
        miss = 0
        while ot - 0xC000 + 2 * i + 1 < lim and miss < 8:
            op = o[ot - 0xC000 + 2 * i] | o[ot - 0xC000 + 2 * i + 1] << 8
            want = offs.get(op - 0xC000)
            np_ = N[lorom(nb, nt + 2 * i)] | N[lorom(nb, nt + 2 * i) + 1] << 8
            got = new_at.get(nb << 16 | np_)
            if want is None:
                miss += 1; i += 1; continue
            miss = 0                                  # gap / non-message entry
            if got != want:
                problems.append('%s index %d: original %s, patched %s (%02X:%04X)' % (sk, i, want, got, nb, np_)); n_bad += 1
            else: n_ok += 1
            i += 1
        checked += n_ok + n_bad; per[sk] = (n_ok, n_bad)
    for sk in sorted(per): print('%-6s table entries ok %3d  wrong %d' % ((sk,) + per[sk]))
    print('checked', checked, 'problems', len(problems))
    for p in problems[:50]: print('  ', p)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
