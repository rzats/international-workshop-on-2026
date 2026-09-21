"""Layout analysis over hOCR word boxes: page furniture, block roles, reading order.

Everything is derived from geometry plus corpus-level statistics; no access to the
page image is required at this stage, which keeps the analysis applicable to the
OCR derivatives that libraries publish alongside their scans.
"""
import json, re, statistics, collections

NORM_MAP = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
    "—": "-", "−": "-", "­": "", " ": " ", "…": "...",
})
WORDCHARS = re.compile(r"[^a-z0-9']+")


def norm_word(s):
    s = s.translate(NORM_MAP).lower()
    s = s.replace("ﬁ", "fi").replace("ﬂ", "fl")
    return WORDCHARS.sub("", s)


def load_pages(key):
    return [json.loads(l) for l in open(f"data/pages/{key}.jsonl")]


def book_stats(pages):
    """Median body x-height, text-area margins and page geometry for one volume."""
    xs, lefts, rights, heights, widths = [], [], [], [], []
    for pg in pages:
        W, H = pg["bbox"][2], pg["bbox"][3]
        if not W or not H:
            continue
        widths.append(W); heights.append(H)
        for b in pg["blocks"]:
            for p in b["pars"]:
                for l in p["lines"]:
                    if l["xs"]:
                        xs.append(l["xs"])
                    lefts.append(l["bbox"][0] / W)
                    rights.append(l["bbox"][2] / W)
    return {
        "xs": statistics.median(xs) if xs else 1.0,
        "left": statistics.median(lefts) if lefts else 0.1,
        "right": statistics.median(rights) if rights else 0.9,
        "W": statistics.median(widths) if widths else 1,
        "H": statistics.median(heights) if heights else 1,
    }


def running_head_index(pages):
    """Normalised text of short top/bottom lines, counted across the volume."""
    cnt = collections.Counter()
    for pg in pages:
        H = pg["bbox"][3] or 1
        for b in pg["blocks"]:
            for p in b["pars"]:
                if len(p["lines"]) != 1:
                    continue
                l = p["lines"][0]
                rel, rel2 = l["bbox"][1] / H, l["bbox"][3] / H
                if rel < 0.18 or rel2 > 0.86:
                    t = head_key(l)
                    if t:
                        cnt[t] += 1
    return cnt


def head_key(line, k=3):
    """Key for recognising a repeated running head.

    The folio is stripped from either end and only the opening words are kept:
    the tail of a running head is often the part the OCR engine garbles, and a
    key built from the whole line would then differ on every page.
    """
    ws = [re.sub(r"\d+", "#", norm_word(w[5])) for w in line["w"]]
    ws = [w for w in ws if w]
    while ws and set(ws[0]) <= {"#", ".", "-", "'"}:
        ws.pop(0)
    while ws and set(ws[-1]) <= {"#", ".", "-", "'"}:
        ws.pop()
    return " ".join(ws[:k])


def classify_par(par, pg, st, heads, n_pages, photos):
    """Assign one of: furniture, heading, caption, footnote, verse, body."""
    H, W = pg["bbox"][3] or 1, pg["bbox"][2] or 1
    lines = par["lines"]
    y0, y1 = par["bbox"][1] / H, par["bbox"][3] / H
    xsz = statistics.median([l["xs"] for l in lines if l["xs"]] or [st["xs"]])
    words = [w for l in lines for w in l["w"]]
    text = " ".join(w[5] for w in words)
    ntext = re.sub(r"\d+", "#", " ".join(norm_word(w[5]) for w in words).strip())


    # caption: small type adjacent to an illustration region
    for ph in photos:
        gap_below = par["bbox"][1] - ph[3]
        gap_above = ph[1] - par["bbox"][3]
        near = (0 <= gap_below < 3 * st["xs"]) or (0 <= gap_above < 3 * st["xs"])
        if near and len(lines) <= 4 and xsz <= 1.05 * st["xs"]:
            return "caption"

    # footnote: distinctly smaller type in the bottom fifth of the page
    if y0 > 0.78 and xsz < 0.85 * st["xs"]:
        return "footnote"

    # heading: larger or all-caps type in a short block
    if len(lines) <= 3:
        caps = sum(1 for w in words if w[5].isupper() and len(w[5]) > 1)
        if xsz >= 1.18 * st["xs"]:
            return "heading"
        if caps >= max(1, 0.7 * len(words)) and len(words) <= 12:
            return "heading"
        if y0 < 0.30 and len(words) <= 10 and re.match(r"^(chapter|book|part|canto)\b", ntext or ""):
            return "heading"

    # verse: most lines stop well short of the measured right margin and the
    # left edges fall on a small set of indent positions
    if len(lines) >= 3:
        right_edge = st["right"] * W
        short = sum(1 for l in lines if l["bbox"][2] < right_edge - 4 * st["xs"])
        indents = {round(l["bbox"][0] / (2 * st["xs"])) for l in lines}
        if short >= 0.75 * len(lines) and len(indents) <= 3:
            return "verse"
    return "body"


