"""Render a composed large-print edition to PDF.

Text lines are drawn as text; facsimile strips and illustrations are drawn as
crops of the source page image, so the output is a single document mixing
reflowed type with magnified images of the original setting.
"""
import os, sys, io, json, math, requests
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS
import engine as E

IMGD = "data/scans"
REQ_W = 1800
PROBE_W = 160


MISSING = set()


def page_image(ident, n):
    """Fetch a page image; returns None for leaves the item does not publish."""
    if n < 0 or (ident, n) in MISSING:
        return None
    os.makedirs(f"{IMGD}/{ident}", exist_ok=True)
    p = f"{IMGD}/{ident}/n{n}_w{REQ_W}.jpg"
    if not os.path.exists(p):
        url = f"https://archive.org/download/{ident}/page/n{n}_w{REQ_W}.jpg"
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
        except Exception:
            MISSING.add((ident, n))
            return None
        open(p, "wb").write(r.content)
    return p


def _probe(ident, leaf, w=PROBE_W):
    p = f"{IMGD}/{ident}/probe_n{leaf}_w{w}.jpg"
    if not os.path.exists(p):
        os.makedirs(f"{IMGD}/{ident}", exist_ok=True)
        try:
            r = requests.get(
                f"https://archive.org/download/{ident}/page/n{leaf}_w{w}.jpg", timeout=90)
            r.raise_for_status()
            open(p, "wb").write(r.content)
        except Exception:
            return None
    try:
        im = Image.open(p)
        return im.height / im.width
    except Exception:
        return None


def leaf_offset(key, ident, pages, span=8):
    """Recover the offset between hOCR page order and Internet Archive leaf numbers.

    Not every published hOCR carries usable page numbers - some derivatives
    report ppageno 0 for every page - so the offset is recovered by matching the
    aspect ratio of a few sample leaves against the page rectangles in the hOCR.
    """
    cachep = f"{IMGD}/{ident}/offset.json"
    if os.path.exists(cachep):
        return json.load(open(cachep))["offset"]
    n = len(pages)
    samples = [i for i in (int(n * f) for f in (0.25, 0.45, 0.65, 0.85)) if 0 <= i < n]
    order = sorted(range(-span, span + 1), key=lambda d: (abs(d), d))
    best, best_hits = 0, -1
    for d in order:
        if min(samples) + d < 0:
            continue
        hits = 0
        for i in samples:
            a = _probe(ident, i + d)
            b = pages[i]["bbox"]
            if a is None or not b[2]:
                continue
            if abs(a - b[3] / b[2]) < 0.004:
                hits += 1
        if hits > best_hits:                    # ties keep the smallest shift
            best, best_hits = d, hits
        if hits == len(samples):
            break
    os.makedirs(f"{IMGD}/{ident}", exist_ok=True)
    json.dump({"offset": best, "hits": best_hits, "samples": len(samples)},
              open(cachep, "w"))
    return best


_OFFSET = {}
_CACHE = {}


def offset_for(key):
    if key not in _OFFSET:
        ident = CORPUS[key][0]
        pages = [json.loads(l) for l in open(f"data/pages/{key}.jsonl")]
        _OFFSET[key] = leaf_offset(key, ident, pages)
    return _OFFSET[key]


def crop(ident, n, box, src_w, slope=0.0):
    """Crop a region given in hOCR pixel coordinates from the fetched page image.

    Scans of bound volumes and of microfilm are rarely square to the page, so a
    rectangular crop of a sloping line catches the descenders of its neighbours.
    The baseline slope that the OCR engine already reports is used to rotate the
    crop upright before it is placed.
    """
    key = (ident, n)
    if key not in _CACHE:
        if len(_CACHE) > 6:
            _CACHE.clear()
        path = page_image(ident, n)
        _CACHE[key] = Image.open(path).convert("L") if path else None
    im = _CACHE[key]
    if im is None:
        return None
    k = im.width / float(src_w)
    x0, y0, x1, y1 = [v * k for v in box]
    pad = 1
    if abs(slope) > 0.002:
        h = y1 - y0
        m = abs(slope) * (x1 - x0) / 2.0 + pad
        wide = im.crop((max(0, int(x0 - pad)), max(0, int(y0 - m)),
                        min(im.width, int(x1 + pad)), min(im.height, int(y1 + m))))
        rot = wide.rotate(math.degrees(math.atan(slope)), resample=Image.BICUBIC,
                          expand=False, fillcolor=int(wide.resize((1, 1)).getpixel((0, 0))))
        top = max(0, (rot.height - (h + 2 * pad)) / 2.0)
        return rot.crop((0, int(top), rot.width, int(top + h + 2 * pad)))
    return im.crop((max(0, int(x0 - pad)), max(0, int(y0 - pad)),
                    min(im.width, int(x1 + pad)), min(im.height, int(y1 + pad))))


def render(key, items, pages, out_pdf, limit=None, footer=True):
    ident = CORPUS[key][0]
    S = E.SPEC
    c = canvas.Canvas(out_pdf, pagesize=(S["pw"], S["ph"]))
    c.setTitle(f"{CORPUS[key][4]} - large-print edition")
    shown = pages[:limit] if limit else pages
    off = offset_for(key)
    for pnum, page in enumerate(shown, 1):
        y = S["ph"] - S["margin"]
        for i in page:
            it = items[i]
            if it["t"] == "line":
                y -= it["size"] * S["lead"]
                x = S["margin"] + it.get("indent", 0.0)
                c.setFont("AH-Bold" if it.get("role") == "heading" else "AH", it["size"])
                c.setFillGray(0)
                c.drawString(x, y, " ".join(it["words"]))
                y -= it["h"] - it["size"] * S["lead"]
            elif it["t"] == "strip":
                h = it["h"] - S["strip_gap"]
                y -= h
                img = crop(ident, it["page"] + off, it["src"], it["pw"], it.get("slope", 0.0))
                if img is not None:
                    c.drawImage(ImageReader(img), S["margin"] + it.get("indent", 0.0), y,
                                width=it["w"], height=h, mask=None)
                y -= S["strip_gap"]
            elif it["t"] == "fig":
                h = it["h"] - S["fig_gap"]
                y -= h
                img = crop(ident, it["page"], it["src"], it["pw"])
                c.drawImage(ImageReader(img), S["margin"] + (S["measure"] - it["w"]) / 2,
                            y, width=it["w"], height=h, mask=None)
                y -= S["fig_gap"]
        if footer:
            c.setFont("AH", 12)
            c.setFillGray(0.35)
            c.drawCentredString(S["pw"] / 2, S["margin"] / 2.2, str(pnum))
        c.showPage()
    c.save()
    return out_pdf


def build(key, cov_loss=0.10, limit=None, tag="", first_page=0):
    segs, st = E.document(key)
    scores = E.score_model(segs)
    route, _ = E.route_by_score(segs, scores, cov_loss)
    items = E.build_items(segs, route)
    pages = E.paginate(items)
    os.makedirs("data/render", exist_ok=True)
    out = f"data/render/{key}{tag}.pdf"
    sel = pages[first_page:first_page + limit] if limit else pages
    render(key, items, sel, out, limit=None)
    return out, len(pages), route, items, pages


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "carol"
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    cov = float(sys.argv[3]) if len(sys.argv) > 3 else 0.10
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    out, n, *_ = build(key, cov_loss=cov, limit=lim, tag=f"_c{int(cov*100)}",
                       first_page=first)
    print(out, "pages composed:", n, "rendered:", lim)
