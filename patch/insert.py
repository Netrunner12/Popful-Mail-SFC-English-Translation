"""Rebuild the text area of a standard scene stream with English text, in a ROM bank."""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, HERE)
from pmlz import decompress
exec(open(os.path.join(ROOT, 'tools', 'extract.py'), encoding='utf-8').read())
exec(open(os.path.join(ROOT, 'tools', 'tok2.py'), encoding='utf-8').read())
from build import char_code

PORTRAIT = {'Mail': 0x08, 'Tatto': 0x09, 'Gaw': 0x0A, 'NARR': 0x04}
PORT_JP = {0x08, 0x09, 0x0A, 0x04}
FREE_CMDS = {0x0B, 0x13}            # line break / pause: not aligned between JP and EN

def load_names():
    m = {}
    for line in open(os.path.join(HERE, 'names.tsv'), encoding='utf-8'):
        if line.strip() and not line.startswith('#'):
            jp, en = line.rstrip('\n').split('\t'); m[jp] = en
    return m
NAMES = load_names()

# reverse JP table for stray kana/kanji argument bytes kept in the English text
REV = {}
for k, v in sorted(S.items(), reverse=True): REV[v] = bytes([k])
for k, v in sorted(D.items(), reverse=True): REV.setdefault(v, bytes([0x21, k]))

def jp_tokens(o, a, b):
    """list of dicts: pos, end, kind (text/aligned/free), sub (detail), raw bytes"""
    toks = list(tokenize(o, a, b)); out = []
    for i, (p, k, v) in enumerate(toks):
        end = toks[i+1][0] if i + 1 < len(toks) else b
        t = {'pos': p, 'end': end, 'raw': bytes(o[p:end])}
        if k == 'chr': t['kind'] = 'text'; t['sub'] = v
        elif k == 'name': t['kind'] = 'aligned'; t['sub'] = ('label', v)
        else:
            c, args = v
            if c in FREE_CMDS: t['kind'] = 'free'; t['sub'] = ('cmd', c)
            elif c == 0x0E:
                s = substr(o, args[0] | args[1] << 8) if len(args) == 2 else None
                if s and s.startswith('['): t['kind'] = 'aligned'; t['sub'] = ('call',)
                else: t['kind'] = 'free'; t['sub'] = ('subcall',)
            else: t['kind'] = 'aligned'; t['sub'] = ('cmd', c)
        out.append(t)
    return out

TOK_RE = re.compile(r'(⟦KEEP⟧|¦|⇥[+-]?|⟨w\d+⟩|▽|⏎|▼|■|⏸\d?|«|»|‹|【[^】]*】|\{\[[^\]]*\]\}|〔[^〕]*〕|<[0-9A-F]{2}(?::[0-9a-f]+)?>)')
def en_tokens(s):
    out = []
    for part in TOK_RE.split(s):
        if not part: continue
        if TOK_RE.fullmatch(part):
            if part == '⟦KEEP⟧': out.append(('keep',))
            elif part == '¦': out.append(('join',))
            elif part == '⏎': out.append(('free', 0x0B, b''))
            elif part == '▽': out.append(('free', 0x0C, b''))      # box break added in English only
            elif part == '⇥': out.append(('free', 0x18, b'\x00'))      # centring indent added in English
            elif part == '⇥+': out.append(('free', 0x18, b'\x01'))    # same, odd padding rounded right (per-line tweak)
            elif part == '⇥-': out.append(('free', 0x18, b'\x02'))    # same, odd padding rounded left (per-line tweak)
            elif part.startswith('⟨w'): out.append(('width', int(part[2:-1])))   # centring width of a line that continues through a jump
            elif part.startswith('⏸'): out.append(('free', 0x13, bytes([int(part[1:] or 0)])))
            elif part == '▼': out.append(('aligned', ('cmd', 0x0C)))
            elif part == '■': out.append(('aligned', ('cmd', 0xFF)))
            elif part == '«': out.append(('aligned', ('cmd', 0x01)))
            elif part == '»': out.append(('aligned', ('cmd', 0x00)))
            elif part == '‹': out.append(('aligned', ('cmd', 0x02)))
            elif part.startswith('【+'): out.append(('free', PORTRAIT[part[2:-1]], b''))   # speaker name added in English only
            elif part.startswith('【'): out.append(('aligned', ('cmd', PORTRAIT[part[1:-1]])))
            elif part.startswith('{['): out.append(('aligned', ('call',)))
            elif part.startswith('〔'): out.append(('aligned', ('label', part[1:-1])))
            else:
                c = int(part[1:3], 16); out.append(('aligned', ('cmd', c)))
        else:
            out.append(('text', part))
    return out

