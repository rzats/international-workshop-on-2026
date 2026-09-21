"""Per-token reliability estimation.

Library OCR derivatives are produced by different engines over several decades,
so the confidence values attached to them are not comparable across items. This
module builds features that are either engine-agnostic (lexicon, shape,
geometry) or normalised within an item, fits a logistic model, and evaluates it
leave-one-volume-out so that the reported numbers reflect transfer to an unseen
volume rather than within-volume fitting.
"""
import os, sys, json, math, re
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS
from lexicon import lexicon
from structure import norm_word

FEATS = ["conf_pct", "conf_z", "conf_raw01", "in_lex", "in_lex_lower", "len",
         "nonalpha", "has_digit", "mixed_case", "run_nonalpha", "isolated",
         "nb_conf_pct", "nb_in_lex", "xs_dev", "h_dev", "aspect_dev",
         "y_rel", "n_merge", "role_body", "role_head", "role_verse",
         "role_note", "role_cap"]

VOWELS = set("aeiouy")


def load(key):
    return [json.loads(l) for l in open(f"data/aligned/{key}.jsonl")]


def token_feats(recs):
    lex = lexicon()
    n = len(recs)
    conf = np.array([min(r["conf"]) if r["conf"] else 0 for r in recs], float)
    # within-item normalisation: rank-percentile and z-score of the raw value
    order = conf.argsort(kind="mergesort")
    pct = np.empty(n); pct[order] = np.linspace(0, 1, n, endpoint=False)
    z = (conf - conf.mean()) / (conf.std() + 1e-6)

    xs = np.array([r["geo"][0][4] or 1.0 for r in recs], float)
    xs_med = np.median(xs[xs > 0]) if (xs > 0).any() else 1.0
    h = np.array([max(1, r["geo"][0][3] - r["geo"][0][1]) for r in recs], float)
    w = np.array([max(1, r["geo"][-1][2] - r["geo"][0][0]) for r in recs], float)
    h_med = np.median(h)

    norm = [norm_word(r["raw"]) for r in recs]
    in_lex = np.array([1.0 if t in lex else 0.0 for t in norm])
    in_lex_lo = np.array([1.0 if (t.rstrip("s") in lex or t.rstrip("'") in lex) else 0.0
                          for t in norm])
    length = np.array([len(t) for t in norm], float)
    nonalpha = np.array([sum(1 for c in r["raw"] if not c.isalnum()) / max(1, len(r["raw"]))
                         for r in recs])
    has_digit = np.array([1.0 if any(c.isdigit() for c in r["raw"]) else 0.0 for r in recs])
    mixed = np.array([1.0 if re.search(r"[a-z][A-Z]", r["raw"]) else 0.0 for r in recs])
    run_na = np.array([1.0 if re.search(r"[^\w\s]{2,}", r["raw"]) else 0.0 for r in recs])
    # a one- or two-letter token that is not a real English short word
    isolated = np.array([1.0 if (len(t) <= 2 and t not in
                                 {"a", "i", "an", "as", "at", "be", "by", "do", "go", "he",
                                  "if", "in", "is", "it", "me", "my", "no", "of", "on", "or",
                                  "so", "to", "up", "us", "we", "am", "oh", "ah"}) else 0.0
                         for t in norm])

    def neigh(v):
        p = np.pad(v, 2, mode="edge")
        return (p[:-4] + p[1:-3] + p[3:-1] + p[4:]) / 4.0

    X = np.column_stack([
        pct, z, conf / 100.0, in_lex, in_lex_lo, np.minimum(length, 20) / 20.0,
        nonalpha, has_digit, mixed, run_na, isolated,
        neigh(pct), neigh(in_lex),
        np.clip(xs / xs_med - 1, -1, 1), np.clip(h / h_med - 1, -1, 1),
        np.clip((w / h) / (length + 1) - 0.5, -1, 1),
        np.array([r["geo"][0][5] / max(1, r["PH"]) for r in recs]),
        np.array([min(len(r["refs"]), 3) / 3.0 for r in recs]),
        np.array([1.0 if r["role"] == "body" else 0.0 for r in recs]),
        np.array([1.0 if r["role"] == "heading" else 0.0 for r in recs]),
        np.array([1.0 if r["role"] == "verse" else 0.0 for r in recs]),
        np.array([1.0 if r["role"] == "footnote" else 0.0 for r in recs]),
        np.array([1.0 if r["role"] == "caption" else 0.0 for r in recs]),
    ])
    y = np.array([0 if r["label"] == "ok" else 1 for r in recs], float)
    scorable = np.array([r["label"] != "unk" for r in recs])
    return X, y, scorable


FDIR = "data/features"


