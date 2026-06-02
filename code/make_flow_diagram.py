"""
Generate the STROBE participant-flow diagram for the arts engagement
public-data reconstruction.

All counts are parsed from the validated pipeline outputs
(output/tables/table2.csv and output/tables/weight_diagnostics.csv) so the
figure cannot drift from the manuscript numbers.

Layout: main boxes are stacked with a uniform edge-to-edge gap (box heights
scale with line count), and each exclusion box is centred on the arrow between
the two main boxes it applies to.

Output: output/figures/figure_s1_flow.png
"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

TABLES = Path(__file__).resolve().parent.parent / "output" / "tables"


def _read_table2():
    out = {}
    for r in csv.DictReader((TABLES / "table2.csv").open()):
        out[r["Model"]] = (int(float(r["N"])), int(float(r["Deaths"])))
    return out


def _read_weight_diag():
    out = {}
    for r in csv.DictReader((TABLES / "weight_diagnostics.csv").open()):
        out[r["stat"]] = r["value"]
    return out


t2 = _read_table2()
wd = _read_weight_diag()
n_baseline, d_baseline = t2["Baseline-fixed Cox"]
n_outcome = int(float(wd["n_outcome"]))
n_missing = int(float(wd["n_missing_weight"]))
n_panel_pre = n_outcome + n_missing
_, d_panel = t2["MSM IPTW+IPCW cloglog"]

# --- content -----------------------------------------------------------------
MAIN = [
    "ELSA wave 2 (2004–05) respondents\naged 50 years or older",
    f"Baseline analytic sample (N = {n_baseline:,})\n"
    "Complete data on arts engagement and\nall baseline covariates",
    f"Baseline-fixed Cox model (full sample)\n"
    f"N = {n_baseline:,}; {d_baseline:,} deaths over follow-up\n"
    "(Figure 2: “Baseline-fixed Cox”)",
    "Monotone-censored person-wave panel\n"
    "Intervals from wave 2 until the first non-interview\n"
    "or missing arts items; later waves censored",
    f"Person-wave intervals before weight exclusion\n{n_panel_pre:,} intervals",
    f"Outcome-model analytic sample\n"
    f"{n_outcome:,} person-wave intervals; {d_panel:,} deaths\n"
    "(Figure 2: cloglog panel, discrete-time PH, MSM)",
]
# exclusion text keyed by the gap after main-box index i
EXCL = {
    0: "Excluded: missing self-completion\narts items or baseline covariates",
    2: "Person-waves dropped at or after the\nfirst non-interview or missing arts items",
    4: f"Excluded: {n_missing} person-wave intervals\nwith missing weight-model inputs",
}

# --- layout constants (data units; axis aspect is equal) ---------------------
W = 6.6          # main box width
WX = 4.4         # exclusion box width
LH = 0.46        # line height
PAD = 0.55       # vertical padding inside a box
GAP = 0.95       # uniform edge-to-edge gap between main boxes
X = 0.0          # main column centre
XCOL = X + W / 2 + 1.0 + WX / 2   # exclusion column centre


def nlines(t):
    return t.count("\n") + 1


def height(t):
    return nlines(t) * LH + PAD


fig, ax = plt.subplots(figsize=(8.4, 10.2))
ax.set_aspect("equal")
ax.axis("off")

# stack main boxes from the top with uniform edge gaps
centres = []
y = 0.0
for t in MAIN:
    h = height(t)
    cy = y - h / 2
    centres.append((cy, h))
    y = cy - h / 2 - GAP


def draw_box(cx, cy, w, h, text, fc="white", ec="black", lw=1.2, fs=9.5):
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.16",
        facecolor=fc, edgecolor=ec, linewidth=lw, mutation_aspect=1.0))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            family="Times New Roman")


# main boxes
for t, (cy, h) in zip(MAIN, centres):
    draw_box(X, cy, W, h, t)

# vertical arrows between consecutive main boxes
for i in range(len(MAIN) - 1):
    y0 = centres[i][0] - centres[i][1] / 2
    y1 = centres[i + 1][0] + centres[i + 1][1] / 2
    ax.annotate("", xy=(X, y1), xytext=(X, y0),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.3))

# exclusion boxes centred on the relevant arrow, with a horizontal side arrow
for i, text in EXCL.items():
    y_mid = (centres[i][0] - centres[i][1] / 2
             + centres[i + 1][0] + centres[i + 1][1] / 2) / 2
    draw_box(XCOL, y_mid, WX, height(text), text,
             fc="#f4f4f4", ec="gray", lw=0.9, fs=8.5)
    ax.annotate("", xy=(XCOL - WX / 2, y_mid), xytext=(X, y_mid),
                arrowprops=dict(arrowstyle="-|>", color="gray", lw=0.9))

# title and limits
top_edge = centres[0][0] + centres[0][1] / 2
bot_edge = centres[-1][0] - centres[-1][1] / 2
ax.text(X, top_edge + 0.85, "Participant flow", ha="center", va="center",
        fontsize=13, weight="bold", family="Times New Roman")
ax.set_xlim(X - W / 2 - 0.5, XCOL + WX / 2 + 0.5)
ax.set_ylim(bot_edge - 0.5, top_edge + 1.5)

plt.savefig("output/figures/figure_s1_flow.png",
            dpi=200, bbox_inches="tight", facecolor="white")
print(f"Flow diagram saved (N={n_baseline:,}; panel {n_outcome:,}; "
      f"{d_panel:,} deaths) to output/figures/figure_s1_flow.png")