def enc_text(s, jp_runs):
    out = bytearray(); i = 0
    while i < len(s):
        ch = s[i]
        try:
            out.append(char_code(ch)); i += 1; continue
        except KeyError:
            pass
        j = i                                   # run of non-ASCII (stray argument bytes)
        while j < len(s):
            try: char_code(s[j]); break
            except KeyError: j += 1
        run = s[i:j]
        if run in jp_runs: out += jp_runs[run]
        else:
            for c in run:
                if c not in REV: raise ValueError('cannot encode %r' % c)
                out += REV[c]
        i = j
    return bytes(out)

class Builder:
    def __init__(self, base_addr):
        self.base = base_addr; self.buf = bytearray(); self.map = {}; self.fix = []; self.warn = []
    def here(self): return self.base + len(self.buf)
    def mark(self, old): self.map.setdefault(old, self.here())
    def emit_cmd_raw(self, raw, old_pos):
        """emit an original command token, recording pointer arguments for later remapping"""
        self.mark(old_pos)
        start = len(self.buf); self.buf += raw
        if len(raw) >= 2 and raw[0] == 0x20:
            c = raw[1]
            if c in (0x0E, 0x0D) and len(raw) >= 4:
                self.fix.append((start + 2, raw[2] | raw[3] << 8))
            elif c == 0x10:
                for k in range(2, len(raw) - 1, 2): self.fix.append((start + k, raw[k] | raw[k+1] << 8))
            elif c in (0x14, 0x1C) and len(raw) >= 6:
                self.fix.append((start + 4, raw[4] | raw[5] << 8))

def translate_label(raw):
    """20 12 <jp name> 20  ->  20 12 <en name> 20"""
    name = ''; j = 2
    while j < len(raw) and raw[j] != 0x20:
        if raw[j] == 0x21: name += D.get(raw[j+1], '?'); j += 2
        else: name += S.get(raw[j], '?'); j += 1
    en = NAMES.get(name)
    if en is None: return raw, name
    return b'\x20\x12' + bytes(char_code(c) for c in en) + b'\x20', None

SUBST = {}
_sp = os.path.join(HERE, 'substrings.tsv')
if os.path.exists(_sp):
    for _l in open(_sp, encoding='utf-8'):
        if _l.strip() and not _l.startswith('#'):
            _k, _a, _b, _e = _l.rstrip('\n').split('\t')
            SUBST[(_k, int(_a, 16))] = (int(_b, 16), _e)

def encode_simple(e):
    """English with only ⏎ ⏸ « » <18:xx> <cc> tokens -> bytes"""
    out = bytearray()
    for part in TOK_RE.split(e):
        if not part: continue
        m = re.fullmatch(r'<([0-9A-F]{2})(?::([0-9a-f]+))?>', part)
        if m: out += bytes([0x20, int(m.group(1), 16)]) + bytes.fromhex(m.group(2) or ''); continue
        if part == '⏎': out += b'\x20\x0b'
        elif part.startswith('⏸'): out += bytes([0x20, 0x13, int(part[1:] or 0)])
        elif part == '«': out += b'\x20\x01'
        elif part == '»': out += b'\x20\x00'
        elif TOK_RE.fullmatch(part): raise ValueError('unsupported token in substring %r' % part)
        else: out += enc_text(part, {})
    return bytes(out)

POSTER_NUDGE = {'Material Horn': 1}   # letters to the right

def poster_centre(label):
    """half-cell centring for a label line (20 12 text 20): -> (indent cells, leading space 0/1)"""
    n = len(label) - 3; narrow = n > 0 and label[-2] in {char_code(c) for c in ".,!?'"}
    left = max(0, (31 if narrow else 30) - n) // 2
    for name, d in POSTER_NUDGE.items():               # per-poster tweaks requested after play-testing
        if label[2:-1] == bytes(char_code(c) for c in name): left += d
    return left // 2, left & 1

