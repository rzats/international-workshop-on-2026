"""Ground-truth alignment of OCR word streams against Project Gutenberg e-texts.

The clean e-text of the same work gives a reference transcription. Aligning the
two word streams labels every OCR token as correct, substituted or spurious,
which is what lets us measure how much error a reflowed large-print edition
would actually put in front of a reader.
"""
import os, re, sys, json, bisect, difflib
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS
from structure import analyse, norm_word

CONTENT_ROLES = ("body", "verse", "heading", "caption", "footnote")
NGRAM = 5
MAX_GAP = 400


def ocr_stream(key):
    """Reading-order OCR tokens with provenance; line-end hyphens are joined."""
    doc, st = analyse(key)
    toks = []          # (normalised, [refs]) ; ref = (page, par_id, word_index)
    meta = []          # parallel list of dicts describing each token
    for pi, pg in enumerate(doc):
        for ri, rec in enumerate(pg["pars"]):
            if rec["role"] not in CONTENT_ROLES:
                continue
            lines = rec["par"]["lines"]
            pend = None
            for li, l in enumerate(lines):
                ws = l["w"]
                for wi, w in enumerate(ws):
                    raw, conf = w[5], w[4]
                    geo = [w[0], w[1], w[2], w[3], l["xs"], l["bbox"][1],
                           l["bbox"][0], l["bbox"][2]]
                    ref = (pi, ri, li, wi)
                    last = (wi == len(ws) - 1)
                    if pend is not None:
                        raw = pend[0] + raw
                        refs = pend[1] + [ref]
                        confs = pend[2] + [conf]
                        geos = pend[3] + [geo]
                        pend = None
                    else:
                        refs, confs, geos = [ref], [conf], [geo]
                    if last and li < len(lines) - 1 and raw.endswith(("-", "¬", "‐")):
                        pend = (raw[:-1], refs, confs, geos)
                        continue
                    n = norm_word(raw)
                    if not n:
                        continue
                    toks.append(n)
                    meta.append({"raw": raw, "refs": refs, "conf": confs, "geo": geos,
                                 "role": rec["role"], "page": pi,
                                 "PW": pg["page"]["bbox"][2], "PH": pg["page"]["bbox"][3],
                                 "res": pg["page"]["res"]})
            if pend is not None:
                n = norm_word(pend[0])
                if n:
                    toks.append(n)
                    meta.append({"raw": pend[0], "refs": pend[1], "conf": pend[2],
                                 "geo": pend[3], "role": rec["role"], "page": pi,
                                 "PW": pg["page"]["bbox"][2], "PH": pg["page"]["bbox"][3],
                                 "res": pg["page"]["res"]})
    return doc, st, toks, meta


PG_START = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.S)
PG_END = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.S)


def pg_stream(pgid):
    ids = pgid if isinstance(pgid, tuple) else (pgid,)
    out = []
    for i in ids:
        out.extend(_pg_one(i))
    return out


def _pg_one(pgid):
    txt = open(f"data/raw/pg{pgid}.txt", encoding="utf-8", errors="replace").read()
    m = PG_START.search(txt)
    if m:
        txt = txt[m.end():]
    m = PG_END.search(txt)
    if m:
        txt = txt[:m.start()]
    txt = re.sub(r"(\w)-\n(\w)", r"\1\2", txt)
    toks = [norm_word(t) for t in re.split(r"\s+", txt)]
    return [t for t in toks if t]


def lis(pairs):
    """Longest increasing subsequence over the second coordinate."""
    tails, idx, prev = [], [], [-1] * len(pairs)
    for i, (_, b) in enumerate(pairs):
        j = bisect.bisect_left(tails, b)
        if j == len(tails):
            tails.append(b); idx.append(i)
        else:
            tails[j] = b; idx[j] = i
        prev[i] = idx[j - 1] if j else -1
    if not idx:
        return []
    out, cur = [], idx[-1]
    while cur != -1:
        out.append(pairs[cur]); cur = prev[cur]
    return out[::-1]


def anchors(a, b, n=NGRAM):
    from collections import defaultdict
    ai, bi = defaultdict(list), defaultdict(list)
    for i in range(len(a) - n + 1):
        ai[tuple(a[i:i + n])].append(i)
    for i in range(len(b) - n + 1):
        bi[tuple(b[i:i + n])].append(i)
    pairs = []
    for g, ps in ai.items():
        if len(ps) != 1:
            continue
        qs = bi.get(g)
        if qs and len(qs) == 1:
            pairs.append((ps[0], qs[0]))
    pairs.sort()
    return lis(pairs)


def label(a, b):
    """Per-token labels for stream a (OCR) against reference b."""
    lab = ["unk"] * len(a)
    ref = [None] * len(a)
    anc = anchors(a, b)
    if not anc:
        return lab, ref, 0
    spans = []
    prev = (0, 0)
    for (i, j) in anc:
        spans.append((prev[0], i, prev[1], j))
        prev = (i + NGRAM, j + NGRAM)
        for k in range(NGRAM):
            lab[i + k] = "ok"; ref[i + k] = b[j + k]
    spans.append((prev[0], len(a), prev[1], len(b)))
    for a0, a1, b0, b1 in spans:
        la, lb = a1 - a0, b1 - b0
        if la <= 0 and lb <= 0:
            continue
        # Only score inside short, length-balanced gaps between anchors. Long or
        # lopsided gaps mean the scan and the e-text carry different material
        # (front matter, plates, a different edition) rather than OCR error.
        if max(la, lb) > MAX_GAP or (min(la, lb) + 1) / (max(la, lb) + 1) < 0.5:
            continue
        sm = difflib.SequenceMatcher(None, a[a0:a1], b[b0:b1], autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i1, i2):
                    lab[a0 + k] = "ok"; ref[a0 + k] = b[b0 + j1 + (k - i1)]
            elif tag == "replace":
                for k in range(i1, i2):
                    lab[a0 + k] = "sub"
                    off = b0 + j1 + (k - i1)
                    ref[a0 + k] = b[off] if off < b0 + j2 else None
            elif tag == "delete":
                for k in range(i1, i2):
                    lab[a0 + k] = "ins"; ref[a0 + k] = None
    return lab, ref, len(anc)


def run(key):
    ident, year, pgid, genre, title = CORPUS[key]
    doc, st, toks, meta = ocr_stream(key)
    ptoks = pg_stream(pgid)
    lab, ref, n_anc = label(toks, ptoks)
    for m, L, R in zip(meta, lab, ref):
        m["label"] = L
        m["ref"] = R
    os.makedirs("data/aligned", exist_ok=True)
    with open(f"data/aligned/{key}.jsonl", "w") as f:
        for m in meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    n = len(toks)
    c = {t: sum(1 for L in lab if L == t) for t in ("ok", "sub", "ins", "unk")}
    aligned = n - c["unk"]
    return {"key": key, "ident": ident, "pg": pgid, "genre": genre, "title": title,
            "ocr_tokens": n, "pg_tokens": len(ptoks), "anchors": n_anc,
            "aligned": aligned, "alignable_frac": round(aligned / n, 4) if n else 0,
            "wer_aligned": round((c["sub"] + c["ins"]) / aligned, 4) if aligned else None,
            **{f"n_{k}": v for k, v in c.items()}}


if __name__ == "__main__":
    res = {}
    for key in (sys.argv[1:] or CORPUS):
        r = run(key)
        res[key] = r
        print(json.dumps(r), flush=True)
    json.dump(res, open("data/corpus/align_summary.json", "w"), indent=1)
