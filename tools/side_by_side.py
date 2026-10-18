"""Write out/side_by_side.tsv: every message with the Japanese text (decoded from your ROM) next to the
English in script/popful_mail_translation.tsv.  Handy for reviewing or editing the translation.

    python3 tools/side_by_side.py
"""
import os, sys, csv, json

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
import prepare
prepare.main()

jp = {r['id']: r['jp'] for r in json.load(open(os.path.join('out', 'src.json'), encoding='utf-8'))}
rows = list(csv.DictReader(open(os.path.join('script', 'popful_mail_translation.tsv'), encoding='utf-8'), delimiter='\t'))
path = os.path.join('out', 'side_by_side.tsv')
with open(path, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['id', 'stream', 'msg_offset', 'jp', 'en_wrapped'])
    for r in rows:
        w.writerow([r['id'], r['stream'], r['msg_offset'], jp.get(r['id'], ''), r['en_wrapped']])
print('wrote', path, len(rows), 'messages')