def copy_raw(B, o, a, b):
    """copy original bytes, translating name labels/definitions and keeping pointer fixups"""
    last18 = None; skip_to = None
    for t in jp_tokens(o, a, b):
        if skip_to is not None:
            if t['pos'] < skip_to: B.map.setdefault(t['pos'], B.here()); continue
            skip_to = None
        sub = SUBST.get((getattr(B, 'key', None), t['pos']))
        if sub:
            B.mark(t['pos']); B.buf += encode_simple(sub[1]); skip_to = sub[0]; continue
        if t['kind'] == 'aligned' and t['sub'][0] == 'label':
            new, miss = translate_label(t['raw'])
            if miss: B.warn.append('untranslated name %r' % miss)
            elif last18 is not None:            # centred label (posters): re-centre for the English width
                B.buf[last18], sp = poster_centre(new)
                if sp: new = new[:2] + enc_text(' ', {}) + new[2:]     # inside the label: a label starts a new cell
            B.mark(t['pos']); B.buf += new; last18 = None
            continue
        if last18 is not None and t['raw'][:2] == b'\x20\x0e' and len(t['raw']) == 4:
            q = (t['raw'][2] | t['raw'][3] << 8) - BASE
            if 0 <= q < len(o) - 2 and o[q] == 0x20 and o[q+1] == 0x12:
                e_ = q + 2
                while e_ < len(o) and o[e_] != 0x20: e_ += 2 if o[e_] == 0x21 else 1
                new, miss = translate_label(bytes(o[q:e_+1]))
                if not miss: B.buf[last18] = center(len(new) - 3)   # shared label: whole cells only
        last18 = len(B.buf) + 2 if t['raw'][:2] == b'\x20\x18' and len(t['raw']) == 3 else (last18 if t['kind'] == 'free' else None)
        for k in range(1, len(t['raw'])): B.map.setdefault(t['pos'] + k, B.here() + k)
        if t['kind'] == 'text':
            if not hasattr(B, 'rawjp') or B.rawjp_end != t['pos']: B.rawjp_list = getattr(B, 'rawjp_list', []); B.rawjp_list.append([t['pos'], ''])
            B.rawjp_list[-1][1] += t['sub']; B.rawjp = True; B.rawjp_end = t['end']
        if t['kind'] in ('aligned', 'free') and t['raw'][:1] == b'\x20':
            B.emit_cmd_raw(t['raw'], t['pos'])
        else:
            B.mark(t['pos']); B.buf += t['raw']

