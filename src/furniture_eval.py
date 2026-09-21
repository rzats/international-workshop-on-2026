"""Evaluate page-furniture removal without hand labelling.

Running heads, folios and catchwords are printing apparatus: they are absent
from the clean e-text of the work. Aligning the *unfiltered* OCR stream against
the e-text therefore gives a free test - material the layout analysis calls
furniture should fail to align, and material it keeps should align.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(__file__))
import align as A
from corpus import CORPUS
from reliability import wilson


def run(key):
    old = A.CONTENT_ROLES
    A.CONTENT_ROLES = ("body", "verse", "heading", "caption", "footnote", "furniture")
    try:
        doc, st, toks, meta = A.ocr_stream(key)
        ptoks = A.pg_stream(CORPUS[key][2])
        lab, ref, n_anc = A.label(toks, ptoks)
    finally:
        A.CONTENT_ROLES = old
    per = collections.defaultdict(lambda: collections.Counter())
    for m, L in zip(meta, lab):
        per[m["role"]][L] += 1
    out = {}
    for role, c in per.items():
        n = sum(c.values())
        out[role] = {"n": n, "ok": c["ok"], "sub": c["sub"], "ins": c["ins"],
                     "unk": c["unk"], "match_rate": c["ok"] / n if n else 0.0}
    return out


if __name__ == "__main__":
    os.makedirs("data/results", exist_ok=True)
    tot = collections.defaultdict(collections.Counter)
    per_book = {}
    for k in (sys.argv[1:] or CORPUS):
        r = run(k)
        per_book[k] = r
        for role, c in r.items():
            for kk, vv in c.items():
                if kk != "match_rate":
                    tot[role][kk] += vv
        print(k, {ro: (c["n"], round(c["match_rate"], 3)) for ro, c in r.items()}, flush=True)
    summ = {}
    for role, c in tot.items():
        lo, hi = wilson(c["ok"], c["n"])
        summ[role] = {"n": c["n"], "match_rate": c["ok"] / c["n"],
                      "ci": [lo, hi], **dict(c)}
    json.dump({"pooled": summ, "per_book": per_book},
              open("data/results/furniture_eval.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))
