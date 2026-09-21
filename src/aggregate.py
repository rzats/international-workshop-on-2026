"""Aggregate experiment output into the tables and figures used in the paper."""
import os, sys, json, math, re, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS
from reliability import wilson

RUNS = "data/results/runs.jsonl"
OUTD = "data/results"
FIGD = "paper/figures"
COV = [0.0, 0.02, 0.05, 0.10, 0.20, 0.40]
SEL_LABEL = {"model": "reliability model", "conf": "OCR confidence",
             "random": "random", "oracle": "oracle"}


def engine_of(ident):
    head = open(f"data/raw/{ident}_hocr.html", errors="replace").read(2500)
    m = re.search(r'name="ocr-system" content="([^"]+)"', head)
    if not m:
        return "unknown"
    s = m.group(1)
    if "LuraDocument" in s:
        return "ABBYY (LuraDocument export)"
    if "FineReader Engine 11" in s:
        return "ABBYY FineReader 11"
    if "tesseract" in s.lower():
        return "Tesseract " + s.split()[-1].split("-")[0]
    return s


def load():
    rows = [json.loads(l) for l in open(RUNS)]
    idx = collections.defaultdict(list)
    for r in rows:
        idx[(r["method"], r["selector"], round(r["cov_loss"], 3))].append(r)
    return rows, idx


def pooled(rs):
    P = sum(r["pages"] for r in rs)
    Ex = sum(r["exposed_errors"] for r in rs)
    S = sum(r["scorable"] for r in rs)
    V = sum(r["widow"] + r["orphan"] + r["split_heading"] for r in rs)
    A = sum(r["all_tokens"] for r in rs)
    T = sum(r["all_text_tokens"] for r in rs)
    lo, hi = wilson(Ex, S)
    rag = sum(r["ragged_rms"] * r["pages"] for r in rs) / max(1, P)
    return {"pages": P, "exposed": Ex, "scorable": S,
            "red": 1000.0 * Ex / S if S else 0.0,
            "red_lo": 1000.0 * lo, "red_hi": 1000.0 * hi,
            "viol": V, "viol_per_100pp": 100.0 * V / P if P else 0.0,
            "coverage": T / A if A else 0.0, "ragged_rms": rag,
            "pages_per_1000w": 1000.0 * P / A if A else 0.0}


