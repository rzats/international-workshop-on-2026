"""Large-print composition: routing, reflow and re-imposition.

The output edition is composed from two kinds of material. Reliable OCR text is
reflowed as real text at the target type size; unreliable passages are kept as
images of the original lines, magnified to the same target x-height and
re-imposed so that they still fit the measure. Both kinds of material are then
paginated by a single dynamic program under typographic constraints.
"""
import os, sys, json, math
import numpy as np
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS
from structure import analyse

FONT_DIR = "assets/fonts"
for name, fn in (("AH", "AtkinsonHyperlegible-Regular.ttf"),
                 ("AH-Bold", "AtkinsonHyperlegible-Bold.ttf"),
                 ("AH-Italic", "AtkinsonHyperlegible-Italic.ttf")):
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, fn)))

# A4 page, 20 mm margins; 18 pt body is the lower bound of the large-print range
# recommended by sight-loss organisations, and no element is set below 16 pt.
SPEC = {
    "pw": 595.276, "ph": 841.89, "margin": 56.693,
    "body": 18.0, "lead": 1.40, "head": 22.0, "small": 16.0,
    "head_before": 16.0, "head_after": 8.0, "para_gap": 6.0,
    "strip_gap": 7.2, "runover": 27.0, "fig_gap": 12.0,
}
SPEC["measure"] = SPEC["pw"] - 2 * SPEC["margin"]
SPEC["avail"] = SPEC["ph"] - 2 * SPEC["margin"]

ROLE_SIZE = {"body": "body", "verse": "body", "heading": "head",
             "caption": "small", "footnote": "small"}


def size_for(role):
    return SPEC[ROLE_SIZE.get(role, "body")]


def wid(text, size, bold=False):
    return pdfmetrics.stringWidth(text, "AH-Bold" if bold else "AH", size)


# ---------------------------------------------------------------- document model

def document(key):
    """Reading-order segments for one volume, carrying labels and predictions."""
    doc, st = analyse(key)
    p_err = np.load(f"data/reliability/{key}.npy")
    bl_by_par = {}
    for pi, pg in enumerate(doc):
        for ri, rec in enumerate(pg["pars"]):
            bl_by_par[(pi, ri)] = [l.get("bl") or [0.0, 0.0] for l in rec["par"]["lines"]]
    toks_by_par = {}
    i = 0
    for line in open(f"data/aligned/{key}.jsonl"):
        r = json.loads(line)
        ref = r["refs"][0]
        # A word hyphenated over a line break carries boxes from two source
        # lines; each box must be credited to the line it actually sits on, or
        # the line rectangle -- and with it every facsimile crop -- grows to
        # span both lines.
        parts = {}
        for rf, g in zip(r["refs"], r["geo"]):
            parts.setdefault(rf[2], []).append(g)
        own = parts[ref[2]]
        toks_by_par.setdefault((ref[0], ref[1]), []).append({
            "raw": r["raw"], "line": ref[2],
            "err": r["label"] not in ("ok", "unk"),
            "scorable": r["label"] != "unk",
            "p": float(p_err[i]),
            "conf": min(r["conf"]) if r["conf"] else 0,
            "box": (own[0][0], min(g[1] for g in own),
                    own[-1][2], max(g[3] for g in own)),
            "extra": [(li, (gs[0][0], min(g[1] for g in gs),
                            gs[-1][2], max(g[3] for g in gs)))
                      for li, gs in parts.items() if li != ref[2]],
            "xs": r["geo"][0][4] or st["xs"],
        })
        i += 1
    assert i == len(p_err), (i, len(p_err))

    segs = []
    for pi, pg in enumerate(doc):
        res = pg["page"]["res"] or 300
        items = []
        for ri, rec in enumerate(pg["pars"]):
            toks = toks_by_par.get((pi, ri))
            if not toks:
                continue
            lines, extents = {}, {}
            for t in toks:
                lines.setdefault(t["line"], []).append(t)
                extents.setdefault(t["line"], []).append(t["box"])
                for li, b in t["extra"]:
                    extents.setdefault(li, []).append(b)
            bls = bl_by_par.get((pi, ri), [])
            lb = []
            for li in sorted(lines):
                ts, ex = lines[li], extents[li]
                bl = bls[li] if li < len(bls) else [0.0, 0.0]
                lb.append({
                    "box": (min(b[0] for b in ex), min(b[1] for b in ex),
                            max(b[2] for b in ex), max(b[3] for b in ex)),
                    "xs": ts[0]["xs"] or st["xs"],
                    "slope": float(bl[0]) if bl else 0.0,
                    "toks": ts,
                })
            items.append({"kind": "par", "role": rec["role"], "toks": toks,
                          "lines": lb, "y": rec["par"]["bbox"][1], "res": res,
                          "page": pi, "pw": pg["page"]["bbox"][2],
                          "ph": pg["page"]["bbox"][3]})
        for ph in pg["photos"]:
            if (ph[2] - ph[0]) < 0.15 * (pg["page"]["bbox"][2] or 1):
                continue
            items.append({"kind": "fig", "box": ph, "y": ph[1], "res": res,
                          "page": pi, "pw": pg["page"]["bbox"][2],
                          "ph": pg["page"]["bbox"][3]})
        items.sort(key=lambda it: it["y"])
        segs.extend(items)
    return segs, st