def build_text_block(o, key, msgs, en, base_addr, base=0xC000, table=None, n_ents=None, region=None, extra_ptrs=()):
    """Rebuild [region) of a stream with English text; the new block = message table + text.
    Standard streams: table found from the header, region = everything after it."""
    global BASE
    BASE = base
    if table is None:
        t0 = (o[3] | o[4] << 8) - base
        ents = []; i = t0
        while i + 1 < len(o):
            w = o[i] | o[i+1] << 8
            valid = [e for e in ents if e != 0xFFFF]
            if valid and i >= min(valid) - base: break
            if w == 0xFFFF or base + t0 < w < base + len(o): ents.append(w); i += 2
            else: break
        while ents and ents[-1] == 0xFFFF: ents.pop()
        tend = t0 + 2 * len(ents); rend = len(o)
    else:
        ents = [o[table + 2*k] | o[table + 2*k + 1] << 8 for k in range(n_ents)]
        tend, rend = region
    B = Builder(base_addr); B.msgstart = {}; B.key = key
    B.targets = set(w - base for w in ents if w != 0xFFFF)
    for t in jp_tokens(o, tend, rend):
        r = t['raw']
        if len(r) >= 4 and r[0] == 0x20 and r[1] in (0x0E, 0x0D, 0x10):
            for k in range(2, len(r) - 1, 2): B.targets.add((r[k] | r[k+1] << 8) - base)
        if len(r) >= 6 and r[0] == 0x20 and r[1] in (0x14, 0x1C):
            B.targets.add((r[4] | r[5] << 8) - base)
    B.buf += bytes(2 * len(ents))
    pos = tend
    spans = [(t['pos'], t['end']) for t in jp_tokens(o, tend, rend) if t['raw'][:1] == b'\x20']
    for (a, b, mid) in msgs:
        if b <= tend or a >= rend: continue
        b = min(b, rend)
        a = max(a, tend)
        for (p_, e_) in spans:                     # message start that splits a command: move past it
            if p_ < a < e_ < b:
                junk = render(o, a, e_); a = e_
                e = en.get(mid, '=')
                lead = '§' if e.startswith('§') else ''
                if e.lstrip('§').startswith(junk): en = dict(en); en[mid] = lead + e.lstrip('§')[len(junk):]
                elif e.lstrip('§')[:1] and ord(e.lstrip('§')[0]) > 0x7F and not e.startswith('!MANUAL!') and not e.lstrip('§').startswith(('【', '〔', '{', '¦', '■', '▼', '⏎')):
                    B.warn.append('%s: split-command junk %r not in English' % (mid, junk))
                break
        for (p_, e_) in spans:
            if p_ < b < e_: B.warn.append('%s: end %04X splits a command at %04X' % (mid, b, p_))
        if a > pos: copy_raw(B, o, pos, a)
        B.msgstart[mid] = B.here()
        e = en.get(mid, '=')
        pre = len(B.buf) - 1 if a >= 3 and o[a-3] == 0x20 and o[a-2] == 0x18 and B.buf[-3:-1] == b'\x20\x18' else None
        if e == '=' or e.startswith('!MANUAL!'):
            copy_raw(B, o, a, b)
        else:
            # split off a header part (name definitions ending in 20 17) that the English skips
            full = bytes(o[a:b]); cut = a
            k = full.rfind(b'\x20\x17')
            if k >= 0: cut = a + k + 2
            if cut > a: copy_raw(B, o, a, cut)
            B.msgstart[mid] = B.here()
            emit_message(B, o, cut, b, e, mid, pre)
        pos = b
    if pos < rend: copy_raw(B, o, pos, rend)
    # table
    for n, w in enumerate(ents):
        if w == 0xFFFF: continue
        old = w - base
        if old not in B.map: B.warn.append('table entry %d -> %04X unmapped' % (n, w)); new = B.base
        else: new = B.map[old]
        B.buf[2*n:2*n+2] = (new & 0xFFFF).to_bytes(2, 'little')
    # pointer words inside data copied verbatim (sub-tables)
    for q in extra_ptrs:
        v = o[q] | o[q+1] << 8
        if v != 0xFFFF: B.fix.append((B.map[q] - B.base, v))
    # pointer fixups
    keys = sorted(B.map)
    for at, oldv in B.fix:
        old = oldv - base
        if not (tend <= old < rend): continue          # not a text pointer (data that only looks like a command)
        if old in B.map: new = B.map[old]
        else:
            nxt = [k for k in keys if k >= old]
            if not nxt: B.warn.append('pointer %04X unmapped' % oldv); continue
            new = B.map[nxt[0]]; B.warn.append('pointer %04X approximated' % oldv)
        B.buf[at:at+2] = (new & 0xFFFF).to_bytes(2, 'little')
    for pos_, txt in getattr(B, 'rawjp_list', []):
        if len(txt) >= 4 and sum(1 for ch in txt if '\u3040' <= ch <= '\u30ff') >= 3:
            B.warn.append('raw JP %04X %s' % (pos_, txt[:24]))
    global LAST_MAP, LAST_BASE, LAST_MSGS
    LAST_MAP, LAST_BASE, LAST_MSGS = B.map, B.base, B.msgstart
    return bytes(B.buf), B.warn

