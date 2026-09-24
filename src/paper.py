# -*- coding: utf-8 -*-
"""Build the manuscript inside the CEURART one-column ODT template.

The template is unpacked, its front matter is edited in place so that every
style, image and footnote construction it defines survives untouched, and the
body between the front matter and the closing tags is replaced.
"""
import os, re, sys, json, shutil, subprocess
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS, SHORT
import paper_text as T
from refs import REFS
from odt import unpack, pack

TPL = "template/CEUR-Template-1col.odt"
WORK = "build/odt"
OUT_ODT = "paper/international-workshop-on-2026.odt"
OUT_PDF = "paper/international-workshop-on-2026.pdf"
TEXTW = 6.2208          # inches of text width in the template page layout
YEAR = 2026


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ------------------------------------------------------------------ numbers

def pct(x, n=1):
    return f"{100 * x:.{n}f}"


def facts():
    S = json.load(open("data/results/summary.json"))
    F = json.load(open("data/results/furniture_eval.json"))["pooled"]
    L = json.load(open("data/results/label_precision.json"))
    A = json.load(open("data/corpus/align_summary.json"))
    ct, rt, comp, gains = (S["corpus_totals"], S["reliability_totals"],
                           S["composition"], S["routing_gains"])
    g10, g40 = gains["0.1"], gains["0.4"]
    rel = {r["key"]: r for r in S["reliability"]}
    pb = {r["key"]: r for r in S["per_book_10pct"]}
    m10 = [p for p in S["routing"]["model"] if p["cov_loss"] == 0.10][0]
    c10 = [p for p in S["routing"]["conf"] if p["cov_loss"] == 0.10][0]
    base = S["routing"]["model"][0]
    import numpy as np
    conf90 = np.load("data/features/baskerville_X.npy")[:, 2]
    f = {
        "NBOOKS": ct["books"], "SRCPAGES": f"{ct['src_pages']:,}",
        "TOKENS": f"{ct['tokens']:,}", "FIGS": f"{ct['figures']:,}",
        "ALIGNEDM": f"{ct['aligned'] / 1e6:.2f}",
        "ALIGNPCT": pct(ct["alignable"]),
        "WERPCT": pct(ct["wer"], 2),
        "WERCI": f"{pct(ct['wer_ci'][0], 2)}–{pct(ct['wer_ci'][1], 2)}%",
        "WERMAX": pct(max(A[k]["wer_aligned"] for k in A), 1),
        "YEARMIN": min(CORPUS[k][1] for k in CORPUS),
        "YEARMAX": max(CORPUS[k][1] for k in CORPUS),
        "NOPANFULL": pct(ct["no_pan_full"], 0),
        "NOPANCROP": pct(ct["no_pan_crop"], 0),
        "MAGPAGES": f"{comp['magnify-tile']['pages']:,}",
        "MAGRATIO": f"{comp['magnify-tile']['pages'] / comp['constrained-reflow']['pages']:.2f}",
        "MAGSRC": f"{comp['magnify-tile']['pages'] / ct['src_pages']:.2f}",
        "FURNTOK": f"{F['furniture']['n']:,}",
        "FURNMATCH": pct(F["furniture"]["match_rate"], 1),
        "FURNCI": f"{pct(F['furniture']['ci'][0], 1)}–{pct(F['furniture']['ci'][1], 1)}%",
        "BODYMATCH": pct(F["body"]["match_rate"], 1),
        "FBSHARE": pct((F["body"]["n"] + F["furniture"]["n"]) /
                       sum(v["n"] for v in F.values()), 0),
        "POOLEDCONF": f"{rt['pooled_conf_auc']:.3f}",
        "POOLEDPCT": f"{rt['pooled_pct_auc']:.3f}",
        "AUCM": f"{rt['auc_model_mean']:.3f}", "AUCMSD": f"{rt['auc_model_sd']:.3f}",
        "AUCC": f"{rt['auc_conf_mean']:.3f}", "AUCCSD": f"{rt['auc_conf_sd']:.3f}",
        "SIGNP": f"{rt['sign_test_p']:.1e}".replace("e-0", " × 10−"),
        "ECE": f"{rt['ece_mean']:.3f}",
        "WALDENC": f"{rel['walden']['auc_conf']:.3f}",
        "WALDENM": f"{rel['walden']['auc_model']:.3f}",
        "MOBYC": f"{rel['moby']['auc_conf']:.3f}",
        "MOBYM": f"{rel['moby']['auc_model']:.3f}",
        "BASKHIGH": f"{100 * (conf90 >= 0.90).mean():.0f}",
        "RAGG": f"{comp['greedy-reflow']['ragged_rms']:.4f}",
        "RAGKP": f"{comp['kp-unconstrained']['ragged_rms']:.4f}",
        "RAGRED": f"{100 * (1 - comp['kp-unconstrained']['ragged_rms'] / comp['greedy-reflow']['ragged_rms']):.1f}",
        "VIOLG": f"{comp['greedy-reflow']['viol']:,}",
        "VIOLC": f"{comp['constrained-reflow']['viol']}",
        "VIOLRED": f"{100 * (1 - comp['constrained-reflow']['viol'] / comp['greedy-reflow']['viol']):.1f}",
        "PAGEOVH": f"{100 * (comp['constrained-reflow']['pages'] / comp['greedy-reflow']['pages'] - 1):.1f}",
        "FACOVH": f"{100 * (comp['all-facsimile']['pages'] / comp['constrained-reflow']['pages'] - 1):.1f}",
        "RED0": f"{base['red']:.1f}", "B10": "10%",
        "RED10V": f"{g10['model']:.1f}", "RED10": f"{100 * g10['reduction_model']:.1f}",
        "REDC10V": f"{g10['conf']:.1f}", "REDC10": f"{100 * g10['reduction_conf']:.1f}",
        "REDR10V": f"{g10['random']:.1f}", "GAP10": f"{100 * g10['oracle_gap_closed']:.0f}",
        "RED40V": f"{g40['model']:.1f}", "REDC40V": f"{g40['conf']:.1f}",
        "REDR40V": f"{g40['random']:.1f}", "REDO40V": f"{g40['oracle']:.1f}",
        "PAGE10": f"{abs(100 * g10['page_overhead']):.1f}",
        "PAGE40": f"{100 * g40['page_overhead']:.1f}",
        "WINS": S["per_book_10pct_wins"]["model_beats_conf"],
        "WINP": f"{S['per_book_10pct_wins']['sign_test_p']:.2f}",
        "CAROLTOK": f"{rel['carol']['n']:,}",
        "BASKBASE": f"{pb['baskerville']['base']['red']:.1f}",
        "BASKMODEL": f"{pb['baskerville']['model']['red']:.1f}",
        "BASKCONF": f"{pb['baskerville']['conf']['red']:.1f}",
        "BASKPAGES": f"{100 * (pb['baskerville']['model']['pages'] / pb['baskerville']['base']['pages'] - 1):.0f}",
        "MEASURE": "482", "CPL": "57", "HEIGHT10": "0.26",
        "CI10M": f"{m10['red_lo']:.1f}–{m10['red_hi']:.1f}",
        "CI10C": f"{c10['red_lo']:.1f}–{c10['red_hi']:.1f}",
        "NTOK": "n", "EXPERR": "e", "SECREL": "6.3",
    }
    return f, S, F, L, A