# ---------------------------------------------------------------- reflow (text)

def kp_ragged(words, size, measure, first_indent=0.0):
    """Optimal ragged-right line breaking (Knuth-Plass with fixed interword glue).

    Justification is avoided because stretched word spacing is a known obstacle
    for low-vision readers; what is optimised instead is the evenness of the
    right-hand edge.
    """
    n = len(words)
    if n == 0:
        return []
    w = [wid(t, size) for t in words]
    sp = wid(" ", size)
    best = [math.inf] * (n + 1)
    prev = [0] * (n + 1)
    best[0] = 0.0
    for j in range(1, n + 1):
        total = 0.0
        for i in range(j - 1, -1, -1):
            total = sum(w[i:j]) + sp * (j - i - 1) if i == j - 1 else total + w[i] + sp
            avail = measure - (first_indent if i == 0 else 0.0)
            if total > avail:
                if i == j - 1:
                    cost = best[i] + 1e9
                    if cost < best[j]:
                        best[j], prev[j] = cost, i
                break
            slack = avail - total
            # Demerits in the manner of Knuth and Plass, but with the badness of a
            # line measured by how far short of the measure it stops.
            pen = 0.0 if j == n else (1.0 + 100.0 * (slack / avail) ** 3) ** 2
            cost = best[i] + pen + 1.0
            if cost < best[j]:
                best[j], prev[j] = cost, i
    out, j = [], n
    while j > 0:
        i = prev[j]
        out.append(words[i:j])
        j = i
    return out[::-1]


def greedy(words, size, measure, first_indent=0.0):
    sp = wid(" ", size)
    lines, cur, cw = [], [], 0.0
    for t in words:
        tw = wid(t, size)
        avail = measure - (first_indent if not lines else 0.0)
        add = tw if not cur else sp + tw
        if cur and cw + add > avail:
            lines.append(cur); cur, cw = [t], tw
        else:
            cur.append(t); cw += add
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------- re-imposition (facsimile)

def strips(seg, target=None):
    """Cut a segment's source lines into magnified image strips that fit the measure.

    Each source line is scaled so that its type reaches the target size; a line
    whose magnified image is wider than the measure is divided at an interword
    gap and continued on the next strip with a run-over indent.
    """
    target = target or SPEC["body"]
    out = []
    for ln in seg["lines"]:
        xs = ln["xs"] or 1.0
        scale = target / xs                      # points per source pixel
        x0, y0, x1, y1 = ln["box"]
        h = (y1 - y0) * scale
        pieces = [(x0, x1)]
        if (x1 - x0) * scale > SPEC["measure"]:
            gaps = []
            ts = sorted(ln["toks"], key=lambda t: t["box"][0])
            for a, b in zip(ts, ts[1:]):
                gaps.append(((a["box"][2] + b["box"][0]) / 2, b["box"][0] - a["box"][2]))
            pieces, cur, budget = [], x0, SPEC["measure"]
            while (x1 - cur) * scale > budget:
                limit = cur + budget / scale
                cand = [g for g, _ in gaps if cur < g < limit]
                cut = cand[-1] if cand else limit
                pieces.append((cur, cut))
                cur = cut
                budget = SPEC["measure"] - SPEC["runover"]
            pieces.append((cur, x1))
        for k, (a, b) in enumerate(pieces):
            out.append({"kind": "strip", "page": seg["page"], "res": seg["res"],
                        "pw": seg["pw"], "src": (a, y0, b, y1), "scale": scale,
                        "slope": ln.get("slope", 0.0),
                        "w": (b - a) * scale, "h": h,
                        "indent": SPEC["runover"] if k else 0.0})
    return out


