"""Check every in-message pointer (20 0D jump, 20 0E substring call, 20 10 branch, 20 14 / 20 1C
conditional) of every scene message: the patched message must point into the same message
(identified by the containing message ID) as the original, in the same order.
usage: ptrcheck.py original.sfc patched.sfc"""
import sys, json, pickle, os, bisect, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from pmlz import decompress
ARGS = {0x13: 1, 0x18: 1, 0x11: 1, 0x1C: 4, 0x1D: 2, 0x14: 4, 0x15: 2, 0x16: 2, 0x0E: 2, 0x0D: 2, 0x19: 3}
def lorom(b, a): return (b & 0x7F) * 0x8000 + (a & 0x7FFF)

def walk(read, a, end):
    """yield (cmd, [targets]) for pointer commands between a and end; read(addr) -> byte"""
    out = []
    while a < end:
        b = read(a)
        if b == 0x21: a += 2; continue
        if b != 0x20: a += 1; continue
        c = read(a + 1)
        if c in (0xFF, 0x17): break                   # end of message / return from substring
        if c == 0x12:
            j = a + 2
            while read(j) != 0x20 and j < a + 40: j += 1
            a = j + 1; continue
        if c == 0x10:
            p0 = read(a + 2) | read(a + 3) << 8
            n = (p0 - ((a + 4) & 0xFFFF)) // 2 + 1
            if not 1 <= n <= 4: out.append((0x10, ['?bad'])); a += 2; continue
            out.append((0x10, [read(a + 2 + 2*k) | read(a + 3 + 2*k) << 8 for k in range(n)]))
            break                                     # control continues at the variants
        if c == 0x0D:
            out.append((c, [read(a + 2) | read(a + 3) << 8])); break
        if c == 0x0E:
            out.append((c, [read(a + 2) | read(a + 3) << 8])); a += 4; continue
        if c in (0x14, 0x1C):
            out.append((c, [read(a + 4) | read(a + 5) << 8])); a += 6; continue
        a += 2 + ARGS.get(c, 0)
    return out

def main(op, np_):
    O = open(op, 'rb').read(); N = open(np_, 'rb').read()
    msgs = json.load(open(np_ + '.msgs.json'))
    rows = json.load(open(os.path.join(ROOT, 'out', 'src.json'), encoding='utf-8'))
    streams = {(s[0], s[1]): s for s in pickle.load(open(os.path.join(ROOT, 'out', 'streams.pkl'), 'rb'))}
    by_sk = collections.defaultdict(list)
    for r in rows: by_sk[r['sk']].append((int(r['off'], 16), r['id']))
    new_by_bank = collections.defaultdict(list)
    for k, v in msgs.items(): new_by_bank[v >> 16].append((v & 0xFFFF, k))
    for b in new_by_bank: new_by_bank[b].sort()
    def new_owner(bank, addr):
        L = new_by_bank[bank]; i = bisect.bisect_right(L, (addr, '~')) - 1
        return L[i][1] if i >= 0 else None
    problems = []; n_ptr = 0; n_msg = 0
    fwd = collections.defaultdict(set); rev = collections.defaultdict(set)
    for sk, lst in sorted(by_sk.items()):
        b, i = sk.split('#'); key = (int(b, 16), int(i))
        if key not in streams: continue
        o, _ = decompress(O, streams[key][2]); o = bytes(o)
        base = 0xC000 if key not in ((0x1A, 0), (0x1F, 0), (0x17, 4)) else 0x2000
        lst.sort(); starts = [x[0] for x in lst]; start_id = {x[0]: x[1] for x in lst}
        def orig_owner(off):
            j = bisect.bisect_right(starts, off) - 1
            return lst[j][1] if j >= 0 else None
        for j, (off, mid) in enumerate(lst):
            end = starts[j + 1] if j + 1 < len(starts) else len(o)
            ow = walk(lambda a: o[a - base] if 0 <= a - base < len(o) else 0, base + off, base + end)
            if mid not in msgs: continue
            na = msgs[mid]; bank = na >> 16
            L = new_by_bank[bank]; k = bisect.bisect_right(L, (na & 0xFFFF, mid))
            nend = L[k][0] if k < len(L) else (na & 0xFFFF) + 2000
            # the English block may contain the message's own label defs after it; walk to next start
            nw = walk(lambda a: N[lorom(bank, a)], na & 0xFFFF, nend)
            n_msg += 1
            ow = [x for x in ow if x[0] != 0x0E]; nw = [x for x in nw if x[0] != 0x0E]   # names are written inline in English
            oc = [(c, len(ts)) for c, ts in ow]; nc = [(c, len(ts)) for c, ts in nw]
            if oc != nc:
                problems.append('%s %s: command list differs orig %s new %s' % (sk, mid, oc, nc)); continue
            for (c, ots), (_, nts) in zip(ow, nw):
                for t, u in zip(ots, nts):
                    n_ptr += 1
                    exact = start_id.get(t - base)
                    if exact is not None:
                        if msgs.get(exact) != (bank << 16 | u):
                            problems.append('%s %s: %02X -> %s expected %06X got %02X:%04X' % (sk, mid, c, exact, msgs.get(exact, 0), bank, u))
                    else:
                        fwd[(sk, t)].add((bank, u)); rev[(bank, u)].add((sk, t))
    for k, v in fwd.items():
        if len(v) > 1: problems.append('orig target %s:%04X maps to several new targets %s' % (k[0], k[1], sorted(v)))
    for k, v in rev.items():
        if len(v) > 1: problems.append('new target %02X:%04X shared by several orig targets %s' % (k[0], k[1], sorted(v)))
    print('label/substring targets', len(fwd))
    print('messages', n_msg, 'pointers', n_ptr, 'mismatches', len(problems))
    for p in problems[:80]: print(p)