# ------------------------------------------------------------------ citations

class Cites:
    def __init__(self):
        self.order = []

    def sub(self, text):
        def rep(m):
            keys = [k.strip() for k in m.group(1).split(",")]
            nums = []
            for k in keys:
                if k not in REFS:
                    raise KeyError(f"unknown citation {k}")
                if k not in self.order:
                    self.order.append(k)
                nums.append(str(self.order.index(k) + 1))
            return "[" + ", ".join(nums) + "]"
        return re.sub(r"\[([a-z0-9_]+(?:\s*,\s*[a-z0-9_]+)*)\]", rep, text)


# ------------------------------------------------------------------ tables

def table_xml(name, cols, header, rows, number, caption, widths=None):
    n = len(cols)
    widths = widths or [TEXTW / n] * n
    sty = [f'<style:style style:name="{name}" style:family="table">'
           f'<style:table-properties style:width="{TEXTW:.4f}in" fo:margin-top="0in" '
           f'fo:margin-bottom="0in" table:align="center" style:writing-mode="lr-tb"/>'
           f'</style:style>']
    for i, w in enumerate(widths):
        sty.append(f'<style:style style:name="{name}.{chr(65+i)}" style:family="table-column">'
                   f'<style:table-column-properties style:column-width="{w:.4f}in"/></style:style>')
    sty.append(f'<style:style style:name="{name}.1" style:family="table-row">'
               f'<style:table-row-properties fo:keep-together="auto"/></style:style>')
    borders = {"H": 'fo:border-left="none" fo:border-right="none" fo:border-top="2.25pt solid #000000" fo:border-bottom="1.5pt solid #000000"',
               "M": 'fo:border="none"',
               "L": 'fo:border-left="none" fo:border-right="none" fo:border-top="none" fo:border-bottom="2.25pt solid #000000"'}
    for k, b in borders.items():
        sty.append(f'<style:style style:name="{name}.{k}" style:family="table-cell">'
                   f'<style:table-cell-properties fo:padding-left="0.05in" fo:padding-right="0.05in" '
                   f'fo:padding-top="0in" fo:padding-bottom="0in" {b} style:writing-mode="lr-tb"/>'
                   f'</style:style>')

    def row(cells, cls):
        out = [f'<table:table-row table:style-name="{name}.1">']
        for j, c in enumerate(cells):
            al = {"c": "TblC", "l": "TblL"}.get(cols[j], "TblR")
            out.append(f'<table:table-cell table:style-name="{name}.{cls}" '
                       f'office:value-type="string"><text:p text:style-name="{al}">'
                       f'{esc(str(c))}</text:p></table:table-cell>')
        out.append('</table:table-row>')
        return "".join(out)

    body = [f'<text:p text:style-name="P4">Table {number}</text:p>',
            f'<text:p text:style-name="P5">{esc(caption)}</text:p>',
            f'<table:table table:name="{name}" table:style-name="{name}">']
    body += [f'<table:table-column table:style-name="{name}.{chr(65+i)}"/>' for i in range(n)]
    body.append('<table:table-header-rows>' + row(header, "H") + '</table:table-header-rows>')
    for i, r in enumerate(rows):
        body.append(row(r, "L" if i == len(rows) - 1 else "M"))
    body.append('</table:table>')
    body.append('<text:p text:style-name="P15"/>')
    return "".join(sty), "".join(body)


