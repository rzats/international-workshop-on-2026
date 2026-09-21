"""Period-appropriate English lexicon used as an OCR-independent reliability cue.

Built from Webster's 1913 Unabridged (PG 29765) plus a set of clean nineteenth-
century e-texts that are disjoint from the evaluation corpus.
"""
import os, re, sys, json, requests
sys.path.insert(0, os.path.dirname(__file__))
from structure import norm_word

AUX = [1400, 98, 158, 1260, 174, 16, 2814, 36, 1232, 1080]   # not in CORPUS
WEBSTER = 29765
OUT = "data/lex/lexicon.txt"


def get(pgid):
    dest = f"data/raw/lex{pgid}.txt"
    if not os.path.exists(dest):
        r = requests.get(f"https://www.gutenberg.org/cache/epub/{pgid}/pg{pgid}.txt", timeout=300)
        r.raise_for_status()
        open(dest, "wb").write(r.content)
    return open(dest, encoding="utf-8", errors="replace").read()


def build():
    import collections
    freq = collections.Counter()
    for pid in AUX:
        for t in re.split(r"\s+", get(pid)):
            n = norm_word(t)
            if n:
                freq[n] += 1
    lex = {w for w, c in freq.items() if c >= 3}
    head = 0
    for line in get(WEBSTER).splitlines():
        m = re.match(r"^([A-Z][A-Z'\-]{1,})\s*$", line.strip())
        if m:
            n = norm_word(m.group(1))
            if n and len(n) > 1:
                lex.add(n); head += 1
    os.makedirs("data/lex", exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(sorted(lex)))
    return len(lex), head


_LEX = None


def lexicon():
    global _LEX
    if _LEX is None:
        _LEX = set(open(OUT).read().split())
    return _LEX


if __name__ == "__main__":
    print(build())