def build_all(keys=None):
    """Materialise per-volume feature matrices on disk.

    The machine this runs on has little memory, so each volume is featurised
    and released before the next one is read.
    """
    os.makedirs(FDIR, exist_ok=True)
    for k in (keys or list(CORPUS)):
        if os.path.exists(f"{FDIR}/{k}_X.npy"):
            continue
        recs = load(k)
        X, y, s = token_feats(recs)
        np.save(f"{FDIR}/{k}_X.npy", X.astype(np.float32))
        np.save(f"{FDIR}/{k}_y.npy", y.astype(np.int8))
        np.save(f"{FDIR}/{k}_s.npy", s)
        del recs, X, y, s


def feats(k):
    return (np.load(f"{FDIR}/{k}_X.npy"),
            np.load(f"{FDIR}/{k}_y.npy").astype(np.float64),
            np.load(f"{FDIR}/{k}_s.npy"))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def ece(p, y, bins=10):
    idx = np.clip((p * bins).astype(int), 0, bins - 1)
    e = 0.0
    for b in range(bins):
        m = idx == b
        if m.sum():
            e += m.sum() / len(p) * abs(p[m].mean() - y[m].mean())
    return e


def auc(p, y):
    o = p.argsort()
    r = np.empty(len(p)); r[o] = np.arange(1, len(p) + 1)
    # average ranks for ties
    s = np.sort(p)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        if j > i:
            r[(p >= s[i]) & (p <= s[j])] = (i + j + 2) / 2.0
        i = j + 1
    n1, n0 = y.sum(), (1 - y).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


CAP = 40000   # training tokens sampled per volume


def loo_cv(keys, cols=None, seed=0):
    """Leave-one-volume-out fit; the held-out volume is never seen in training."""
    from sklearn.linear_model import LogisticRegression
    cols = cols if cols is not None else list(range(len(FEATS)))
    rng = np.random.default_rng(seed)
    cache = {}
    for k in keys:
        X, y, s = feats(k)
        Xs, ys = X[s][:, cols], y[s]
        if len(ys) > CAP:
            idx = rng.choice(len(ys), CAP, replace=False)
            Xs, ys = Xs[idx], ys[idx]
        cache[k] = (Xs.astype(np.float32), ys.astype(np.float32))
    out = {}
    for held in keys:
        Xtr = np.vstack([cache[k][0] for k in keys if k != held])
        ytr = np.concatenate([cache[k][1] for k in keys if k != held])
        clf = LogisticRegression(max_iter=3000, C=1.0)
        clf.fit(Xtr, ytr)
        del Xtr, ytr
        X, y, s = feats(held)
        p_all = clf.predict_proba(X[:, cols])[:, 1]
        p, yv = p_all[s], y[s]
        out[held] = {"p": p_all, "auc": auc(p, yv), "ece": ece(p, yv),
                     "base": float(yv.mean()), "n": int(s.sum()),
                     "coef": dict(zip([FEATS[c] for c in cols],
                                      np.round(clf.coef_[0], 3).tolist()))}
        del X, y, s
    return out


if __name__ == "__main__":
    os.makedirs("data/reliability", exist_ok=True)
    keys = list(CORPUS)
    build_all(keys)
    res = loo_cv(keys)
    summ = {}
    for k, r in res.items():
        np.save(f"data/reliability/{k}.npy", r["p"].astype(np.float32))
        summ[k] = {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                   for kk, vv in r.items() if kk not in ("p", "coef")}
        print(k, summ[k], flush=True)

    # single-feature ranking baselines
    rows, pooled_raw, pooled_pct, pooled_y = [], [], [], []
    for k in keys:
        X, y, s = feats(k)
        raw, pct, yv = X[s][:, 2], X[s][:, 0], y[s]
        rows.append((k, auc(-raw, yv), auc(-pct, yv)))
        pooled_raw.append(raw); pooled_pct.append(pct); pooled_y.append(yv)
        del X, y, s
    pr = np.concatenate(pooled_raw); pp = np.concatenate(pooled_pct)
    py = np.concatenate(pooled_y)
    print("\nranking AUC (raw conf / within-item percentile):")
    for k, a, b in rows:
        print(f"  {k:14s} {a:.3f} {b:.3f}")
    print("pooled raw-conf AUC", round(auc(-pr, py), 4),
          "pooled pct AUC", round(auc(-pp, py), 4))
    json.dump({"loo": summ,
               "coef": res[keys[0]]["coef"],
               "raw_conf_auc": {k: round(a, 4) for k, a, _ in rows},
               "pct_auc": {k: round(b, 4) for k, _, b in rows},
               "pooled_raw_conf_auc": round(auc(-pr, py), 4),
               "pooled_pct_auc": round(auc(-pp, py), 4)},
              open("data/corpus/reliability_summary.json", "w"), indent=1)
