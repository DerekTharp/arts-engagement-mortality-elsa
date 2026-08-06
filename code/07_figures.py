"""07_figures — model-comparison forest plot (Supplementary Figure S3).

Reads output/tables/table2.csv (frequent
vs never) and plots each specification's hazard ratio with 95% CI, alongside
Fancourt & Steptoe's published estimate as a reference.

Output: output/figures/figure_s3_model_ladder.png
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C

ORDER = [
    (
        "Fancourt 2019\n(published)",
        C.FANCOURT_HR_FREQUENT,
        C.FANCOURT_HR_FREQUENT_CI[0],
        C.FANCOURT_HR_FREQUENT_CI[1],
        True,
    ),
    ("Baseline-fixed\nCox (full sample)", "Baseline-fixed Cox", None, None, False),
    ("Time-varying\nCox", "Time-varying Cox", None, None, False),
    ("Baseline-fixed\ncloglog (panel)", "Baseline-fixed cloglog (panel)", None, None, False),
    ("Unweighted\ndiscrete-time PH", "Unweighted discrete-time PH", None, None, False),
    (
        "Concurrent-confounder-\nadjusted PH",
        "Concurrent-confounder-adjusted PH",
        None,
        None,
        False,
    ),
    ("MSM\n(IPTW+IPCW)", "MSM IPTW+IPCW cloglog", None, None, False),
]


def main():
    rows = {}
    with open(C.TABLES / "table2.csv") as f:
        for r in csv.DictReader(f):
            if r["Exposure"] == "Frequent":
                rows[r["Model"]] = (float(r["HR"]), float(r["CI_low"]), float(r["CI_high"]))

    labels, hrs, los, his, refs = [], [], [], [], []
    for entry in ORDER:
        lab = entry[0]
        if entry[4]:
            hr, lo, hi = entry[1], entry[2], entry[3]
        else:
            hr, lo, hi = rows[entry[1]]
        labels.append(lab); hrs.append(hr); los.append(lo); his.append(hi); refs.append(entry[4])

    y = list(range(len(labels)))[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    for yi, hr, lo, hi, ref in zip(y, hrs, los, his, refs):
        col = "#7a7a7a" if ref else "#1f3b6f"
        ax.plot([lo, hi], [yi, yi], "-", color=col, lw=1.6, zorder=2)
        ax.plot(hr, yi, "D", color=col, ms=7, zorder=3)
        ax.annotate(f"{hr:.2f} ({lo:.2f}–{hi:.2f})", (hr, yi), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=7.5, color="#7a1f1f")
    ax.axvline(1.0, color="#bcbcbc", ls="--", lw=0.9, zorder=0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlim(0.4, 1.15)
    ax.set_xticks([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1])
    ax.set_xlabel("Hazard ratio (frequent vs never)", fontsize=9)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    C.FIGURES.mkdir(parents=True, exist_ok=True)
    out = C.FIGURES / "figure_s3_model_ladder.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    print(f"07 complete: {out.relative_to(C.PROJ)}")


if __name__ == "__main__":
    main()
