"""Main experiment: compare large-print production strategies on 14 library scans.

All strategies withdraw the same fraction of running text from the reflowable
layer at each operating point, so the comparison isolates the choice of *which*
passages to keep as magnified images of the original.
"""
import os, sys, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS
import engine as E
from reliability import wilson

COV_LOSS = [0.0, 0.02, 0.05, 0.10, 0.20, 0.40]
SELECTORS = ["model", "conf", "random", "oracle"]
OUT = "data/results/runs.jsonl"


def measure(segs, route, constrained=True, breaker=E.kp_ragged, cache=None):
    items = E.build_items(segs, route, breaker=breaker, cache=cache)
    pages = E.paginate(items, constrained=constrained)
    v = E.violations(items, pages)
    n_tok = n_err = t_tok = t_err = 0        # over ground-truth-scorable tokens
    a_tok = a_text = 0                        # over all content tokens
    for i, s in enumerate(segs):
        if s["kind"] != "par":
            continue
        for t in s["toks"]:
            a_tok += 1
            if route[i] == "text":
                a_text += 1
            if not t["scorable"]:
                continue
            n_tok += 1
            n_err += t["err"]
            if route[i] == "text":
                t_tok += 1
                t_err += t["err"]
    # raggedness of the right-hand edge over non-final text lines
    sl = []
    sp = E.wid(" ", E.SPEC["body"])
    for it in items:
        if it["t"] != "line" or it["last"] or it.get("role") != "body":
            continue
        size = it["size"]
        w = sum(E.wid(t, size) for t in it["words"]) + E.wid(" ", size) * (len(it["words"]) - 1)
        sl.append(max(0.0, E.SPEC["measure"] - it.get("indent", 0.0) - w) / E.SPEC["measure"])
    sl = np.array(sl) if sl else np.zeros(1)
    return {"pages": len(pages), "items": len(items), **v,
            "scorable": n_tok, "src_errors": n_err,
            "text_tokens": t_tok, "exposed_errors": t_err,
            "all_tokens": a_tok, "all_text_tokens": a_text,
            "coverage": a_text / a_tok if a_tok else 0.0,
            "coverage_scorable": t_tok / n_tok if n_tok else 0.0,
            "ragged_rms": float(np.sqrt((sl ** 2).mean())),
            "ragged_max": float(sl.max()),
            "red_per_1000": 1000.0 * t_err / n_tok if n_tok else 0.0}


def run_book(key, f):
    t0 = time.time()
    segs, st = E.document(key)
    page_width = st["W"]
    scores = {"model": E.score_model(segs), "conf": E.score_conf(segs),
              "random": E.score_random(segs), "oracle": E.score_oracle(segs)}
    cache = {}
    ident, year, pgid, genre, title = CORPUS[key]
    base = {"key": key, "ident": ident, "year": year, "genre": genre, "title": title}

    def emit(**kw):
        f.write(json.dumps({**base, **kw}) + "\n"); f.flush()

    all_text = E.route_all(segs, "text")
    emit(method="greedy-reflow", cov_loss=0.0, selector="none",
         **measure(segs, all_text, constrained=False, breaker=E.greedy, cache=cache))
    emit(method="kp-unconstrained", cov_loss=0.0, selector="none",
         **measure(segs, all_text, constrained=False, cache=cache))
    emit(method="constrained-reflow", cov_loss=0.0, selector="none",
         **measure(segs, all_text, constrained=True, cache=cache))
    emit(method="all-facsimile", cov_loss=1.0, selector="none",
         **measure(segs, E.route_all(segs, "fac"), constrained=True, cache=cache))
    z = E.facsimile_zoom(key, segs, page_width=page_width)
    m0 = measure(segs, all_text, constrained=True, cache=cache)
    emit(method="magnify-tile", cov_loss=1.0, selector="none",
         pages=z["pages"], items=0, widow=0, orphan=0, split_heading=0, overfull=0,
         scorable=m0["scorable"], src_errors=m0["src_errors"], text_tokens=0,
         exposed_errors=0, all_tokens=m0["all_tokens"], all_text_tokens=0,
         coverage=0.0, coverage_scorable=0.0, ragged_rms=0.0, ragged_max=0.0,
         red_per_1000=0.0, src_pages=z["src_pages"], no_pan_frac=z["no_pan_frac"],
         no_pan_frac_full=z["no_pan_frac_full"],
         achieved_pt_median=z["achieved_pt_median"])

    for sel in SELECTORS:
        for c in COV_LOSS:
            if c == 0.0 and sel != "model":
                continue
            r, spent = E.route_by_score(segs, scores[sel], c)
            emit(method="hybrid", selector=sel, cov_loss=c, spent=spent,
                 **measure(segs, r, constrained=True, cache=cache))
    emit(method="_meta", selector="none", cov_loss=0.0, src_pages=z["src_pages"],
         no_pan_frac=z["no_pan_frac"], no_pan_frac_full=z["no_pan_frac_full"],
         achieved_pt_median=z["achieved_pt_median"], segments=len(segs),
         figures=sum(1 for s in segs if s["kind"] == "fig"),
         secs=round(time.time() - t0, 1), pages=0, items=0, widow=0, orphan=0,
         split_heading=0, overfull=0, scorable=m0["scorable"],
         src_errors=m0["src_errors"], text_tokens=0, exposed_errors=0,
         all_tokens=m0["all_tokens"], all_text_tokens=0, coverage=0.0,
         coverage_scorable=0.0, ragged_rms=0.0, ragged_max=0.0, red_per_1000=0.0)
    return time.time() - t0


if __name__ == "__main__":
    os.makedirs("data/results", exist_ok=True)
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            done.add(json.loads(line)["key"])
    keys = [k for k in (sys.argv[1:] or CORPUS) if k not in done]
    with open(OUT, "a") as f:
        for k in keys:
            dt = run_book(k, f)
            print(f"{k} done in {dt:.1f}s", flush=True)
