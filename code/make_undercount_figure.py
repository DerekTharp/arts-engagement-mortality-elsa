"""
Render the death-undercount sensitivity heatmap (Supplementary Figure S2).

Reads:  output/tables/death_undercount_sensitivity.csv
Writes: output/figures/figure_s2_undercount_grid.png

The grid varies the number of unobserved deaths assumed (n_extra) and the
relative risk of allocation to never-engagers vs frequent-engagers
(rr_alloc). Cells show the simulation median HR for frequent vs never.
The published Fancourt point estimate is reported from the shared config.
"""

import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from pyelsa import config as C

CSV  = ROOT / "output" / "tables" / "death_undercount_sensitivity.csv"
OUT  = ROOT / "output" / "figures" / "figure_s2_undercount_grid.png"
TABLE1 = ROOT / "output" / "tables" / "table1.csv"

if not CSV.exists():
    print(f"ERROR: {CSV} not found. Run python3 code/run_all.py first.",
          file=sys.stderr)
    sys.exit(1)

# Read grid
rows = []
with open(CSV) as f:
    reader = csv.DictReader(f)
    for r in reader:
        if r["exposure"] != "Frequent":
            continue
        rows.append({
            "n_extra":   int(r["n_extra"]),
            "rr_alloc":  float(r["rr_alloc"]),
            "HR_median": float(r["HR_median"]),
            "HR_p2_5":   float(r["HR_p2_5"]),
            "HR_p97_5":  float(r["HR_p97_5"]),
            "n_reps":    int(r["n_reps"]),
        })

if not rows:
    print("ERROR: no Frequent-exposure rows found in sensitivity CSV.", file=sys.stderr)
    sys.exit(1)

# Derive the published-versus-reconstructed death-count gap from current
# Table 1 rather than duplicating it in the plotting code.
with TABLE1.open(newline="", encoding="utf-8-sig") as handle:
    death_rows = [
        row
        for row in csv.DictReader(handle)
        if row.get("Variable") == "Died during follow-up"
        and row.get("Level", "") == ""
    ]
if len(death_rows) != 1:
    print("ERROR: Table 1 death anchor is missing or ambiguous.", file=sys.stderr)
    sys.exit(1)
baseline_deaths = int(float(death_rows[0]["Total (N=)"]))
calibration_extra = C.PUBLISHED_DEATHS - baseline_deaths

# Build the 2D grid
n_extras  = sorted(set(r["n_extra"]  for r in rows))
rr_allocs = sorted(set(r["rr_alloc"] for r in rows))
n_reps = sorted({r["n_reps"] for r in rows})
if len(n_reps) != 1:
    print("ERROR: inconsistent repetition counts in sensitivity CSV.", file=sys.stderr)
    sys.exit(1)
grid = np.full((len(rr_allocs), len(n_extras)), np.nan)
for r in rows:
    i = rr_allocs.index(r["rr_alloc"])
    j = n_extras.index(r["n_extra"])
    grid[i, j] = r["HR_median"]

# Plot
fig, ax = plt.subplots(1, 1, figsize=(8.4, 5.6))

# Use a diverging colormap centred on HR = 1.0
vmin = 0.4
vmax = 1.0
im = ax.imshow(grid, aspect='auto', cmap='RdYlBu_r',
               vmin=vmin, vmax=vmax, origin='lower')

ax.set_xticks(range(len(n_extras)))
ax.set_xticklabels(n_extras)
ax.set_yticks(range(len(rr_allocs)))
ax.set_yticklabels([f"{rr:g}" for rr in rr_allocs])
ax.set_xlabel("Assumed number of unobserved deaths added to the public-data sample",
              fontsize=10)
ax.set_ylabel("Allocation RR\n(never vs frequent)", fontsize=10)
ax.set_title("Death-undercount sensitivity: simulation-median HR for frequent vs never",
             fontsize=11, pad=32)

# Annotate each cell with the median HR (and a small p2.5–p97.5 range)
cell_ranges = {(r["n_extra"], r["rr_alloc"]): (r["HR_p2_5"], r["HR_p97_5"]) for r in rows}
for i, rr in enumerate(rr_allocs):
    for j, ne in enumerate(n_extras):
        med = grid[i, j]
        lo, hi = cell_ranges.get((ne, rr), (None, None))
        if np.isnan(med):
            continue
        # Choose annotation colour based on cell intensity
        text_color = "white" if med < 0.6 or med > 0.9 else "black"
        ax.text(j, i, f"{med:.2f}\n({lo:.2f}-{hi:.2f})",
                ha="center", va="center", fontsize=7.5, color=text_color)

# Calibration line: highlight the current published-data death-count gap.
if calibration_extra in n_extras:
    j_calibration = n_extras.index(calibration_extra)
    ax.axvline(
        j_calibration, color="black", linestyle=":", linewidth=0.8, alpha=0.6
    )
    ax.text(j_calibration + 0.05, 1.015,
            "Fancourt gap\n(calibration)",
            transform=ax.get_xaxis_transform(), ha="left", va="bottom",
            fontsize=7, color="black", alpha=0.75,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})

cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Median HR (frequent vs never)", fontsize=9)

fig.text(0.5, 0.015,
         f"Cells show the simulation-median HR across {n_reps[0]} reps per scenario. "
         "Parenthesised range is the 2.5th–97.5th simulation percentile, "
         "not a confidence interval. Fancourt & Steptoe (2019) reported "
         f"HR {C.FANCOURT_HR_FREQUENT:.2f} in the NHS-linked endpoint.",
         ha="center", fontsize=8, style="italic")

fig.tight_layout(rect=(0, 0.09, 1, 0.93))
plt.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Undercount sensitivity heatmap saved to {OUT.relative_to(ROOT)}")
