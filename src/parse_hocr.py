"""Parse ABBYY-derived hOCR from Internet Archive into compact per-page JSONL."""
import os, sys, json, re
from lxml import etree
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS

TITLE_NUM = re.compile(r'(\w+)\s+([-\d.]+(?:\s+[-\d.]+)*)')

def props(el):
    t = el.get("title") or ""
    out = {}
    for part in t.split(";"):
        part = part.strip()
        if not part:
            continue
        bits = part.split()
        key, vals = bits[0], bits[1:]
        nums = []
        for v in vals:
            try:
                nums.append(float(v))
            except ValueError:
                nums = None
                break
        out[key] = nums if nums is not None else " ".join(vals)
    return out

def bbox(el):
    b = props(el).get("bbox")
    return [int(v) for v in b] if b else None

def text_of(el):
    return "".join(el.itertext())

def parse(path, out_path):
    n_pages = 0
    with open(out_path, "w") as out:
        ctx = etree.iterparse(path, events=("end",), html=True, huge_tree=True)
        for _, el in ctx:
            cls = el.get("class")
            if cls != "ocr_page":
                continue
            p = props(el)
            page = {
                "n": int(p.get("ppageno", [n_pages])[0]),
                "bbox": [int(v) for v in p.get("bbox", [0, 0, 0, 0])],
                "res": int(p.get("scan_res", [300, 300])[0]),
                "photos": [], "blocks": [],
            }
            for ph in el.findall(".//div[@class='ocr_photo']"):
                b = bbox(ph)
                if b:
                    page["photos"].append(b)
            for blk in el.findall(".//div[@class='ocr_carea']"):
                B = {"bbox": bbox(blk), "pars": []}
                for par in blk.findall(".//p[@class='ocr_par']"):
                    P = {"bbox": bbox(par), "lines": []}
                    for ln in par.findall(".//span[@class='ocr_line']"):
                        lp = props(ln)
                        L = {
                            "bbox": bbox(ln),
                            "xs": lp.get("x_size", [0])[0],
                            "fs": lp.get("x_fsize", [0])[0],
                            "bl": lp.get("baseline", [0, 0]),
                            "w": [],
                        }
                        for wd in ln.findall(".//span[@class='ocrx_word']"):
                            wp = props(wd)
                            wb = wp.get("bbox")
                            if not wb:
                                continue
                            txt = text_of(wd).strip()
                            if not txt:
                                continue
                            L["w"].append([int(wb[0]), int(wb[1]), int(wb[2]), int(wb[3]),
                                           int(wp.get("x_wconf", [0])[0]), txt])
                        if L["w"]:
                            P["lines"].append(L)
                    if P["lines"]:
                        B["pars"].append(P)
                if B["pars"]:
                    page["blocks"].append(B)
            out.write(json.dumps(page, ensure_ascii=False) + "\n")
            n_pages += 1
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]
    return n_pages

if __name__ == "__main__":
    os.makedirs("data/pages", exist_ok=True)
    summary = {}
    for key, (ident, *_rest) in CORPUS.items():
        src = f"data/raw/{ident}_hocr.html"
        dst = f"data/pages/{key}.jsonl"
        if os.path.exists(dst) and os.path.getsize(dst) > 100:
            n = sum(1 for _ in open(dst))
        else:
            n = parse(src, dst)
        nw = 0
        for line in open(dst):
            pg = json.loads(line)
            nw += sum(len(l["w"]) for b in pg["blocks"] for p in b["pars"] for l in p["lines"])
        summary[key] = {"pages": n, "words": nw}
        print(key, n, nw, flush=True)
    json.dump(summary, open("data/corpus/parse_summary.json", "w"), indent=1)
