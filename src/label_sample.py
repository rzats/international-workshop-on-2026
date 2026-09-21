"""Draw a stratified sample of classified paragraphs for manual inspection."""
import os, sys, json, random
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS
from structure import analyse

ROLES = ["heading", "verse", "caption", "footnote", "body", "furniture"]
PER_ROLE = 12


def main(seed=7):
    rng = random.Random(seed)
    pool = {r: [] for r in ROLES}
    for key in CORPUS:
        doc, st = analyse(key)
        H = st["H"] or 1
        for pi, pg in enumerate(doc):
            for ri, rec in enumerate(pg["pars"]):
                p = rec["par"]
                txt = " | ".join(" ".join(w[5] for w in l["w"]) for l in p["lines"])
                if not txt.strip():
                    continue
                pool.setdefault(rec["role"], []).append({
                    "id": f"{key}:{pi}:{ri}", "book": key, "role": rec["role"],
                    "lines": len(p["lines"]),
                    "y0": round(p["bbox"][1] / (pg["page"]["bbox"][3] or 1), 3),
                    "x0": round(p["bbox"][0] / (pg["page"]["bbox"][2] or 1), 3),
                    "x1": round(p["bbox"][2] / (pg["page"]["bbox"][2] or 1), 3),
                    "xs_ratio": round((l0 := p["lines"][0]["xs"] or st["xs"]) / st["xs"], 2),
                    "text": txt[:200],
                })
    out = []
    for r in ROLES:
        items = pool.get(r, [])
        rng.shuffle(items)
        out.extend(items[:PER_ROLE])
    os.makedirs("data/results", exist_ok=True)
    json.dump(out, open("data/results/label_sample.json", "w"), indent=1)
    for it in out:
        print(f'{it["id"]:28s} {it["role"]:9s} ln={it["lines"]:2d} y0={it["y0"]:.2f} '
              f'x={it["x0"]:.2f}-{it["x1"]:.2f} xs={it["xs_ratio"]:.2f} :: {it["text"][:120]}')
    return out


if __name__ == "__main__":
    main()
