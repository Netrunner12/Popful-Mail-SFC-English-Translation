"""Generic bug detectors for SNES play-testing.  They look at the program counter and at the
picture, so they work for any game; a game profile only supplies the numbers (which code banks
are legal, where the text box is, what colours text is drawn in, how lines should be aligned).

Issue records are plain dicts: {'kind', 'detail', 'severity'} (+ whatever the caller adds)."""
import numpy as np

# ---------------------------------------------------------------- CPU / screen health
class Health:
    """Feed it one sample per frame (or every few frames); it reports crash / black / frozen screens.
    valid_pc(pc) -> bool comes from the profile."""
    def __init__(self, valid_pc, bad_pc_frames=20, black_frames=600, frozen_frames=900):
        self.valid_pc = valid_pc; self.bad_pc_frames = bad_pc_frames
        self.black_frames = black_frames; self.frozen_frames = frozen_frames
        self.bad_run = 0; self.black_run = 0; self.same_run = 0; self.prev = None
        self.issues = []; self.flagged = set()

    def _flag(self, kind, detail, sev):
        if kind in self.flagged: return
        self.flagged.add(kind); self.issues.append({'kind': kind, 'detail': detail, 'severity': sev})

    def sample(self, e, frame_no, inputs_given=True):
        pc = e.pc()
        if getattr(e, '_valid_pc', None) and e.trace_frozen():      # exact: an instruction ran outside game code
            tr = e.trace_tail(4000); path = []
            for p in tr[-300:]:
                if not path or not (0 < p - path[-1] <= 4): path.append(p)
            self._flag('crash', 'CPU left the game code at %06X (frame %d); last code: %s'
                       % (tr[-1], frame_no, ' '.join('%06X' % p for p in path[-10:])), 'high')
            return True
        self.bad_run = self.bad_run + 1 if not self.valid_pc(pc) else 0
        if self.bad_run >= self.bad_pc_frames:
            self._flag('crash', 'CPU running outside game code at %06X (frame %d)' % (pc, frame_no), 'high')
        f = e.frame
        dark = f.max() < 24
        self.black_run = self.black_run + 1 if dark else 0
        if self.black_run >= self.black_frames:
            self._flag('black_screen', 'screen black for %d frames (frame %d, pc %06X)' % (self.black_run, frame_no, pc), 'high')
        small = f[::8, ::8].astype(np.int16)
        same = self.prev is not None and np.array_equal(small, self.prev)
        self.same_run = self.same_run + 1 if (same and inputs_given) else 0
        if self.same_run >= self.frozen_frames:
            self._flag('frozen', 'picture unchanged for %d frames despite input (frame %d, pc %06X)' % (self.same_run, frame_no, pc), 'medium')
        self.prev = small
        return 'crash' in self.flagged


# ---------------------------------------------------------------- text box analysis
def nearest_colour(px, palette):
    """px: (N,3) -> index into palette (list of (name, rgb))"""
    cols = np.array([c for _, c in palette], np.int32)
    d = ((px[:, None, :].astype(np.int32) - cols[None]) ** 2).sum(-1)
    return d.argmin(1), d.min(1)

def text_lines(frame, box, palette, tol=60 ** 2, min_px=6):
    """Find text lines inside box=(x0, y0, x1, y1) (interior, inclusive-exclusive).
    A pixel is text if it is within `tol` of one of the palette colours.
    Returns [{'y0','y1','x0','x1','colours': {name: count}}] top to bottom."""
    x0, y0, x1, y1 = box
    sub = frame[y0:y1, x0:x1].reshape(-1, 3)
    idx, dist = nearest_colour(sub, palette)
    mask = (dist <= tol).reshape(y1 - y0, x1 - x0)
    idx = idx.reshape(y1 - y0, x1 - x0)
    rows = np.where(mask.sum(1) >= 1)[0]
    lines = []
    if len(rows) == 0: return lines
    start = prev = rows[0]
    groups = []
    for r in rows[1:]:
        if r > prev + 2: groups.append((start, prev)); start = r
        prev = r
    groups.append((start, prev))
    for a, b in groups:
        m = mask[a:b + 1]
        if m.sum() < min_px: continue
        cols = np.where(m.any(0))[0]
        names = {}
        for k in np.unique(idx[a:b + 1][m]):
            names[palette[k][0]] = int((idx[a:b + 1][m] == k).sum())
        lines.append({'y0': y0 + a, 'y1': y0 + b, 'x0': x0 + cols[0], 'x1': x0 + cols[-1], 'colours': names})
    return lines