# ---------------------------------------------------------------- item stream

def line_advance(size):
    return size * SPEC["lead"]


def build_items(segs, route, breaker=kp_ragged, cache=None):
    """Flatten segments into atomic vertical items ready for pagination.

    Line breaking and strip planning depend only on a segment, never on the
    routing decision, so results are memoised across the operating points.
    """
    cache = {} if cache is None else cache
    items = []
    for si, seg in enumerate(segs):
        if seg["kind"] == "fig":
            x0, y0, x1, y1 = seg["box"]
            sc = min(SPEC["measure"] / max(1, x1 - x0),
                     0.45 * SPEC["avail"] / max(1, y1 - y0)) * 1.0
            dpi = seg["res"] or 300
            w = (x1 - x0) * 72.0 / dpi
            h = (y1 - y0) * 72.0 / dpi
            k = min(SPEC["measure"] / w, 0.5 * SPEC["avail"] / h, 2.0)
            items.append({"t": "fig", "h": h * k + SPEC["fig_gap"], "seg": si,
                          "first": True, "last": True, "keep": False,
                          "w": w * k, "src": seg["box"], "page": seg["page"],
                          "res": seg["res"], "pw": seg["pw"], "toks": []})
            continue
        role = seg["role"]
        size = size_for(role)
        if route[si] == "fac":
            ck = ("fac", si)
            if ck not in cache:
                cache[ck] = strips(seg, target=size)
            ss = cache[ck]
            for j, s in enumerate(ss):
                items.append({"t": "strip", "h": s["h"] + SPEC["strip_gap"], "seg": si,
                              "first": j == 0, "last": j == len(ss) - 1,
                              "keep": role == "heading", "role": role,
                              "src": s["src"], "scale": s["scale"], "w": s["w"],
                              "indent": s["indent"], "page": s["page"],
                              "res": s["res"], "pw": s["pw"],
                              "slope": s.get("slope", 0.0),
                              "toks": [] if j else seg["toks"]})
            continue
        indent = SPEC["runover"] if role == "body" else 0.0
        ck = ("txt", si, breaker.__name__)
        if ck not in cache:
            if role == "verse":
                # verse keeps its source line division instead of being reflowed
                ls = []
                for ln in seg["lines"]:
                    ws = [t["raw"] for t in ln["toks"]]
                    ls.extend(breaker(ws, size, SPEC["measure"] - SPEC["runover"]))
            else:
                ls = breaker([t["raw"] for t in seg["toks"]], size,
                             SPEC["measure"], first_indent=indent)
            cache[ck] = ls
        ls = cache[ck]
        adv = line_advance(size)
        for j, ln in enumerate(ls):
            items.append({"t": "line", "h": adv + (SPEC["para_gap"] if j == len(ls) - 1 else 0),
                          "seg": si, "first": j == 0, "last": j == len(ls) - 1,
                          "keep": role == "heading", "role": role, "size": size,
                          "words": ln, "indent": indent if (j == 0 and role == "body") else
                          (SPEC["runover"] if role == "verse" and j else 0.0),
                          "toks": seg["toks"] if j == 0 else []})
        if role == "heading" and items:
            items[-1]["h"] += SPEC["head_after"]
            items[len(items) - len(ls)]["h"] += SPEC["head_before"]
    return items


# ---------------------------------------------------------------- pagination

HARD = 1e6
W_PAGE = 1e4


