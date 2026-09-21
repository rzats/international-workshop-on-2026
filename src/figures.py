"""Paper figures. Print-first: one-column width, greyscale-safe encodings.

Series identity is carried by line style and marker as well as hue, and every
series is directly labelled, so the figures survive both greyscale printing and
colour-vision deficiency.
"""
import os, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
sys.path.insert(0, os.path.dirname(__file__))
from corpus import CORPUS, SHORT
from reliability import wilson

FIGD = "paper/figures"
# categorical slots 1-4 of the reference palette, in fixed order
C = {"model": "#2a78d6", "conf": "#eb6834", "random": "#1baf7a", "oracle": "#4a3aa7"}
STYLE = {"model": ("-", "o"), "conf": ("--", "s"), "random": (":", "^"),
         "oracle": ("-.", "D")}
LABEL = {"model": "reliability model", "conf": "OCR confidence",
         "random": "random", "oracle": "oracle"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d8d7d2"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Libertinus Serif", "DejaVu Serif"],
    "font.size": 8.5, "axes.labelsize": 9, "axes.titlesize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.edgecolor": INK2, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.labelcolor": INK,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})
W1 = 4.6      # one-column width in inches


def style_ax(ax):
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fig_tradeoff(o):
    fig, ax = plt.subplots(figsize=(W1, 3.1))
    style_ax(ax)
    for sel in ("random", "conf", "model", "oracle"):
        pts = o["routing"][sel]
        x = [100 * p["coverage"] for p in pts]
        y = [p["red"] for p in pts]
        lo = [p["red"] - p["red_lo"] for p in pts]
        hi = [p["red_hi"] - p["red"] for p in pts]
        ls, mk = STYLE[sel]
        ax.errorbar(x, y, yerr=[lo, hi], color=C[sel], linestyle=ls, marker=mk,
                    markersize=4.2, linewidth=1.6, capsize=2, elinewidth=0.8,
                    markeredgecolor="white", markeredgewidth=0.5, label=LABEL[sel])
        ax.annotate(LABEL[sel], (x[-1], y[-1]), textcoords="offset points",
                    xytext=(7, 5), fontsize=7.2, color=INK2, ha="left")
    ax.set_xlabel("reflowable coverage (% of running words kept as text)")
    ax.set_ylabel("residual error density\n(exposed OCR errors per 1000 words)")
    ax.set_xlim(56, 104)
    ax.set_ylim(0, 36)
    ax.set_xticks([60, 70, 80, 90, 100])
    leg = ax.legend(frameon=False, loc="lower right", handlelength=2.4,
                    borderaxespad=0.2, labelspacing=0.35)
    for t in leg.get_texts():
        t.set_fontsize(7.2)
    fig.savefig(f"{FIGD}/tradeoff.png")
    plt.close(fig)


def fig_auc(o):
    rows = sorted(o["reliability"], key=lambda r: r["auc_model"])
    fig, ax = plt.subplots(figsize=(W1, 3.4))
    style_ax(ax)
    ax.grid(axis="y", visible=False)
    y = np.arange(len(rows))
    for i, r in enumerate(rows):
        ax.plot([r["auc_conf"], r["auc_model"]], [i, i], color=GRID, linewidth=1.4,
                zorder=1, solid_capstyle="round")
    ax.scatter([r["auc_conf"] for r in rows], y, s=26, marker="s",
               color=C["conf"], edgecolor="white", linewidth=0.5, zorder=3,
               label="OCR confidence")
    ax.scatter([r["auc_model"] for r in rows], y, s=30, marker="o",
               color=C["model"], edgecolor="white", linewidth=0.5, zorder=3,
               label="reliability model")
    ax.set_yticks(y)
    ax.set_yticklabels([SHORT[r["key"]] for r in rows])
    ax.axvline(0.5, color=INK2, linewidth=0.6, linestyle=(0, (1, 2)))
    ax.set_xlabel("AUC for predicting that an OCR token is wrong")
    ax.set_xlim(0.45, 1.02)
    ax.set_ylim(-0.8, len(rows) - 0.2)
    leg = ax.legend(frameon=False, loc="lower left", scatterpoints=1,
                    borderaxespad=0.3, labelspacing=0.35)
    for t in leg.get_texts():
        t.set_fontsize(7.4)
    fig.savefig(f"{FIGD}/auc.png")
    plt.close(fig)


