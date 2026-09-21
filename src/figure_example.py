"""Side-by-side figure: one scanned source page and one composed output page."""
import os, sys, subprocess, json
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS
import engine as E
import render as R

FIGD = "paper/figures"


def pick_page(items, pages, rich, min_strips=3, min_lines=8):
    """Prefer a composed page whose facsimile strips all come from one
    content-bearing source page, so the pair really is a before/after."""
    import collections
    best = None
    for pi, p in enumerate(pages):
        strips = [items[i] for i in p if items[i]["t"] == "strip"]
        nl = sum(1 for i in p if items[i]["t"] == "line")
        if len(strips) < min_strips or nl < min_lines:
            continue
        c = collections.Counter(s["page"] for s in strips)
        src, dom = c.most_common(1)[0]
        if src not in rich or dom < len(strips):
            continue
        score = min(dom, 10) + min(nl, 20) * 0.3
        if best is None or score > best[0]:
            best = (score, pi, src)
    return (best[1], best[2]) if best else (None, None)


def main(key="timemachine", cov=0.10):
    segs, st = E.document(key)
    route, _ = E.route_by_score(segs, E.score_model(segs), cov)
    items = E.build_items(segs, route)
    pages = E.paginate(items)
    import collections
    nlines = collections.Counter()
    for sg in segs:
        if sg["kind"] == "par":
            nlines[sg["page"]] += len(sg["lines"])
    rich = {p for p, n in nlines.items() if n >= 15}
    pi, src_page = pick_page(items, pages, rich)
    assert pi is not None, "no mixed page found"
    os.makedirs("data/render", exist_ok=True)
    pdf = f"data/render/{key}_example.pdf"
    R.render(key, items, [pages[pi]], pdf, footer=False)
    subprocess.run(["pdftoppm", "-r", "150", "-png", "-f", "1", "-l", "1",
                    pdf, f"data/render/{key}_ex"], check=True)
    out = Image.open(f"data/render/{key}_ex-1.png").convert("RGB")
    src_leaf = src_page + R.offset_for(key)
    src = Image.open(R.page_image(CORPUS[key][0], src_leaf)).convert("RGB")

    h = 1400
    src = src.resize((int(src.width * h / src.height), h), Image.LANCZOS)
    out = out.resize((int(out.width * h / out.height), h), Image.LANCZOS)
    gap, pad, cap = 40, 8, 54
    W = src.width + out.width + gap + 2 * pad
    canvas = Image.new("RGB", (W, h + cap + 2 * pad), "white")
    canvas.paste(src, (pad, cap + pad))
    canvas.paste(out, (pad + src.width + gap, cap + pad))
    d = ImageDraw.Draw(canvas)
    for im, x0, x1 in ((src, pad, pad + src.width),
                       (out, pad + src.width + gap, pad + src.width + gap + out.width)):
        d.rectangle([x0, cap + pad, x1 - 1, cap + pad + h - 1], outline="#9a9a95", width=2)
    try:
        f = ImageFont.truetype("/home/paperbot/.local/share/fonts/LibertinusSerif-Regular.otf", 34)
    except Exception:
        f = ImageFont.load_default()
    d.text((pad, 10), f"(a) scanned source page (leaf {src_leaf})", font=f, fill="#0b0b0b")
    d.text((pad + src.width + gap, 10),
           "(b) composed large-print page", font=f, fill="#0b0b0b")
    canvas.save(f"{FIGD}/example.png")
    return {"key": key, "out_page": pi + 1, "src_leaf": src_leaf,
            "total_pages": len(pages),
            "strips": sum(1 for i in pages[pi] if items[i]["t"] == "strip"),
            "lines": sum(1 for i in pages[pi] if items[i]["t"] == "line")}


if __name__ == "__main__":
    print(main(*(sys.argv[1:2] or ["timemachine"])))