def break_penalty(items, j):
    """Cost of starting a new page immediately before item j."""
    if j <= 0 or j >= len(items):
        return 0.0
    prev, cur = items[j - 1], items[j]
    pen = 0.0
    if prev.get("keep") and prev["t"] in ("line", "strip"):
        return HARD                                   # heading stranded at page foot
    if prev["seg"] == cur["seg"]:
        if prev["first"]:
            pen += HARD                               # orphan: one opening line left behind
        if cur["last"] and not cur["first"]:
            pen += HARD                               # widow: one closing line carried over
    if prev["seg"] != cur["seg"]:
        # a heading may not be separated from the first two lines it introduces
        k = j - 1
        while k >= 0 and items[k]["seg"] == prev["seg"]:
            k -= 1
        if k >= 0 and items[k].get("keep") and (j - 1 - k) < 2:
            pen += HARD
    return pen


def paginate(items, constrained=True):
    """Optimal page breaking (DP). Without constraints this reduces to first-fit."""
    n = len(items)
    avail = SPEC["avail"]
    if not constrained:
        pages, used, cur = [], 0.0, []
        for i, it in enumerate(items):
            if cur and used + it["h"] > avail:
                pages.append(cur); cur, used = [], 0.0
            cur.append(i); used += it["h"]
        if cur:
            pages.append(cur)
        return pages
    best = [math.inf] * (n + 1)
    prev = [0] * (n + 1)
    best[0] = 0.0
    for i in range(n):
        if best[i] == math.inf:
            continue
        used = 0.0
        for j in range(i, n):
            used += items[j]["h"]
            if used > avail and j > i:
                break
            slack = max(0.0, avail - used)
            fill = 40.0 * (slack / avail) ** 2 if j + 1 < n else 0.0
            cost = best[i] + W_PAGE + fill + break_penalty(items, j + 1)
            if cost < best[j + 1]:
                best[j + 1], prev[j + 1] = cost, i
    pages, j = [], n
    while j > 0:
        i = prev[j]
        pages.append(list(range(i, j)))
        j = i
    return pages[::-1]


def violations(items, pages):
    v = {"widow": 0, "orphan": 0, "split_heading": 0, "overfull": 0}
    for p in pages:
        if sum(items[i]["h"] for i in p) > SPEC["avail"] + 1e-6 and len(p) > 1:
            v["overfull"] += 1
    for p in pages[1:]:
        j = p[0]
        prev, cur = items[j - 1], items[j]
        if prev.get("keep") and prev["t"] in ("line", "strip"):
            v["split_heading"] += 1
        if prev["seg"] == cur["seg"]:
            if prev["first"]:
                v["orphan"] += 1
            if cur["last"] and not cur["first"]:
                v["widow"] += 1
    return v


# ---------------------------------------------------------------- routing

def seg_costs(segs):
    """Expected exposed errors and the height of each routing choice per segment."""
    rows = []
    for si, seg in enumerate(segs):
        if seg["kind"] == "fig":
            rows.append({"e": 0.0, "h_text": 0.0, "h_fac": 0.0, "n": 0, "fig": True})
            continue
        size = size_for(seg["role"])
        words = [t["raw"] for t in seg["toks"]]
        if seg["role"] == "verse":
            nl = sum(len(kp_ragged([t["raw"] for t in ln["toks"]], size,
                                   SPEC["measure"] - SPEC["runover"]))
                     for ln in seg["lines"])
        else:
            nl = len(kp_ragged(words, size, SPEC["measure"],
                               first_indent=SPEC["runover"] if seg["role"] == "body" else 0.0))
        h_text = nl * line_advance(size) + SPEC["para_gap"]
        ss = strips(seg, target=size)
        h_fac = sum(s["h"] + SPEC["strip_gap"] for s in ss)
        rows.append({"e": float(sum(t["p"] for t in seg["toks"])),
                     "h_text": h_text, "h_fac": h_fac,
                     "n": len(seg["toks"]), "fig": False})
    return rows


def route_all(segs, mode):
    return {i: ("fac" if mode == "fac" else "text") for i in range(len(segs))}