if __name__ == '__main__' and len(sys.argv) == 3:
    main(sys.argv[1], sys.argv[2])

def flow(read, entries, label):
    """follow the text flow from entry addresses; return Counter of (cmd, label(target))"""
    seen = set(); todo = list(entries); got = collections.Counter(); steps = 0
    while todo and steps < 200000:
        a = todo.pop(); 
        if a in seen: continue
        seen.add(a)
        while steps < 200000:
            steps += 1
            b = read(a)
            if b == 0x21: a += 2; continue
            if b != 0x20: a += 1; continue
            c = read(a + 1)
            if c in (0xFF, 0x17): break
            if c == 0x12:
                j = a + 2
                while read(j) != 0x20 and j < a + 40: j += 1
                a = j + 1; continue
            if c == 0x10:
                p0 = read(a + 2) | read(a + 3) << 8
                n = (p0 - ((a + 4) & 0xFFFF)) // 2 + 1
                if not 1 <= n <= 4: got[('bad10',)] += 1; break
                ts = [read(a + 2 + 2*k) | read(a + 3 + 2*k) << 8 for k in range(n)]
                got[(0x10, tuple(label(t) for t in ts))] += 1; todo += ts; break
            if c == 0x0D:
                t = read(a + 2) | read(a + 3) << 8; got[(0x0D, label(t))] += 1; todo.append(t); break
            if c == 0x0E: a += 4; continue
            if c in (0x14, 0x1C):
                t = read(a + 4) | read(a + 5) << 8; got[(c, label(t))] += 1; todo.append(t); a += 6; continue
            a += 2 + ARGS.get(c, 0)
    return got

def flow_main(op, np_):
    global ROWS
    ROWS = json.load(open(os.path.join(ROOT, 'out', 'src.json'), encoding='utf-8'))
    O = open(op, 'rb').read(); N = open(np_, 'rb').read()
    msgs = json.load(open(np_ + '.msgs.json'))
    new_at = {}
    for k, v in msgs.items(): new_at.setdefault(v, k)
    streams = {(s[0], s[1]): s for s in pickle.load(open(os.path.join(ROOT, 'out', 'streams.pkl'), 'rb'))}
    d = lorom(0x20, 0xC000); ents = []
    while N[d] != 0xFF: ents.append((N[d], N[d + 1], N[d + 2] | N[d + 3] << 8)); d += 4
    bad = 0
    for bank, idx, lst in ents:
        s = streams[(bank, idx)]
        o, _ = decompress(O, s[2]); o = bytes(o)
        ram = bytearray(decompress(N, s[2])[0]) + bytes(0x400)
        p = lorom(0x20, lst)
        while True:
            dst = N[p] | N[p + 1] << 8
            if dst == 0xFFFF: break
            n = N[p + 2]; ram[dst - 0xC000:dst - 0xC000 + n] = N[p + 3:p + 3 + n]; p += 3 + n
        ot = o[3] | o[4] << 8; nt = ram[3] | ram[4] << 8; nb = ram[5]
        starts_of = {int(r['off'], 16): r['id'] for r in ROWS if r['sk'] == '%02X#%d' % (bank, idx)}
        oe = []; ne = []
        for i in range(400):
            q = ot - 0xC000 + 2 * i
            if q + 1 >= len(o): break
            op_ = o[q] | o[q + 1] << 8
            if not 0xC000 <= op_ < 0xC000 + len(o): continue
            np__ = N[lorom(nb, nt + 2 * i)] | N[lorom(nb, nt + 2 * i) + 1] << 8
            if op_ - 0xC000 not in starts_of or new_at.get(nb << 16 | np__) != starts_of[op_ - 0xC000]: continue
            oe.append(op_); ne.append(np__)
        # labels: a target is named by the index-order position in which flow first reaches it
        def mk(names):
            return lambda t: names.setdefault(t, len(names))
        on, nn = {}, {}
        for x in oe: on.setdefault(x, len(on))
        for x in ne: nn.setdefault(x, len(nn))
        # name message starts the same way on both sides; other labels by count only
        oid = {}; 
        go = flow(lambda a: o[a - 0xC000] if 0 <= a - 0xC000 < len(o) else 0, oe, lambda t: 'L')
        gn = flow(lambda a: N[lorom(nb, a)], ne, lambda t: 'L')
        if go != gn:
            bad += 1
            print('%02X#%d flow differs:' % (bank, idx))
            for k in sorted(set(go) | set(gn), key=str):
                if go[k] != gn[k]: print('    %-40s orig %3d new %3d' % (str(k), go[k], gn[k]))
    print('scenes', len(ents), 'with flow differences', bad)

if __name__ == '__main__' and len(sys.argv) > 3 and sys.argv[3] == 'flow':
    flow_main(sys.argv[1], sys.argv[2])
