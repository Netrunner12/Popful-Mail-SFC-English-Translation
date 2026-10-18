"""Static check of an English build: walk every message the way the game's text builder does.
usage: verify.py built.sfc   (needs built.sfc.msgs.json from the build)"""
import sys, json, collections
ARGS = {0x13: 1, 0x18: 1, 0x11: 1, 0x1C: 4, 0x1D: 2, 0x14: 4, 0x15: 2, 0x16: 2, 0x0E: 2, 0x0D: 2, 0x19: 3}
KNOWN = set(range(0x00, 0x20))

def lorom(a): return ((a >> 16) & 0x7F) * 0x8000 + (a & 0x7FFF)

def main(path):
    rom = open(path, 'rb').read()
    msgs = json.load(open(path + '.msgs.json'))
    starts = {v: k for k, v in msgs.items()}
    problems = collections.defaultdict(list)
    seen_paths = set()

    def walk(mid, addr, depth=0, line_slots=None):
        bank = addr >> 16
        if (addr, depth > 0) in seen_paths: return
        seen_paths.add((addr, depth > 0))
        chars = 0; indent = 0; jp = 0; steps = 0; lines = []
        a = addr
        while steps < 4000:
            steps += 1
            if (a & 0xFFFF) < 0x8000: problems[mid].append('pointer outside ROM half %06X' % a); return
            b = rom[lorom(a)]
            if b == 0x20:
                c = rom[lorom(a + 1)]
                if c == 0xFF:
                    slots = indent + (chars + 1) // 2         # the last line ends at the end marker
                    if slots > 15: problems[mid].append('line %d slots ending %06X' % (slots, a))
                    break
                if c == 0x17 and depth: return
                if c in (0x0B, 0x0C):
                    slots = indent + (chars + 1) // 2
                    if slots > 15: problems[mid].append('line %d slots ending %06X' % (slots, a))
                    chars = 0; indent = 0; a += 2; continue
                if c == 0x12:                                   # name label
                    j = a + 2
                    while rom[lorom(j)] != 0x20 and j < a + 40: j += 1
                    if j >= a + 40: problems[mid].append('unterminated label'); return
                    a = j + 1; continue
                if c == 0x10:
                    p0 = rom[lorom(a + 2)] | rom[lorom(a + 3)] << 8
                    n = (p0 - ((a + 4) & 0xFFFF)) // 2 + 1
                    if not 1 <= n <= 4: problems[mid].append('bad branch at %06X' % a); return
                    for k in range(n):
                        p = rom[lorom(a + 2 + 2*k)] | rom[lorom(a + 3 + 2*k)] << 8
                        walk(mid, (bank << 16) | p, depth, None)
                    return
                if c == 0x0D:
                    p = rom[lorom(a + 2)] | rom[lorom(a + 3)] << 8
                    a = (bank << 16) | p; continue
                if c == 0x0E:
                    p = rom[lorom(a + 2)] | rom[lorom(a + 3)] << 8
                    walk(mid, (bank << 16) | p, depth + 1)
                    a += 4; continue
                if c in (0x14, 0x1C):
                    p = rom[lorom(a + 4)] | rom[lorom(a + 5)] << 8
                    walk(mid, (bank << 16) | p, depth, None)
                    a += 6; continue
                if c == 0x18:
                    indent += rom[lorom(a + 2)]; a += 3; continue
                if c not in KNOWN and c != 0x19: problems[mid].append('unknown command %02X at %06X' % (c, a)); return
                a += 2 + ARGS.get(c, 0); continue
            if b == 0x21:
                jp += 1; problems[mid].append('JP kanji at %06X' % a); chars += 2; a += 2; continue
            if b >= 0x85: jp += 1; problems[mid].append('JP byte %02X at %06X' % (b, a))
            chars += 1; a += 1
        else:
            problems[mid].append('no end found')
        if jp: problems[mid].append('%d Japanese glyphs' % jp)

    for mid, addr in msgs.items():
        walk(mid, addr)
    kinds = collections.Counter(p.split(' ')[0] if not p[0].isdigit() else 'jp' for v in problems.values() for p in v)
    for mid in sorted(problems):
        print(mid, '; '.join(sorted(set(problems[mid])))[:160])
    print('messages', len(msgs), 'with problems', len(problems), dict(kinds))

if __name__ == '__main__':
    main(sys.argv[1])