def route_conf(segs, tau):
    """Ablation: route on the OCR engine's own confidence with a fixed threshold."""
    r = {}
    for i, s in enumerate(segs):
        if s["kind"] == "fig" or not s["toks"]:
            r[i] = "text"; continue
        m = sum(t["conf"] for t in s["toks"]) / len(s["toks"])
        r[i] = "fac" if m < tau else "text"
    return r


def route_by_score(segs, scores, cov_loss):
    """Move the highest-scoring segments to facsimile until the coverage budget is spent.

    Every selector under comparison is applied through this same procedure, so
    the methods differ only in how they rank segments, never in how much text
    they are allowed to withdraw from the reflowable layer.
    """
    n_tok = [len(s["toks"]) if s["kind"] == "par" else 0 for s in segs]
    total = sum(n_tok)
    budget = cov_loss * total
    order = sorted((i for i in range(len(segs)) if n_tok[i]),
                   key=lambda i: -scores[i])
    r = {i: "text" for i in range(len(segs))}
    spent = 0.0
    for i in order:
        if spent + n_tok[i] <= budget:
            r[i] = "fac"
            spent += n_tok[i]
    return r, (spent / total if total else 0.0)


def score_model(segs):
    return [(sum(t["p"] for t in s["toks"]) / len(s["toks"]))
            if s["kind"] == "par" and s["toks"] else -1.0 for s in segs]


def score_conf(segs):
    return [(-sum(t["conf"] for t in s["toks"]) / len(s["toks"]))
            if s["kind"] == "par" and s["toks"] else -1e9 for s in segs]


def score_oracle(segs):
    return [(sum(1 for t in s["toks"] if t["err"]) / len(s["toks"]))
            if s["kind"] == "par" and s["toks"] else -1.0 for s in segs]


def score_random(segs, seed=0):
    rng = np.random.default_rng(seed)
    return [float(rng.random()) if s["kind"] == "par" and s["toks"] else -1.0
            for s in segs]


# ------------------------------------------------- whole-page magnification baseline

def facsimile_zoom(key, segs, page_width=None):
    """Cost of the obvious alternative: magnify each scanned page and tile it.

    The baseline is given every advantage: the page is cropped to its text
    block before magnification, and tiles are counted only where the magnified
    block genuinely exceeds the A4 text area.
    """
    import collections
    by_page = collections.defaultdict(list)
    for s in segs:
        by_page[s["page"]].append(s)
    all_xs = [ln["xs"] for s in segs if s["kind"] == "par" for ln in s["lines"] if ln["xs"]]
    book_xs = float(np.median(all_xs)) if all_xs else 1.0
    pages, fit_crop, fit_full, achieved = 0, 0, 0, []
    for pi, items in by_page.items():
        boxes, xss = [], []
        for s in items:
            if s["kind"] == "fig":
                boxes.append(s["box"])
            else:
                for ln in s["lines"]:
                    boxes.append(ln["box"])
                    if ln["xs"]:
                        xss.append(ln["xs"])
        if not boxes:
            continue
        x0 = min(b[0] for b in boxes); x1 = max(b[2] for b in boxes)
        y0 = min(b[1] for b in boxes); y1 = max(b[3] for b in boxes)
        xs = float(np.median(xss)) if xss else book_xs
        scale = SPEC["body"] / xs
        w, h = (x1 - x0) * scale, (y1 - y0) * scale
        cols = max(1, math.ceil(w / SPEC["measure"] - 1e-9))
        rows = max(1, math.ceil(h / SPEC["avail"] - 1e-9))
        pages += cols * rows
        # type size reachable if the page is shown whole, cropped or uncropped
        pt_crop = xs * SPEC["measure"] / max(1e-6, x1 - x0)
        achieved.append(pt_crop)
        fit_crop += pt_crop >= SPEC["body"] - 1e-9
        if page_width:
            fit_full += xs * SPEC["measure"] / max(1e-6, page_width) >= SPEC["body"] - 1e-9
    n = len(by_page)
    return {"pages": pages, "src_pages": n,
            "no_pan_frac": fit_crop / n if n else 0.0,
            "no_pan_frac_full": fit_full / n if n else 0.0,
            "achieved_pt_median": float(np.median(achieved)) if achieved else 0.0}