def center(n):
    slots = (n + 1) // 2
    return max(0, (15 - slots) // 2)

def emit_message(B, o, a, b, e, mid, pre=None):
    jt = jp_tokens(o, a, b)
    jp_al = [t for t in jt if t['kind'] == 'aligned']
    et = en_tokens(e.lstrip('§'))
    en_al = [t for t in et if t[0] == 'aligned']
    if len(jp_al) != len(en_al):
        raise ValueError('%s: aligned token count %d vs %d' % (mid, len(jp_al), len(en_al)))
    jp_runs = {}
    for t in jt:
        if t['kind'] == 'text': jp_runs[t['sub']] = jp_runs.get(t['sub'], b'') or t['raw']
    # merge consecutive JP text tokens into runs for stray-byte lookup
    run_s, run_b = '', b''
    for t in jt + [{'kind': 'end'}]:
        if t['kind'] == 'text': run_s += t['sub']; run_b += t['raw']
        else:
            if run_s: jp_runs.setdefault(run_s, run_b)
            run_s, run_b = '', b''
    def line_after(k):
        n = 0; skip = 0
        for t in et[k:]:
            if t[0] == 'width': return t[1]
            if t[0] == 'text': n += skip + len(enc_text(t[1], jp_runs)); skip = 0
            elif t[0] == 'free' and t[1] in (0x0B, 0x0C): break
            elif t[0] == 'aligned' and t[1] in (('cmd', 0x0C), ('cmd', 0xFF)): break
            elif t[0] == 'aligned' and t[1] in (('cmd', 0x00), ('cmd', 0x01), ('cmd', 0x02)): skip = n & 1   # colour change starts a new cell
        return n
    def centre_at(k, right=None):
        # half-cell accurate centring: indent in cells, plus one leading space when the letter padding is odd
        n = line_after(k)
        last = ''
        for t in et[k:]:
            if t[0] == 'text': last = t[1].rstrip()[-1:] or last
            elif (t[0] == 'free' and t[1] == 0x0B) or (t[0] == 'aligned' and t[1] in (('cmd', 0x0C), ('cmd', 0xFF))): break
        # odd padding: round right when the line ends in narrow punctuation (it looks short), else left
        if right is None: right = last in ".,!?'"
        left = max(0, (31 if right else 30) - n) // 2
        nxt = next((t for t in et[k:] if t[0] != 'free' or t[1] not in (0x13,)), None)
        if nxt is not None and nxt[0] == 'aligned' and nxt[1] in (('cmd', 0x01), ('cmd', 0x02)): left &= ~1
        if n == 0: left = 0
        for t in et[k:]:                       # another indent follows before the text: it places the line
            if t[0] == 'text': break
            if t[:2] == ('free', 0x18) or (t[0] == 'aligned' and t[1] == ('cmd', 0x18)): return 0, 0      # indents add up: the later one centres
        return left // 2, left & 1
    space = enc_text(' ', jp_runs)
    lead_space = False
    if pre is not None:
        B.buf[pre], lead_space = centre_at(0)
    bounds = set(t['pos'] for t in jp_al) | set(t['end'] for t in jp_al) | {a}
    pending = sorted(t for t in getattr(B, 'targets', ()) if a < t < b and t not in bounds)
    ai = 0; jpos_marked = set()
    # old positions of free/text JP tokens before each aligned token map to that aligned token's start
    al_old = [t['pos'] for t in jp_al]
    B.mark(a)
    if lead_space: B.buf += space
    et = list(et)
    # strip characters that are really the pointer bytes of 14/1C (shown as kana in the source text)
    aj = 0
    for k in range(len(et)):
        if et[k][0] != 'aligned': continue
        jtok = jp_al[aj]; aj += 1
        r = jtok['raw']
        if len(r) >= 6 and r[1] in (0x14, 0x1C) and k + 1 < len(et) and et[k+1][0] == 'text':
            junk = ''.join(S.get(x, '') for x in r[4:6]) if r[4] != 0x21 else D.get(r[5], '')
            n = 0
            while n < len(junk) and et[k+1][1][n:n+1] == junk[n]: n += 1
            et[k+1] = ('text', et[k+1][1][n:])
            if et[k+1][1][:1] and ord(et[k+1][1][0]) > 0x7F: B.warn.append('%s: stray %r after <%02X>' % (mid, et[k+1][1][:3], r[1]))
    for k, t in enumerate(et):
        if t[0] == 'join':
            if pending: B.mark(pending.pop(0))
            else: B.warn.append('%s: join marker without target' % mid)
        elif t[0] == 'width':
            pass                                  # only steers centring (line_after)
        elif t[0] == 'keep':
            first = al_old[0] if al_old else b
            for q in range(a, first): B.map.setdefault(q, B.here() + (q - a))
            B.buf += bytes(o[a:first])
        elif t[0] == 'text':
            B.buf += enc_text(t[1], jp_runs)
        elif t[0] == 'free':
            if t[1] == 0x0B and k + 1 < len(et) and et[k+1][0] == 'aligned' and ai < len(jp_al):
                lo = jp_al[ai-1]['end'] if ai else a
                for jt_ in jt:
                    if lo <= jt_['pos'] < jp_al[ai]['pos'] and jt_['kind'] == 'free' and jt_['sub'] == ('cmd', 0x0B):
                        B.mark(jt_['pos'])
            B.buf += bytes([0x20, t[1]]) + t[2]
            if t[1] == 0x18:
                B.buf[-1], sp = centre_at(k + 1, {b'\x01': True, b'\x02': False}.get(t[2]))
                if sp: B.buf += space
        else:
            jtok = jp_al[ai]; ai += 1
            if jtok['sub'][0] == 'label':
                B.mark(jtok['pos']); new, miss = translate_label(jtok['raw'])
                if miss: B.warn.append('%s untranslated label %r' % (mid, miss))
                B.buf += new
            else:
                B.emit_cmd_raw(jtok['raw'], jtok['pos'])
                sp = 0
                if jtok['sub'] == ('cmd', 0x18) and len(jtok['raw']) == 3:
                    B.buf[-1], sp = centre_at(k + 1)
            # targets that pointed just past this token (e.g. variant starts)
            B.mark(jtok['end'])
            if jtok['sub'][0] != 'label' and sp: B.buf += space
