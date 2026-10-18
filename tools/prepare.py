"""Make the working files in out/ from the repo data and your own copy of the ROM.

out/streams.pkl  the game's compressed data streams (from data/streams.json)
out/src.json     one entry per message: id, stream, offset in the stream, and the Japanese text
                 decoded from your ROM (used by the build to find each message, and by the checking tools)

Run from the repo root; patch/make.py calls it before every build.  Nothing here is written back to
the repo: out/ is in .gitignore.
"""
import os, sys, json, pickle, zlib, subprocess

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ROM = os.environ.get('PM_ROM') or os.path.join(ROOT, 'rom', 'Popful Mail (Japan).sfc')
ROM_CRC = 0x88E5BCDF


def main():
    if not os.path.exists(ROM):
        sys.exit('Original ROM not found: %s\nPut "Popful Mail (Japan).sfc" (1 MB, no copier header, '
                 'CRC32 88E5BCDF) in rom/, or set PM_ROM to its path.' % ROM)
    crc = zlib.crc32(open(ROM, 'rb').read())
    if crc != ROM_CRC:
        sys.exit('%s has CRC32 %08X; the patch needs the original Japanese ROM with CRC32 %08X '
                 '(1 MB, no 512-byte copier header).' % (ROM, crc, ROM_CRC))
    out = os.path.join(ROOT, 'out'); os.makedirs(out, exist_ok=True)
    pkl = os.path.join(out, 'streams.pkl')
    if not os.path.exists(pkl):
        streams = [tuple(s) for s in json.load(open(os.path.join(ROOT, 'data', 'streams.json')))['streams']]
        pickle.dump(streams, open(pkl, 'wb'))
    src = os.path.join(out, 'src.json')
    if not os.path.exists(src):
        print('decoding the message index from the ROM (once)...')
        subprocess.run([sys.executable, os.path.join('tools', 'build_src.py')], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, env=dict(os.environ, PM_ROM=ROM))


if __name__ == '__main__':
    main()