# ------------------------------------------------------------------ figures

def figure_xml(pic_name, width_in, caption, number):
    im = Image.open(f"paper/figures/{pic_name}.png")
    h = width_in * im.height / im.width
    frame = (f'<text:p text:style-name="Figure"><draw:frame draw:style-name="fr2" '
             f'draw:name="Figure{number}" text:anchor-type="as-char" '
             f'svg:width="{width_in:.4f}in" svg:height="{h:.4f}in" draw:z-index="0">'
             f'<draw:image xlink:href="Pictures/{pic_name}.png" xlink:type="simple" '
             f'xlink:show="embed" xlink:actuate="onLoad" draw:mime-type="image/png"/>'
             f'<svg:desc>{esc(caption)}</svg:desc></draw:frame></text:p>')
    cap = (f'<text:p text:style-name="P21">Figure {number}: {esc(caption)}</text:p>')
    return frame + cap


# ------------------------------------------------------------------ table data

def build_tables(f, S, F, L):
    ali = json.load(open("data/corpus/align_summary.json"))
    corp = {r["key"]: r for r in S["corpus"]}
    rel = {r["key"]: r for r in S["reliability"]}
    pb = {r["key"]: r for r in S["per_book_10pct"]}
    eng = {"ABBYY (LuraDocument export)": "ABBYY/Lura",
           "ABBYY FineReader 11": "ABBYY FR11",
           "Tesseract 5.3.0": "Tesseract 5.3"}
    T1 = []
    for k in CORPUS:
        c = corp[k]
        T1.append([SHORT[k], c["year"], eng.get(c["engine"], c["engine"]),
                   f"{c['src_pages']:,}", f"{c['tokens']:,}",
                   f"{100 * c['alignable']:.1f}", f"{100 * c['wer']:.2f}"])
    T1.append(["all 14 volumes", "", "", f"{S['corpus_totals']['src_pages']:,}",
               f"{S['corpus_totals']['tokens']:,}",
               f"{100 * S['corpus_totals']['alignable']:.1f}",
               f"{100 * S['corpus_totals']['wer']:.2f}"])
    t1 = table_xml("TblCorpus", ["l", "c", "l", "r", "r", "r", "r"],
                   ["volume", "printed", "OCR engine", "pages", "tokens",
                    "scorable %", "word err. %"], T1, 1,
                   "The corpus. Word error is measured against the Project Gutenberg e-text of "
                   "the same work, over the scorable tokens only.",
                   widths=[1.72, .52, .88, .55, .72, .72, .78])

    order = ["furniture", "body", "verse", "heading", "caption", "footnote"]
    T2 = []
    for r in order:
        p = L[r]
        fe = F.get(r)
        T2.append([r, f"{p['k']}/{p['n']}", f"{p['precision']:.2f}",
                   f"{p['ci'][0]:.2f}–{p['ci'][1]:.2f}",
                   f"{fe['n']:,}" if fe else "–",
                   f"{100 * fe['match_rate']:.1f}" if fe else "–"])
    t2 = table_xml("TblRoles", ["l", "c", "c", "c", "r", "r"],
                   ["predicted role", "correct", "precision", "95% CI", "tokens",
                    "match e-text %"], T2, 2,
                   "Layout analysis. Precision is adjudicated on twelve sampled paragraphs per "
                   "predicted class. The last two columns give, for all tokens of that class, "
                   "how often they match the reference transcription; apparatus is expected not "
                   "to match, running text is.",
                   widths=[1.25, .72, .82, 1.05, 1.05, 1.12])

    comp = S["composition"]
    lab = [("magnify-tile", "magnify and tile"), ("all-facsimile", "all facsimile"),
           ("greedy-reflow", "greedy reflow"), ("kp-unconstrained", "Knuth–Plass reflow"),
           ("constrained-reflow", "constrained reflow")]
    T3 = []
    for k, nm in lab:
        c = comp[k]
        T3.append([nm, f"{c['pages']:,}", f"{c['pages_per_1000w']:.2f}",
                   f"{100 * c['coverage']:.0f}", f"{c['red']:.1f}",
                   f"{c['viol_per_100pp']:.1f}",
                   "–" if c["ragged_rms"] == 0 else f"{c['ragged_rms']:.4f}"])
    t3 = table_xml("TblComp", ["l", "r", "r", "r", "r", "r", "r"],
                   ["strategy", "pages", "per 1000 w", "cover %", "err./1000 w",
                    "viol./100 pp", "ragged"], T3, 3,
                   "Composition strategies at full coverage, pooled over the corpus. Residual "
                   "error density counts erroneous recognised words presented as text.",
                   widths=[1.45, .72, .85, .72, .92, .88, .68])

    T4 = []
    for c in (0.02, 0.05, 0.10, 0.20, 0.40):
        key = f"{c:g}"
        g = S["routing_gains"][key]
        row = [f"{100 * c:.0f}", f"{100 * (1 - c):.0f}"]
        row += [f"{g[s]:.1f}" for s in ("random", "conf", "model", "oracle")]
        row += [f"{100 * g['oracle_gap_closed']:.0f}", f"{100 * g['page_overhead']:+.1f}"]
        T4.append(row)
    t4 = table_xml("TblRouting", ["c", "c", "r", "r", "r", "r", "r", "r"],
                   ["budget %", "cover %", "random", "confid.", "model", "oracle",
                    "gap closed %", "pages %"], T4, 4,
                   "Residual error density (erroneous words presented as text, per thousand "
                   "words) at matched coverage budgets. Reflowing everything gives "
                   f"{f['RED0']}. The last column is the change in extent against that edition.",
                   widths=[.78, .72, .72, .72, .68, .68, .98, .72])

    T5 = []
    for k in CORPUS:
        r = pb[k]
        T5.append([SHORT[k], f"{rel[k]['auc_conf']:.3f}", f"{rel[k]['auc_model']:.3f}",
                   f"{r['base']['red']:.1f}", f"{r['random']['red']:.1f}",
                   f"{r['conf']['red']:.1f}", f"{r['model']['red']:.1f}",
                   f"{r['oracle']['red']:.1f}"])
    t5 = table_xml("TblBook", ["l", "r", "r", "r", "r", "r", "r", "r"],
                   ["volume", "AUC conf.", "AUC model", "all text", "random",
                    "confid.", "model", "oracle"], T5, 5,
                   "Per volume: ranking quality, and residual error density at the 10% coverage "
                   "budget. Lower is better in the last five columns.",
                   widths=[1.62, .68, .72, .62, .62, .62, .6, .62])

    return {"corpus": t1, "roles": t2, "composition": t3, "routing": t4, "perbook": t5}