def reading_order(pg, st):
    """Column-aware ordering of paragraphs on a page."""
    W = pg["bbox"][2] or 1
    items = []
    for b in pg["blocks"]:
        for p in b["pars"]:
            items.append(p)
    if not items:
        return []
    centres = sorted((p["bbox"][0] + p["bbox"][2]) / 2 / W for p in items)
    ncol = 1
    if len(centres) >= 6:
        gaps = [(centres[i + 1] - centres[i], i) for i in range(len(centres) - 1)]
        g, i = max(gaps)
        if g > 0.22 and 0.25 < (i + 1) / len(centres) < 0.75:
            ncol = 2
            split = (centres[i] + centres[i + 1]) / 2
    if ncol == 1:
        return sorted(items, key=lambda p: (p["bbox"][1], p["bbox"][0]))
    return sorted(items, key=lambda p: (0 if (p["bbox"][0] + p["bbox"][2]) / 2 / W < split else 1,
                                        p["bbox"][1], p["bbox"][0]))


def apply_page_furniture(recs, pg, st, heads, n_pages):
    """Strip running heads, folios and catchwords.

    These repeat on every page of the original and would otherwise be scattered
    through the reflowed text, so they are identified as the single-line
    paragraph at the very top or very bottom of a page whose wording recurs
    across the volume or which is nothing but a page number.
    """
    if not recs:
        return
    H = pg["bbox"][3] or 1
    thresh = max(3, 0.02 * n_pages)
    order = sorted(range(len(recs)), key=lambda i: recs[i]["par"]["bbox"][1])
    for pos, band in ((order[0], "top"), (order[-1], "bot")):
        r = recs[pos]
        lines = r["par"]["lines"]
        if len(lines) != 1:
            continue
        y0, y1 = r["par"]["bbox"][1] / H, r["par"]["bbox"][3] / H
        if band == "top" and y0 > 0.20:
            continue
        if band == "bot" and y1 < 0.85:
            continue
        ws = [w[5] for w in lines[0]["w"]]
        key = head_key(lines[0])
        digits = re.sub(r"\d+", "#", " ".join(norm_word(w) for w in ws)).strip()
        if key and heads.get(key, 0) >= thresh:
            r["role"] = "furniture"
        elif len(ws) <= 3 and re.fullmatch(r"[#\s\-.ivxlc]*", digits or ""):
            r["role"] = "furniture"
        elif "#" in digits and len(ws) <= 9:
            r["role"] = "furniture"


def apply_page_verse(recs, pg, st):
    """Whole-page verse pass.

    OCR engines emit one paragraph per verse line, so a paragraph-local test
    cannot see a stanza. A page of verse is instead recognised by two signals
    that prose pages do not show: most lines stop well short of the right
    margin, and paragraphs are only one or two lines long.
    """
    W = pg["bbox"][2] or 1
    cand = [r for r in recs if r["role"] in ("body", "verse")]
    lines = [l for r in cand for l in r["par"]["lines"]]
    if len(lines) < 8:
        return
    right_edge = st["right"] * W
    short = [l["bbox"][2] < right_edge - 4 * st["xs"] for l in lines]
    frac_short = sum(short) / len(lines)
    mean_lpp = len(lines) / len(cand)
    # In prose a short line ends a paragraph and is followed by an indented
    # first line; in verse it is followed by another flush-left line.
    modal_left = min(l["bbox"][0] for l in lines)
    after, indented = 0, 0
    for i, sh in enumerate(short[:-1]):
        if sh:
            after += 1
            if lines[i + 1]["bbox"][0] - modal_left >= 1.2 * st["xs"]:
                indented += 1
    indent_after_short = indented / after if after else 1.0
    # Rapid dialogue also produces short flush-left paragraphs; verse lines,
    # unlike speech turns, do not begin with a quotation mark.
    starts = [r["par"]["lines"][0]["w"][0][5] for r in cand if r["par"]["lines"][0]["w"]]
    quoted = sum(1 for t in starts if t[:1] in "\"'“‘" or t[:1] == "%") / max(1, len(starts))
    if (frac_short >= 0.55 and mean_lpp <= 2.5
            and indent_after_short < 0.40 and quoted < 0.30):
        for r in cand:
            r["role"] = "verse"


def analyse(key):
    pages = load_pages(key)
    st = book_stats(pages)
    heads = running_head_index(pages)
    out = []
    for pg in pages:
        photos = pg["photos"]
        pars = reading_order(pg, st)
        recs = []
        for p in pars:
            role = classify_par(p, pg, st, heads, len(pages), photos)
            recs.append({"role": role, "par": p})
        apply_page_furniture(recs, pg, st, heads, len(pages))
        apply_page_verse(recs, pg, st)
        out.append({"page": pg, "pars": recs, "photos": photos})
    return out, st


if __name__ == "__main__":
    import sys
    from corpus import CORPUS
    tally = {}
    for key in (sys.argv[1:] or CORPUS):
        doc, st = analyse(key)
        c = collections.Counter(r["role"] for pg in doc for r in pg["pars"])
        tally[key] = dict(c)
        print(key, dict(c), {k: round(v, 3) for k, v in st.items()}, flush=True)
    json.dump(tally, open("data/corpus/role_tally.json", "w"), indent=1)