def check_box(frame, box, palette, align_of, letter_w=8, centre_tol=None, indent_tol=None,
              allow_mixed=False, allow_indent=False, max_lines=None, area=None, ignore=()):
    """Look at one text box picture and return issues.
    align_of(colour_name) -> 'centre' | 'left' | None  (how a line of that colour should sit)."""
    centre_tol = centre_tol if centre_tol is not None else letter_w + 4
    indent_tol = indent_tol if indent_tol is not None else letter_w - 2
    issues = []
    if ignore:                                             # blank out icons (e.g. a blinking 'more' arrow)
        frame = frame.copy()
        for ix0, iy0, ix1, iy1 in ignore: frame[iy0:iy1, ix0:ix1] = 0
    lines = text_lines(frame, area or box, palette)      # search a wider area so overflow is visible
    x0, y0, x1, y1 = box
    for n, L in enumerate(lines):
        main = max(L['colours'], key=L['colours'].get)
        total = sum(L['colours'].values())
        minor = {k: v for k, v in L['colours'].items() if k != main and v >= max(8, total * 0.06)}
        if minor and not allow_mixed:
            issues.append({'kind': 'colour_mix', 'severity': 'medium',
                           'detail': 'line %d mixes %s with %s (overflow or a stray colour code)' % (n + 1, main, '/'.join(minor))})
        if L['x1'] >= x1 or L['x0'] < x0:
            issues.append({'kind': 'overflow', 'severity': 'high', 'detail': 'line %d touches the box edge' % (n + 1)})
        a = align_of(main)
        left, right = L['x0'] - x0, (x1 - 1) - L['x1']
        if a == 'centre' and abs(left - right) > centre_tol:
            issues.append({'kind': 'off_centre', 'severity': 'low',
                           'detail': 'line %d off centre: %dpx left / %dpx right' % (n + 1, left, right)})
        if a == 'left' and left > indent_tol and not allow_indent:
            issues.append({'kind': 'leading_space', 'severity': 'low',
                           'detail': 'line %d starts %dpx in (about %d letters)' % (n + 1, left, round(left / letter_w))})
    if max_lines and len(lines) > max_lines:
        issues.append({'kind': 'too_many_lines', 'severity': 'high', 'detail': '%d lines in one box' % len(lines)})
    return issues, lines


# ---------------------------------------------------------------- untranslated text on screen
class GlyphMonitor:
    """Watch reads of the font memory outside the glyphs the translation uses.  Any such read means
    some routine is drawing original-language text (whatever routine it is: boxes, scrolls, menus).
    font_range = (lo, hi) work-RAM offsets of the foreign glyphs; needs the patched core."""
    def __init__(self, e, font_range):
        self.w = e.watch_reads(*font_range).__enter__(); self.issues = []; self.flagged = False
    def poll(self, e, frame_no, shot=None):
        new = self.w.poll()
        if new and not self.flagged:
            self.flagged = True
            pcs = sorted({'%06X' % h[1] for h in new})[:6]
            i = {'kind': 'untranslated_text', 'severity': 'high',
                 'detail': 'original-language glyphs drawn (frame %d) by code at %s' % (frame_no, ', '.join(pcs))}
            if shot: i['shot'] = shot(e)
            self.issues.append(i)
        return bool(new)
    def close(self):
        self.w.__exit__()


class TextReadMonitor:
    """Watch reads of the ORIGINAL text bytes in memory.  A translation redirects the game's text
    pointers to new text, so any code still reading the original text is drawing untranslated text
    (a scroll, a menu, a credits roll, a sign...) through a path the patch never touched.
    region(e) -> (lo, hi, label) work-RAM range of the original text currently loaded, or None.
    Reads made by code inside the range itself (patch code living in freed text space) are ignored.
    Text areas often hold small data tables too; a read only counts as text when looks_like_text()
    finds a run of >= min_run consecutive bytes read that looks like text (few zero bytes), which is
    what a routine drawing a line of text does and a table lookup does not."""
    def __init__(self, e, region, min_run=8, ignore_pcs=(), judge=None):
        self.e, self.region, self.cur, self.w, self.min_run = e, region, None, None, min_run
        self.judge = judge                         # judge(bytes) -> True if they read as text (profile's model)
        self.ignore_pcs = set(ignore_pcs)          # e.g. the decompressor (LZ back-references read its output)
        self.issues = []; self.flagged = set()
    def _arm(self, r):
        if self.w: self.w.__exit__(); self.w = None
        self.cur = r
        if r: self.w = self.e.watch_reads(r[0], r[1]).__enter__()
    def poll(self, e, frame_no, shot=None):
        r = self.region(e)
        if r != self.cur:
            if self.w: self._check(e, frame_no, shot)
            self._arm(r)
        elif self.w: self._check(e, frame_no, shot)
    def _check(self, e, frame_no, shot):
        lo, hi, label = self.cur
        new = [h for h in self.w.poll() if not ((h[1] >> 16) == 0x7E and lo <= (h[1] & 0xFFFF) < hi)
               and h[1] not in self.ignore_pcs]
        if not new or label in self.flagged: return
        mem = e.wram()
        run = looks_like_text(mem, sorted({h[0] for h in new}), self.min_run)
        if not run: return
        if self.judge and not self.judge(bytes(mem[run[0]:run[-1] + 1])): return     # a data table, not text
        self.flagged.add(label)
        new = [h for h in new if run[0] <= h[0] <= run[-1]]
        pcs = sorted({'%06X' % h[1] for h in new})[:6]
        addrs = run
        i = {'kind': 'untranslated_text', 'severity': 'high',
             'detail': '%s: code at %s read %d bytes of the original text ($%04X-$%04X) at frame %d'
                       % (label, ', '.join(pcs), len(addrs), addrs[0], addrs[-1], frame_no)}
        if shot: i['shot'] = shot(e)
        self.issues.append(i)
    def close(self):
        if self.w: self.w.__exit__(); self.w = None


def looks_like_text(mem, addrs, min_run=8, max_zero=0.15):
    """longest run of consecutive addresses (gaps of 1 allowed: two-byte codes) whose bytes have
    few zeros; [] if shorter than min_run"""
    best, cur = [], []
    for a in addrs:
        if cur and a - cur[-1] > 2:
            if len(cur) > len(best): best = cur
            cur = []
        cur.append(a)
    if len(cur) > len(best): best = cur
    if len(best) < min_run: return []
    zeros = sum(1 for a in best if mem[a] == 0)
    return best if zeros <= max_zero * len(best) else []
