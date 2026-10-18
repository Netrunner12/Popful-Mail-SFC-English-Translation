"""SNES Game Genie decoder -> (24-bit address, value)"""
T = 'DF4709156BC8A23E'
def decode(code):
    c = code.replace('-', '').upper()
    v = [T.index(ch) for ch in c]
    data = v[0] << 4 | v[1]
    n = 0
    for x in v[2:]: n = n << 4 | x
    # n bits: ijklqrst opabcduv wxefghmn  ->  abcdefgh ijklmnop qrstuvwx
    b = [(n >> (23 - i)) & 1 for i in range(24)]
    ijkl, qrst, op, abcd, uv, wx, efgh, mn = b[0:4], b[4:8], b[8:10], b[10:14], b[14:16], b[16:18], b[18:22], b[22:24]
    bits = abcd + efgh + ijkl + mn + op + qrst + uv + wx
    addr = 0
    for x in bits: addr = addr << 1 | x
    return addr, data
if __name__ == '__main__':
    import sys
    for c in sys.argv[1:]:
        a, d = decode(c); print(c, '%06X = %02X' % (a, d))
