import sys, os, json, glob, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import insert as I
import build as _build
rom = open(_build.SRC, 'rb').read()
streams = pickle.load(open(os.path.join(ROOT, 'out', 'streams.pkl'), 'rb'))
rows = json.load(open(os.path.join(ROOT, 'out', 'src.json'), encoding='utf-8'))
wrapped = {}
import csv
for r in csv.DictReader(open(os.path.join(ROOT, 'script', 'popful_mail_translation.tsv'), encoding='utf-8'), delimiter='\t'):
    wrapped[r['id']] = r['en_wrapped'] if not r['en'].startswith('§') else r['en']
OVR = os.path.join(HERE, 'overrides.tsv')
if os.path.exists(OVR):
    for line in open(OVR, encoding='utf-8'):
        if line.strip() and not line.startswith('#'):
            k, v = line.rstrip('\n').split('\t', 1); wrapped[k] = v
import re as _re
for _k in list(wrapped):      # old tokenizer split '20 14/1C a b lo hi' when lo == 0x20
    wrapped[_k] = _re.sub(r'<(14|1C):([0-9a-f]{4})><([0-9A-F]{2})>', r'<\1:\2>', wrapped[_k])
    # ... and '20 10 p0 p1 .. 20 hi' when a later branch pointer's low byte is $20
    wrapped[_k] = _re.sub(r'<10:((?:[0-9a-f]{4})+)><([0-9A-F]{2})>', lambda m: '<10:%s20%s>' % (m.group(1), m.group(2).lower()), wrapped[_k])
# boxes of 3+ lines: re-flow at the full 30-letter width when that saves a line (cut-scene windows hold 2)
_LEAD = _re.compile(r'^((?:【[^】]*】|\{\[[^\]]*\]\}|〔[^〕]*〕)*)')
def _reflow(t):
    if t.startswith(('§', '=', '!MANUAL!', '⟦KEEP⟧')): return t
    out = []
    for part in _re.split(r'([▼■])', t):
        if part in ('▼', '■') or part.count('⏎') < 2: out.append(part); continue
        lead = _LEAD.match(part).group(1); body = part[len(lead):]
        if _re.search(r'[<{【〔«»‹¦⏸]', body): out.append(part); continue
        words = body.replace('⏎', ' ').split(); lines = ['']
        for w in words:
            if lines[-1] and len(lines[-1]) + 1 + len(w) > 30: lines.append(w)
            else: lines[-1] = (lines[-1] + ' ' + w) if lines[-1] else w
        out.append(lead + '⏎'.join(lines) if len(lines) < part.count('⏎') + 1 else part)
    return ''.join(out)
for _k in list(wrapped): wrapped[_k] = _reflow(wrapped[_k])
CONDENSED = {}
for line in open(os.path.join(HERE, 'condensed.tsv'), encoding='utf-8'):
    if line.strip() and not line.startswith('#'):
        k, v = line.rstrip('\n').split('\t', 1); CONDENSED[k] = v
wrapped.update(CONDENSED)
EXTRA = {}
for line in open(os.path.join(HERE, 'extra_msgs.tsv'), encoding='utf-8'):
    if line.strip() and not line.startswith('#'):
        k, a, b, mid, en = line.rstrip('\n').split('\t')
        EXTRA.setdefault(k, []).append((int(a, 16), int(b, 16), mid)); wrapped[mid] = en
# the "more" arrow sits in the last cell of the last text row of a box that ends in a wait (▼):
# keep that row to 28 letters when the box can be re-flowed without adding a line
def _arrow(t):
    if t.startswith(('=', '!MANUAL!', '⟦KEEP⟧')): return t
    parts = _re.split(r'([▼■])', t); out = []
    for i, part in enumerate(parts):
        nxt = parts[i+1] if i + 1 < len(parts) else ''
        if nxt != '▼' or not part: out.append(part); continue
        lead = _LEAD.match(part.lstrip('§')).group(1); pre = '§' if part.startswith('§') else ''
        body = part[len(pre) + len(lead):]
        lines = body.split('⏎')
        if len(lines[-1]) < 30 or _re.search(r'[<{【〔«»‹¦⏸]', body) or body.startswith('⏎'): out.append(part); continue
        words = body.replace('⏎', ' ').split(); n = len(lines)
        rev = []; cur = ''; width = 28
        for w in reversed(words):
            if cur and len(cur) + 1 + len(w) > width: rev.append(cur); cur = w; width = 30
            else: cur = (w + ' ' + cur) if cur else w
        rev.append(cur)
        if len(rev) <= n and all(len(x) <= 30 for x in rev): out.append(pre + lead + '⏎'.join(reversed(rev)))
        else: out.append(part)
    return ''.join(out)