def fig_calibration():
    ps, ys = [], []
    for k in CORPUS:
        p = np.load(f"data/reliability/{k}.npy")
        y = np.load(f"data/features/{k}_y.npy").astype(float)
        s = np.load(f"data/features/{k}_s.npy")
        ps.append(p[s]); ys.append(y[s])
    p = np.concatenate(ps); y = np.concatenate(ys)
    edges = np.array([0, .01, .02, .04, .07, .12, .2, .35, .6, 1.0])
    idx = np.clip(np.digitize(p, edges) - 1, 0, len(edges) - 2)
    xs, obs, lo, hi, ns = [], [], [], [], []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() < 30:
            continue
        xs.append(p[m].mean()); obs.append(y[m].mean()); ns.append(int(m.sum()))
        a, c = wilson(int(y[m].sum()), int(m.sum()))
        lo.append(obs[-1] - a); hi.append(c - obs[-1])
    fig, ax = plt.subplots(figsize=(W1, 2.9))
    style_ax(ax)
    ax.plot([0, 1], [0, 1], color=INK2, linewidth=0.7, linestyle=(0, (1, 2)),
            zorder=1)
    ax.errorbar(xs, obs, yerr=[lo, hi], color=C["model"], marker="o",
                markersize=4.5, linewidth=1.6, capsize=2, elinewidth=0.8,
                markeredgecolor="white", markeredgewidth=0.5, zorder=3)
    ax.annotate("perfect calibration", xy=(0.030, 0.030), xytext=(0.075, 0.0075),
                fontsize=7, color=INK2, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=INK2, linewidth=0.5,
                                shrinkA=2, shrinkB=2))
    ax.set_xlabel("predicted probability that a token is wrong")
    ax.set_ylabel("observed error rate")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(0.004, 1.0); ax.set_ylim(0.004, 1.0)
    fig.savefig(f"{FIGD}/calibration.png")
    plt.close(fig)
    return {"bins": len(xs), "n": int(len(p))}


def fig_pipeline():
    """Vertical stage diagram; a horizontal strip cannot hold the labels at
    one-column width."""
    stages = [
        ("scanned page + hOCR",
         "word boxes, engine confidence,\nillustration regions"),
        ("layout analysis",
         "body, headings, verse, captions, footnotes;\nrunning heads and folios removed"),
        ("reliability estimation",
         "calibrated p(token is wrong) from lexicon,\nshape, geometry and normalised confidence"),
        ("budgeted routing",
         "each paragraph becomes reflowed text\nor a magnified facsimile"),
        ("reflow and re-imposition",
         "A4, 18 pt, ragged right, no widows,\nno stranded headings"),
    ]
    fig, ax = plt.subplots(figsize=(W1, 3.5))
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, len(stages) * 2.0)
    for i, (title, note) in enumerate(stages):
        y = (len(stages) - 1 - i) * 2.0 + 0.35
        ax.add_patch(plt.Rectangle((0.1, y), 4.3, 1.1, facecolor="#f2f1ee" if i else "white",
                                   edgecolor=INK2, linewidth=0.7))
        ax.text(2.25, y + 0.55, title, ha="center", va="center", fontsize=7.8,
                color=INK)
        ax.text(4.75, y + 0.55, note, ha="left", va="center", fontsize=6.9,
                color=INK2, linespacing=1.35)
        if i < len(stages) - 1:
            ax.annotate("", xy=(2.25, y - 0.55), xytext=(2.25, y - 0.02),
                        arrowprops=dict(arrowstyle="->", color=INK2, linewidth=0.7))
    fig.savefig(f"{FIGD}/pipeline.png")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIGD, exist_ok=True)
    o = json.load(open("data/results/summary.json"))
    fig_tradeoff(o)
    fig_auc(o)
    print(fig_calibration())
    fig_pipeline()
    print("figures written to", FIGD)
