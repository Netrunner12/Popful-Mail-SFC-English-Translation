"""Full build: original ROM -> English ROM (engine, font, text)."""
import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(ROOT)                                  # the helper scripts in tools/ use paths relative to the repo root
sys.path.insert(0, os.path.join(ROOT, 'patch')); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import prepare; prepare.main()                  # out/ (stream table + message index), made from your ROM
out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, 'build', 'popful_mail_en.sfc')
os.makedirs(os.path.dirname(out), exist_ok=True); sys.argv[1:2] = [out]
import build
out = sys.argv[1]
syms = build.main(out)
rep = build.insert_all(out, syms)
for l in rep: print(l)
import mkpatch
rom = open(out, 'rb').read()
open(out, 'wb').write(mkpatch.fix_checksum(rom))
print('checksum fixed')