def _cell_style(name, align):
    return (f'<style:style style:name="{name}" style:family="paragraph" '
            f'style:parent-style-name="Standard"><style:paragraph-properties '
            f'fo:margin-top="0.014in" fo:margin-bottom="0.014in" '
            f'style:contextual-spacing="false" fo:text-align="{align}" '
            f'style:justify-single-word="false" fo:text-indent="0in" '
            f'fo:line-height="100%" style:auto-text-indent="false"/>'
            f'<style:text-properties fo:font-size="9pt" '
            f'style:font-size-asian="9pt" style:font-size-complex="9pt"/></style:style>')


EXTRA_STYLES = (
 _cell_style("TblL", "start") + _cell_style("TblC", "center") + _cell_style("TblR", "end")
 + '<style:style style:name="Tit" style:family="text">'
   '<style:text-properties fo:font-style="italic"/></style:style>'
)

FIG_W = {"pipeline": 4.4, "auc": 5.1, "calibration": 4.6, "tradeoff": 4.9, "example": 6.1}


def render_body(f, tables, cites):
    out, fign, tabn = [], 0, 0
    first_after_head = False
    for kind, payload in T.BODY:
        if kind in ("h1", "h2", "h3"):
            lvl = {"h1": 1, "h2": 2, "h3": 3}[kind]
            sty = {"h1": "P29", "h2": "P30", "h3": "P31"}[kind]
            out.append(f'<text:h text:style-name="{sty}" text:outline-level="{lvl}">'
                       f'{esc(payload)}</text:h>')
            first_after_head = True
        elif kind in ("p", "p0"):
            txt = cites.sub(payload.format(**f))
            sty = "P15" if (kind == "p0" or first_after_head) else "Standard"
            out.append(f'<text:p text:style-name="{sty}">{esc(txt)}</text:p>')
            first_after_head = False
        elif kind == "fig":
            name, cap = payload
            fign += 1
            out.append(figure_xml(name, FIG_W[name], cap.format(**f), fign))
            first_after_head = False
        elif kind == "table":
            tabn += 1
            out.append(tables[payload][1])
            first_after_head = False
    return "".join(out)


