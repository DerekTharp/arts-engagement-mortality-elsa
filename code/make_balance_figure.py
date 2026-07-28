"""Love plot of numerator-adjusted balance for the arts-engagement MSM.

For each time-varying confounder, the figure shows regression-adjusted
standardised mean differences before and after IPTW-IPCW weighting. Separate
rows report frequent-versus-never and infrequent-versus-never current exposure;
columns stratify by prior-wave exposure. The adjustment model contains current
age, age squared, and the baseline covariates included in the stabilised weight
numerator.

Input:  output/tables/weight_balance_stratified.csv  (written by 05_msm_iptw.py)
Output: output/figures/figure2_balance_smd.png
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from pyelsa import config as C

CSV = ROOT / "output" / "tables" / "weight_balance_stratified.csv"
OUT = ROOT / "output" / "figures" / "figure2_balance_smd.png"

LABELS = {
    "any_mobil_tv": "Mobility limitation",
    "any_adl_tv": "ADL limitation",
    "any_iadl_tv": "IADL limitation",
    "cog_tv": "Cognition (z)",
    "cancre": "Cancer",
    "lunge": "Lung disease",
    "cvd_any_tv": "Cardiovascular disease",
    "smoke_now_tv": "Current smoker",
    "cesd_w": "Depressive symptoms",
    "poor_sight_tv": "Poor eyesight",
    "poor_hear_tv": "Poor hearing",
}
STRATA = [
    ("lag_never", "Prior exposure: never"),
    ("lag_infrequent", "Prior exposure: infrequent"),
    ("lag_frequent", "Prior exposure: frequent"),
]
CONTRASTS = [
    ("freq_vs_never", "Current frequent versus never", "frequent"),
    ("infreq_vs_never", "Current infrequent versus never", "infrequent"),
]


def load():
    if not CSV.exists():
        sys.exit(f"Missing {CSV}; run the Python pipeline (code/run_all.py) first.")
    rows = list(csv.DictReader(open(CSV)))
    data = {}
    for r in rows:
        data.setdefault((r["contrast"], r["stratum"]), {})[r["covariate"]] = r
    return data


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def main():
    data = load()
    # Use one ordering across all six panels; the largest adjusted pre-weighting
    # imbalance appears at the top.
    order = sorted(
        LABELS,
        key=lambda cov: max(
            abs(fnum(data[(contrast, stratum)][cov]["smd_adjusted_unweighted"]))
            for contrast, _, _ in CONTRASTS
            for stratum, _ in STRATA
        ),
    )
    ypos = range(len(order))

    fig, axes = plt.subplots(
        len(CONTRASTS), len(STRATA), figsize=(11.5, 7.6),
        sharex=True, sharey=True,
    )
    unw_col, wt_col, conn_col = "#8c8c8c", "#1f3b6f", "#c8c8c8"

    for row_index, (contrast, contrast_label, group_label) in enumerate(CONTRASTS):
        for column_index, (stratum, stratum_label) in enumerate(STRATA):
            ax = axes[row_index, column_index]
            d = data.get((contrast, stratum), {})
            for y, cov in zip(ypos, order):
                r = d.get(cov, {})
                su = fnum(r.get("smd_adjusted_unweighted"))
                sw = fnum(r.get("smd_adjusted_weighted"))
                if su == su and sw == sw:
                    ax.plot(
                        [su, sw], [y, y], "-", color=conn_col, lw=1.0, zorder=1
                    )
                ax.plot(
                    su, y, "o", mfc="white", mec=unw_col, mew=1.3, ms=5.5,
                    zorder=2,
                )
                ax.plot(
                    sw, y, "o", mfc=wt_col, mec=wt_col, ms=5.5, zorder=3
                )
            for threshold in (
                -C.SMD_IMBALANCE_THRESHOLD,
                C.SMD_IMBALANCE_THRESHOLD,
            ):
                ax.axvline(
                    threshold, color="#bcbcbc", ls="--", lw=0.8, zorder=0
                )
            ax.axvline(0, color="#4d4d4d", ls="-", lw=0.8, zorder=0)
            any_row = d.get("cog_tv", {})
            n_high_raw = any_row.get("n_hi", "")
            n_never_raw = any_row.get("n_lo", "")
            n_high = (
                f"{int(float(n_high_raw)):,}" if n_high_raw else "?"
            )
            n_never = (
                f"{int(float(n_never_raw)):,}" if n_never_raw else "?"
            )
            ax.set_title(
                f"{stratum_label}\n({group_label} n={n_high}; never n={n_never})",
                fontsize=8.5,
            )
            ax.set_xlim(-0.45, 0.45)
            ax.set_xticks([-0.4, -0.2, 0, 0.2, 0.4])
            ax.tick_params(axis="x", labelsize=7.5)
            ax.set_xlabel("Regression-adjusted SMD", fontsize=8)
            if column_index == 0:
                ax.set_ylabel(contrast_label, fontsize=9, labelpad=90)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)

    for row in axes:
        row[0].set_yticks(list(ypos))
        row[0].set_yticklabels([LABELS[cov] for cov in order], fontsize=8)
        row[0].set_ylim(-0.6, len(order) - 0.4)

    legend = [
        Line2D([0], [0], marker="o", color="w", mfc="white", mec=unw_col, mew=1.3,
               ms=7, label="Unweighted"),
        Line2D([0], [0], marker="o", color="w", mfc=wt_col, mec=wt_col, ms=7,
               label="IPTW-IPCW weighted"),
    ]
    fig.legend(
        handles=legend, loc="lower center", ncol=2, frameon=False,
        fontsize=9, bbox_to_anchor=(0.5, 0.005),
    )
    fig.tight_layout(rect=(0.09, 0.045, 1, 1), h_pad=2.2, w_pad=1.0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
