import sys, json
rom = open(sys.argv[1], 'rb').read(); m = json.load(open(sys.argv[1] + '.msgs.json'))
def lorom(a): return ((a >> 16) & 0x7F) * 0x8000 + (a & 0x7FFF)
for mid in sys.argv[2:]:
    a = m[mid]; o = lorom(a); b = rom[o:o+90]
    e = b.find(b'\x20\xff'); b = b[:e+2] if e >= 0 else b
    print(mid, '%06X' % a, ''.join(chr(x) if 0x22 <= x < 0x7f else ('·' if x == 0 else '[%02X]' % x) for x in b))
