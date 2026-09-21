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


def page_image(ident, n):
    os.makedirs(f"{IMGD}/{ident}", exist_ok=True)
    p = f"{IMGD}/{ident}/n{n}_w{REQ_W}.jpg"
    if not os.path.exists(p):
        url = f"https://archive.org/download/{ident}/page/n{n}_w{REQ_W}.jpg"
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        open(p, "wb").write(r.content)
    return p


_CACHE = {}


def crop(ident, n, box, src_w):
    """Crop a region given in hOCR pixel coordinates from the fetched page image."""
    key = (ident, n)
    if key not in _CACHE:
        if len(_CACHE) > 6:
            _CACHE.clear()
        _CACHE[key] = Image.open(page_image(ident, n)).convert("L")
    im = _CACHE[key]
    k = im.width / float(src_w)
    x0, y0, x1, y1 = [v * k for v in box]
    pad = 2
    return im.crop((max(0, int(x0 - pad)), max(0, int(y0 - pad)),
                    min(im.width, int(x1 + pad)), min(im.height, int(y1 + pad))))


def render(key, items, pages, out_pdf, limit=None, footer=True):
    ident = CORPUS[key][0]
    S = E.SPEC
    c = canvas.Canvas(out_pdf, pagesize=(S["pw"], S["ph"]))
    c.setTitle(f"{CORPUS[key][4]} - large-print edition")
    shown = pages[:limit] if limit else pages
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
                img = crop(ident, it["page"], it["src"], it["pw"])
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