def main():
    os.makedirs(FIGD, exist_ok=True)
    rows, idx = load()
    align = json.load(open("data/corpus/align_summary.json"))
    rel = json.load(open("data/corpus/reliability_summary.json"))
    meta = {r["key"]: r for r in rows if r["method"] == "_meta"}

    out = {}

    # ---- Table 1: corpus
    t1 = []
    for k, (ident, year, pgid, genre, title) in CORPUS.items():
        a = align[k]
        t1.append({"key": k, "title": title, "year": year, "genre": genre,
                   "ident": ident, "engine": engine_of(ident),
                   "src_pages": meta[k]["src_pages"],
                   "tokens": a["ocr_tokens"], "alignable": a["alignable_frac"],
                   "wer": a["wer_aligned"], "segments": meta[k]["segments"],
                   "figures": meta[k]["figures"],
                   "achieved_pt": meta[k]["achieved_pt_median"],
                   "no_pan_crop": meta[k]["no_pan_frac"],
                   "no_pan_full": meta[k]["no_pan_frac_full"]})
    out["corpus"] = t1
    tot_tok = sum(r["tokens"] for r in t1)
    tot_al = sum(align[r["key"]]["aligned"] for r in t1)
    tot_err = sum(align[r["key"]]["n_sub"] + align[r["key"]]["n_ins"] for r in t1)
    out["corpus_totals"] = {
        "books": len(t1), "src_pages": sum(r["src_pages"] for r in t1),
        "tokens": tot_tok, "aligned": tot_al,
        "alignable": tot_al / tot_tok, "wer": tot_err / tot_al,
        "wer_ci": [x for x in wilson(tot_err, tot_al)],
        "figures": sum(r["figures"] for r in t1),
        "no_pan_crop": sum(r["no_pan_crop"] * r["src_pages"] for r in t1) / sum(r["src_pages"] for r in t1),
        "no_pan_full": sum(r["no_pan_full"] * r["src_pages"] for r in t1) / sum(r["src_pages"] for r in t1),
    }

    # ---- Table 2: reliability
    t2 = []
    for k in CORPUS:
        t2.append({"key": k, "n": rel["loo"][k]["n"], "base": rel["loo"][k]["base"],
                   "auc_model": rel["loo"][k]["auc"], "auc_conf": rel["raw_conf_auc"][k],
                   "ece": rel["loo"][k]["ece"]})
    out["reliability"] = t2
    out["reliability_totals"] = {
        "auc_model_mean": float(np.mean([r["auc_model"] for r in t2])),
        "auc_model_sd": float(np.std([r["auc_model"] for r in t2], ddof=1)),
        "auc_conf_mean": float(np.mean([r["auc_conf"] for r in t2])),
        "auc_conf_sd": float(np.std([r["auc_conf"] for r in t2], ddof=1)),
        "ece_mean": float(np.mean([r["ece"] for r in t2])),
        "wins": int(sum(1 for r in t2 if r["auc_model"] > r["auc_conf"])),
        "pooled_conf_auc": rel["pooled_raw_conf_auc"],
        "pooled_pct_auc": rel["pooled_pct_auc"],
    }
    # paired sign test over volumes
    d = [r["auc_model"] - r["auc_conf"] for r in t2]
    n_pos, n = sum(1 for x in d if x > 0), len(d)
    out["reliability_totals"]["sign_test_p"] = float(
        sum(math.comb(n, i) for i in range(n_pos, n + 1)) / 2 ** n * 2)
    out["reliability_totals"]["auc_gain_mean"] = float(np.mean(d))

    # ---- Table 3: composition strategies
    t3 = {}
    for name, key in (("greedy-reflow", ("greedy-reflow", "none", 0.0)),
                      ("kp-unconstrained", ("kp-unconstrained", "none", 0.0)),
                      ("constrained-reflow", ("constrained-reflow", "none", 0.0)),
                      ("all-facsimile", ("all-facsimile", "none", 1.0)),
                      ("magnify-tile", ("magnify-tile", "none", 1.0))):
        t3[name] = pooled(idx[key])
    out["composition"] = t3

    # ---- Table 4 / Figure 1: routing operating curve
    t4 = {}
    for sel in ("model", "conf", "random", "oracle"):
        pts = []
        for c in COV:
            k = ("hybrid", sel if c > 0 else "model", c)
            if not idx[k]:
                continue
            p = pooled(idx[k])
            p["cov_loss"] = c
            pts.append(p)
        t4[sel] = pts
    out["routing"] = t4

    base = t4["model"][0]["red"]
    gains = {}
    for c in COV[1:]:
        m = [p for p in t4["model"] if p["cov_loss"] == c][0]
        o = [p for p in t4["oracle"] if p["cov_loss"] == c][0]
        cf = [p for p in t4["conf"] if p["cov_loss"] == c][0]
        rd = [p for p in t4["random"] if p["cov_loss"] == c][0]
        gains[c] = {"model": m["red"], "conf": cf["red"], "random": rd["red"],
                    "oracle": o["red"],
                    "reduction_model": 1 - m["red"] / base,
                    "reduction_conf": 1 - cf["red"] / base,
                    "oracle_gap_closed": (base - m["red"]) / (base - o["red"]),
                    "page_overhead": m["pages"] / t4["model"][0]["pages"] - 1}
    out["routing_gains"] = gains

    # ---- per-book routing at the 10 % operating point, with CIs
    per = []
    for k in CORPUS:
        row = {"key": k}
        for sel in ("model", "conf", "random", "oracle"):
            r = [x for x in idx[("hybrid", sel, 0.10)] if x["key"] == k]
            if not r:
                continue
            r = r[0]
            lo, hi = wilson(r["exposed_errors"], r["scorable"])
            row[sel] = {"red": 1000.0 * r["exposed_errors"] / r["scorable"],
                        "lo": 1000.0 * lo, "hi": 1000.0 * hi, "pages": r["pages"]}
        b = [x for x in idx[("hybrid", "model", 0.0)] if x["key"] == k][0]
        row["base"] = {"red": 1000.0 * b["exposed_errors"] / b["scorable"],
                       "pages": b["pages"]}
        per.append(row)
    out["per_book_10pct"] = per
    wins = sum(1 for r in per if r["model"]["red"] < r["conf"]["red"])
    n = len(per)
    out["per_book_10pct_wins"] = {"model_beats_conf": wins, "n": n,
        "sign_test_p": float(sum(math.comb(n, i) for i in range(wins, n + 1)) / 2 ** n * 2)}

    json.dump(out, open(f"{OUTD}/summary.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps(o["corpus_totals"], indent=1))
    print(json.dumps(o["reliability_totals"], indent=1))
    print(json.dumps(o["composition"], indent=1))
    print(json.dumps(o["routing_gains"], indent=1))
    print(json.dumps(o["per_book_10pct_wins"], indent=1))
