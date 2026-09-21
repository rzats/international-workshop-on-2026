"""Check that every DOI in the bibliography resolves through Crossref."""
import sys, os, json, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from refs import REFS

if __name__ == "__main__":
    report = {}
    for k, r in REFS.items():
        if not r["doi"]:
            report[k] = {"doi": None, "status": "no-doi"}
            print(f"{k:22s} -- no DOI (checked manually)")
            continue
        try:
            resp = requests.get(f"https://api.crossref.org/works/{r['doi']}",
                                headers={"User-Agent": "largeprint-paper/1.0 (mailto:zatserkovnyi.rostyslav@gmail.com)"},
                                timeout=60)
            if resp.status_code == 200:
                m = resp.json()["message"]
                title = (m.get("title") or [""])[0]
                year = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
                report[k] = {"doi": r["doi"], "status": "ok", "title": title, "year": year}
                print(f"{k:22s} OK  {year}  {title[:70]}")
            else:
                report[k] = {"doi": r["doi"], "status": resp.status_code}
                print(f"{k:22s} FAIL {resp.status_code} {r['doi']}")
        except Exception as e:
            report[k] = {"doi": r["doi"], "status": str(e)}
            print(f"{k:22s} ERR {e}")
        time.sleep(0.3)
    json.dump(report, open("data/results/ref_check.json", "w"), indent=1)
