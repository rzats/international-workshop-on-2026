"""Download hOCR + Gutenberg text for every corpus item (resumable, cached)."""
import os, sys, json, gzip, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS

RAW = "data/raw"
os.makedirs(RAW, exist_ok=True)

def get(url, dest, timeout=600):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return dest
    tmp = dest + ".part"
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    os.rename(tmp, dest)
    return dest

def ia_hocr(ident):
    dest = f"{RAW}/{ident}_hocr.html"
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return dest
    meta = requests.get(f"https://archive.org/metadata/{ident}", timeout=120).json()
    names = {f["name"] for f in meta["files"]}
    if f"{ident}_hocr.html" in names:
        return get(f"https://archive.org/download/{ident}/{ident}_hocr.html", dest)
    if f"{ident}_hocr.html.gz" in names:
        gz = get(f"https://archive.org/download/{ident}/{ident}_hocr.html.gz", dest + ".gz")
        with gzip.open(gz) as fi, open(dest, "wb") as fo:
            fo.write(fi.read())
        os.remove(gz)
        return dest
    raise RuntimeError(f"no hOCR for {ident}: {sorted(n for n in names if 'hocr' in n)}")

def pg_text(pgid):
    dest = f"{RAW}/pg{pgid}.txt"
    for url in (f"https://www.gutenberg.org/cache/epub/{pgid}/pg{pgid}.txt",
                f"https://www.gutenberg.org/files/{pgid}/{pgid}-0.txt"):
        try:
            return get(url, dest, timeout=180)
        except Exception:
            continue
    raise RuntimeError(f"no PG text for {pgid}")

if __name__ == "__main__":
    report = {}
    for key, (ident, year, pgid, genre, label) in CORPUS.items():
        rec = {"ident": ident, "year": year, "pg": pgid, "genre": genre, "label": label}
        try:
            h = ia_hocr(ident); rec["hocr_bytes"] = os.path.getsize(h)
        except Exception as e:
            rec["hocr_error"] = str(e)
        try:
            t = pg_text(pgid); rec["pg_bytes"] = os.path.getsize(t)
        except Exception as e:
            rec["pg_error"] = str(e)
        print(key, rec.get("hocr_bytes"), rec.get("pg_bytes"),
              rec.get("hocr_error", ""), rec.get("pg_error", ""), flush=True)
        report[key] = rec
        time.sleep(0.5)
    json.dump(report, open("data/corpus/fetch_report.json", "w"), indent=1)
