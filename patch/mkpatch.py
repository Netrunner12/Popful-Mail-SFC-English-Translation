"""Create BPS and IPS patches (original ROM -> English ROM). Also fixes the SNES header checksum of the target."""
import sys, zlib, struct

def fix_checksum(rom):
    rom = bytearray(rom)
    rom[0x7FDC:0x7FE0] = b'\xff\xff\x00\x00'
    s = sum(rom) & 0xFFFF
    rom[0x7FDC:0x7FDE] = struct.pack('<H', s ^ 0xFFFF)
    rom[0x7FDE:0x7FE0] = struct.pack('<H', s)
    return bytes(rom)

def vlq(n):
    out = bytearray()
    while True:
        x = n & 0x7F; n >>= 7
        if n == 0: out.append(0x80 | x); return bytes(out)
        out.append(x); n -= 1

def bps(src, dst, meta=b''):
    out = bytearray(b'BPS1') + vlq(len(src)) + vlq(len(dst)) + vlq(len(meta)) + meta
    i = 0; n = len(dst); tgt_off = [0]
    while i < n:
        # SourceRead run: bytes identical at same offset
        j = i
        while j < n and j < len(src) and src[j] == dst[j]: j += 1
        if j - i >= 4 or (j == n and j > i):
            out += vlq(((j - i - 1) << 2) | 0); i = j; continue
        # run of one repeated byte: TargetRead 1 byte, then TargetCopy from the previous output byte
        j = i + 1
        while j < n and dst[j] == dst[i] and not (j < len(src) and src[j] == dst[j]): j += 1
        if j - i >= 16:
            out += vlq((0 << 2) | 1) + dst[i:i+1]
            rel = (i) - tgt_off[0]; tgt_off[0] = i + (j - i - 1)
            out += vlq(((j - i - 2) << 2) | 3) + vlq((abs(rel) << 1) | (1 if rel < 0 else 0))
            i = j; continue
        # TargetRead run until a 4-byte match or a long repeat resumes
        j = i
        while j < n:
            if j + 4 <= min(n, len(src)) and src[j:j+4] == dst[j:j+4]: break
            if j + 16 <= n and dst[j:j+16] == dst[j:j+1] * 16: break
            j += 1
        if j == i: j = i + 1
        out += vlq(((j - i - 1) << 2) | 1) + dst[i:j]; i = j
    out += struct.pack('<I', zlib.crc32(src)) + struct.pack('<I', zlib.crc32(dst))
    out += struct.pack('<I', zlib.crc32(bytes(out)))
    return bytes(out)

def ips(src, dst):
    out = bytearray(b'PATCH'); i = 0; n = len(dst)
    while i < n:
        if i < len(src) and src[i] == dst[i]: i += 1; continue
        j = i
        while j < n and j - i < 0xFFFF and not (j + 6 <= len(src) and src[j:j+6] == dst[j:j+6]): j += 1
        if i == 0x454F46: i -= 1                     # avoid the 'EOF' marker offset
        chunk = dst[i:j]
        if len(chunk) > 8 and chunk.count(chunk[0]) == len(chunk):
            out += i.to_bytes(3, 'big') + b'\0\0' + len(chunk).to_bytes(2, 'big') + chunk[:1]
        else:
            out += i.to_bytes(3, 'big') + len(chunk).to_bytes(2, 'big') + chunk
        i = j
    out += b'EOF'
    return bytes(out)

def apply_bps(src, p):
    assert p[:4] == b'BPS1'; pos = 4
    def rd():
        nonlocal pos
        d = 0; s = 1
        while True:
            x = p[pos]; pos += 1; d += (x & 0x7F) * s
            if x & 0x80: return d
            s <<= 7; d += s
    ss, ts, ms = rd(), rd(), rd(); pos += ms
    out = bytearray(); so = to = 0
    while pos < len(p) - 12:
        d = rd(); cmd = d & 3; ln = (d >> 2) + 1
        if cmd == 0: out += src[len(out):len(out)+ln]
        elif cmd == 1: out += p[pos:pos+ln]; pos += ln
        elif cmd == 3:
            d2 = rd(); to += (-1 if d2 & 1 else 1) * (d2 >> 1)
            for _ in range(ln): out.append(out[to]); to += 1
        else: raise ValueError('unsupported')
    assert zlib.crc32(bytes(out)) == struct.unpack('<I', p[-8:-4])[0]
    return bytes(out)

def apply_ips(src, p):
    out = bytearray(src); pos = 5
    while p[pos:pos+3] != b'EOF':
        o = int.from_bytes(p[pos:pos+3], 'big'); ln = int.from_bytes(p[pos+3:pos+5], 'big'); pos += 5
        if ln == 0:
            rl = int.from_bytes(p[pos:pos+2], 'big'); v = p[pos+2]; pos += 3; data = bytes([v]) * rl
        else: data = p[pos:pos+ln]; pos += ln
        if len(out) < o + len(data): out += bytes(o + len(data) - len(out))
        out[o:o+len(data)] = data
    return bytes(out)

if __name__ == '__main__':
    src = open(sys.argv[1], 'rb').read(); dst = open(sys.argv[2], 'rb').read(); base = sys.argv[3]
    b = bps(src, dst); i = ips(src, dst)
    assert apply_bps(src, b) == dst and apply_ips(src, i) == dst
    open(base + '.bps', 'wb').write(b); open(base + '.ips', 'wb').write(i)
    print('bps %d bytes, ips %d bytes, target crc32 %08X' % (len(b), len(i), zlib.crc32(dst)))