def references_xml(cites):
    items = []
    for k in cites.order:
        items.append('<text:list-item><text:p text:style-name="P36">'
                     + esc(REFS[k]["text"]) + '</text:p></text:list-item>')
    return ('<text:h text:style-name="P8" text:outline-level="1">References</text:h>'
            '<text:list xml:id="listrefs" text:style-name="WWNum24">'
            + "".join(items) + '</text:list>')


DECLARATION = (
 '<text:h text:style-name="P7" text:outline-level="1">Declaration on Generative AI</text:h>'
 '<text:p text:style-name="P15">During the preparation of this work, the authors used Claude '
 '(Anthropic) in order to: proofread the manuscript and check grammar and spelling. After using '
 'this tool, the authors reviewed and edited the content as needed and take full responsibility '
 'for the publication&#8217;s content.</text:p>'
)


def front_matter(fm, f):
    """Substitute the template's specimen front matter, keeping its construction."""
    a1, a2 = T.AUTHORS
    # title
    fm = fm.replace('A better way to format your document for CEUR-WS ', esc(T.TITLE))
    fm = fm.replace('<text:span text:style-name="T1">using LibreOffice</text:span>', '')
    # venue footnote and the template's instruction footnote
    fm = re.sub(r'<text:p text:style-name="Proceedings_20_title">.*?</text:p>',
                f'<text:p text:style-name="Proceedings_20_title">{esc(T.VENUE)}</text:p>',
                fm, count=1, flags=re.S)
    fm = re.sub(r'<text:p text:style-name="Footnote"><text:span text:style-name='
                r'"Footnote_20_Symbol">⋆</text:span>[^<]*</text:p>', '', fm, count=1)
    # authors
    authors = (f'Rostyslav <text:span text:style-name="Author_20_Last_20_Name_20_Char">'
               f'Zatserkovnyi</text:span><text:span text:style-name="T5">1,</text:span>'
               f'<text:span text:style-name="T6">∗,†</text:span>'
               f'<text:span text:style-name="T7">, </text:span>'
               f'Roksoliana <text:span text:style-name="Author_20_Last_20_Name_20_Char">'
               f'Zatserkovna</text:span><text:span text:style-name="T4">2</text:span>'
               f'<text:span text:style-name="T6">,†</text:span>')
    fm = re.sub(r'(<text:p text:style-name="P9">).*?(</text:p>)',
                lambda m: m.group(1) + authors + m.group(2), fm, count=1, flags=re.S)
    # affiliations: three University paragraphs in the template, two here
    unis = list(re.finditer(r'<text:p text:style-name="University">.*?</text:p>', fm, flags=re.S))
    new = "".join(f'<text:p text:style-name="University"><text:span text:style-name="T9">'
                  f'{i + 1}</text:span> {esc(a)} </text:p>'
                  for i, a in enumerate(T.AFFILIATIONS))
    fm = fm[:unis[0].start()] + new + fm[unis[2].end():]
    # abstract and keywords
    fm = re.sub(r'(<text:p text:style-name="Abstract_20_Text">).*?(</text:p>)',
                lambda m: m.group(1) + esc(T.ABSTRACT.format(**f)) + m.group(2),
                fm, count=1, flags=re.S)
    fm = fm.replace('paper template, paper formatting, CEUR-WS', esc(T.KEYWORDS))
    # contact footnote: emails and ORCIDs
    mail = (f'<text:a xlink:type="simple" xlink:href="mailto:{a1["email"]}" '
            f'text:style-name="Internet_20_link" text:visited-style-name="Visited_20_Internet_20_Link">'
            f'<text:span text:style-name="Internet_20_link">{a1["email"]}</text:span></text:a>'
            f' ({a1["short"]}); '
            f'<text:a xlink:type="simple" xlink:href="mailto:{a2["email"]}" '
            f'text:style-name="Internet_20_link" text:visited-style-name="Visited_20_Internet_20_Link">'
            f'<text:span text:style-name="Internet_20_link">{a2["email"]}</text:span></text:a>'
            f' ({a2["short"]}) ')
    fm = re.sub(r'<text:span text:style-name="Internet_20_link">aleksandr\.ometov@tuni\.ee?</text:span>.*?\(M\. Jeusfeld\) ',
                mail, fm, count=1, flags=re.S)
    fm = re.sub(r'<text:span text:style-name="Internet_20_link">aleksandr\.ometov@tuni\.ac?e?</text:span>.*?\(M\. Jeusfeld\) ',
                mail, fm, count=1, flags=re.S)
    fm = re.sub(r'<text:span text:style-name="Internet_20_link">aleksandr\.ometov@tuni\.fi</text:span>.*?\(M\. Jeusfeld\) ',
                mail, fm, count=1, flags=re.S)
    orc = ""
    for a in (a1, a2):
        orc += (f'<text:a xlink:type="simple" xlink:href="https://orcid.org/{a["orcid"]}" '
                f'text:style-name="Internet_20_link" text:visited-style-name="Visited_20_Internet_20_Link">'
                f'<text:span text:style-name="Internet_20_link">{a["orcid"]}</text:span></text:a>'
                f' ({a["short"]}){"; " if a is a1 else " "}')
    fm = re.sub(r'<text:a xlink:type="simple" xlink:href="https://orcid\.org/0000-0000-0000-0000".*?\(M\. Jeusfeld\)',
                orc, fm, count=1, flags=re.S)
    fm = fm.replace('© 2023 Copyright for this paper by its authors.',
                    f'© {YEAR} Copyright for this paper by its authors.')
    return fm