for _k in list(wrapped): wrapped[_k] = _arrow(wrapped[_k])
def stream_jobs():
    for s in streams:
        if s[6] <= 5: continue
        key = '%02X#%d' % (s[0], s[1])
        o, _ = I.decompress(rom, s[2])
        if not (o[0] == 0x4C and o[5] == 0x7E): continue      # non-standard (intro/ending/shop)
        ms = I.messages(o)
        ids = {int(r['off'], 16): r['id'] for r in rows if r['sk'] == key}
        msgs = [(a, b, ids.get(a)) for a, b, m in ms]
        for x in EXTRA.get(key, []):
            keep = []
            for t in msgs:
                if t[0] < x[1] and x[0] < t[1]:
                    if t[1] > x[1]: keep.append((x[1], t[1], t[2]))     # runs past the new message: keep its tail
                    if t[0] < x[0]: keep.append((t[0], x[0], t[2] if t[1] <= x[1] else None))
                else: keep.append(t)
            msgs = keep + [x]
        msgs.sort()
        yield s, key, o, msgs
if __name__ == '__main__':
    total = 0; errs = 0
    for s, key, o, msgs in stream_jobs():
        try:
            blk, warn = I.build_text_block(o, key, msgs, wrapped, 0x8000)
            total += len(blk)
            print('%-6s orig text %5d -> en block %5d  warnings %d %s' % (key, len(o) - ((o[3] | o[4] << 8) - 0xC000), len(blk), len(warn), warn[:3]))
        except Exception as ex:
            errs += 1; print(key, 'ERROR', ex)
    print('total', total, 'errors', errs)

# narration (green) text: centre every line.  Lines that already start with <18:xx> are re-centred
# by the builder; lines without one get a free centring indent (⇥) just before their first letter.
_SK = {r['id']: r['sk'] for r in rows}
for _k, _v in EXTRA.items():
    for _a, _b, _mid in _v: _SK[_mid] = _k
_NO_CENTRE = ('17#4', '1A#0', '1F#0')
def _is_narration(mid, t):
    if _SK.get(mid) in _NO_CENTRE: return False
    if '【NARR】' in t: return True
    return '<18:' in t and not _re.search(r'【|\{\[|〔', t)
def _centre_narration(mid, t):
    if not _is_narration(mid, t): return t
    i = t.find('【NARR】'); i = i + len('【NARR】') if i >= 0 else 0
    head, body = t[:i], t[i:]
    m = _re.search(r'【|\{\[|〔', body)                 # narration ends where a speaker takes over
    tail = body[m.start():] if m else ''; body = body[:m.start()] if m else body
    out = []
    for p in _re.split(r'(⏎|▼|■)', body):
        if p in ('⏎', '▼', '■') or not p: out.append(p); continue
        # leading control tokens, then the first letter
        lead = _re.match(r'^((?:<[^>]*>|[§«»‹¦⇥ ]|⏸\d?)*)', p).group(1)
        rest = p[len(lead):]
        if _re.search(r'<(14|1C):[0-9a-f]+>$', lead):        # pointer bytes shown as kana belong to the 14/1C
            j = _re.match(r'^[^\x00-\x7f]{1,2}', rest)
            if j: lead += j.group(0); rest = rest[j.end():].lstrip(' ')
        if rest and '<18:' not in lead and '⇥' not in lead:
            p = lead.replace(' ', '') + '⇥' + rest
        out.append(p)
    return head + ''.join(out) + tail
for _k in list(wrapped): wrapped[_k] = _centre_narration(_k, wrapped[_k])
