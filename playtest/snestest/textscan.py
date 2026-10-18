"""Find original-language text anywhere in a ROM that the translation's script does not cover.

Generic: the game profile supplies
  runs(data)   -> [(start, end, decoded string)]   greedy decode with the game's own table
  corpus       -> the original strings of the script (what is already known / translated)
  is_native(c) -> True for characters of the original language (e.g. kana and kanji)
A run counts as text when it reads like the script (character-bigram model trained on the corpus)
and no 5-character window of it is in the script.  Random data decodes to gibberish that scores far
below real sentences, so the threshold sits just under the script's own lowest-scoring lines."""
import math, collections

class Model:
    def __init__(self, corpus, is_native, known=None):
        """corpus trains the model; known (default: corpus) is everything already in the script"""
        self.nat = is_native; self.bg = collections.Counter(); self.ug = collections.Counter()
        for t in corpus: self.ug.update(t); self.bg.update(zip(t, t[1:]))
        self.v = len(self.ug) + 1
        self.known = ''.join(''.join(c for c in t if is_native(c)) for t in (known or corpus))
        sc = sorted(self.score(t) for t in corpus if len(t) > 8)
        # 1st percentile of the script's own lines, minus a margin: narration and story text use rarer
        # words than dialogue (the story scroll that started this check scores well below the median)
        self.thresh = (sc[len(sc) // 100] - 0.4) if sc else -99
    def score(self, t):
        t = ''.join(t.split())                       # indentation runs (full-width spaces) say nothing
        if len(t) < 2: return -99
        return sum(math.log((self.bg[(a, b)] + 0.1) / (self.ug[a] + 0.1 * self.v)) for a, b in zip(t, t[1:])) / (len(t) - 1)
    def unknown_text(self, t, min_chars=6):
        core = ''.join(c for c in t if self.nat(c))
        if len(core) < min_chars or len(core) / max(1, len(t)) < 0.6 or len(set(core)) < 4: return None
        win = [core[i:i + 5] for i in range(len(core) - 4)]
        if win and sum(w in self.known for w in win) >= 0.3 * len(win): return None
        s = self.score(t)
        return s if s >= self.thresh else None

def scan(blocks, runs, model):
    """blocks: [(name, bytes)] -> [(name, start, end, text, score)]"""
    out = []
    for name, data in blocks:
        for s, e, t in runs(data):
            sc = model.unknown_text(t)
            if sc is not None: out.append((name, s, e, t, sc))
    return out