def build():
    f, S, F, L, A = facts()
    tables = build_tables(f, S, F, L)
    cites = Cites()
    body = render_body(f, tables, cites)
    assert len(cites.order) >= 20, cites.order
    # Self-citation policy: at most two, never at [1], never adjacent.
    selfc = [i for i, k in enumerate(cites.order)
             if k in ("zatserkovnyi2022", "zatserkovnyi2023")]
    assert len(selfc) <= 2, selfc
    assert 0 not in selfc, "a self-citation must not be reference [1]"
    assert all(b - a > 1 for a, b in zip(selfc, selfc[1:])), "self-citations must not be adjacent"

    os.makedirs("build", exist_ok=True)
    unpack(TPL, WORK)
    xml = open(f"{WORK}/content.xml", encoding="utf-8").read()
    tstyles = "".join(v[0] for v in tables.values())
    xml = xml.replace("</office:automatic-styles>",
                      EXTRA_STYLES + tstyles + "</office:automatic-styles>")
    head, rest = xml.split("<office:body", 1)
    rest = "<office:body" + rest
    start = rest.index("<text:h")
    fm = front_matter(rest[:start], f)
    tail = "</office:text></office:body></office:document-content>"
    new = head + fm + body + DECLARATION + references_xml(cites) + tail
    open(f"{WORK}/content.xml", "w", encoding="utf-8").write(new)

    # register the figures
    man = open(f"{WORK}/META-INF/manifest.xml", encoding="utf-8").read()
    entries = ""
    for name in FIG_W:
        shutil.copy(f"paper/figures/{name}.png", f"{WORK}/Pictures/{name}.png")
        entries += (f'<manifest:file-entry manifest:full-path="Pictures/{name}.png" '
                    f'manifest:media-type="image/png"/>')
    man = man.replace("</manifest:manifest>", entries + "</manifest:manifest>")
    open(f"{WORK}/META-INF/manifest.xml", "w", encoding="utf-8").write(man)

    meta = open(f"{WORK}/meta.xml", encoding="utf-8").read()
    meta = re.sub(r"<dc:title>.*?</dc:title>", "", meta, flags=re.S)
    meta = meta.replace("<office:meta>", f"<office:meta><dc:title>{esc(T.TITLE)}</dc:title>")
    open(f"{WORK}/meta.xml", "w", encoding="utf-8").write(meta)

    with open(f"{WORK}/.zipmeta") as fh:
        zm = fh.read()
    if "Pictures/pipeline.png" not in zm:
        with open(f"{WORK}/.zipmeta", "a") as fh:
            for name in FIG_W:
                fh.write(f"0\tPictures/{name}.png\n")

    os.makedirs("paper", exist_ok=True)
    pack(WORK, OUT_ODT)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", "paper", OUT_ODT], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return cites, f


if __name__ == "__main__":
    cites, f = build()
    print("references:", len(cites.order))
    print("self-citation positions:", [cites.order.index(k) + 1 for k in
                                       ("zatserkovnyi2022", "zatserkovnyi2023")])
    print("built", OUT_ODT, OUT_PDF)
