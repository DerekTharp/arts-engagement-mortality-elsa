"""06_tables — Table 1 (baseline characteristics) and the arts transition matrix.

Table 2 is produced by 05 (single source of truth).
Produces: output/tables/table1.csv, output/tables/transitions.csv
"""
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C
from pyelsa import io


def sfmt(x, dec=1):
    """Stata string(x, "%.<dec>f"): round half away from zero."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    q = Decimal(10) ** -dec
    return str(Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP))


def build():
    b = io.read_dta(C.DATA / "fancourt_baseline.dta")
    n = {c: int((b["arts3"] == c).sum()) for c in (0, 1, 2)}
    nt = len(b)

    def col_counts(mask):
        return [int((mask & (b["arts3"] == c)).sum()) for c in (0, 1, 2)] + [int(mask.sum())]

    def pct(cnt, denoms):
        return [sfmt(100 * cnt[i] / denoms[i]) for i in range(4)]

    denoms = [n[0], n[1], n[2], nt]
    lines = ["Variable,Level,Never (N=),Never %,Infrequent (N=),Infrequent %,"
             "Frequent (N=),Frequent %,Total (N=),Total %"]
    lines.append(f"N,,{n[0]},,{n[1]},,{n[2]},,{nt},")

    def mean_sd_row(label, col, dec=1):
        cells = []
        for c in (0, 1, 2):
            s = b.loc[b["arts3"] == c, col]
            cells += [str(len(s)), f"{sfmt(s.mean(), dec)} ({sfmt(s.std(ddof=1), dec)})"]
        s = b[col]
        cells += [str(nt), f"{sfmt(s.mean(), dec)} ({sfmt(s.std(ddof=1), dec)})"]
        return f"{label},," + ",".join(cells)

    lines.append(mean_sd_row("Age (mean (SD))", "r2agey"))

    agecat = np.select([(b["r2agey"] >= C.BASELINE_MIN_AGE) & (b["r2agey"] < 60),
                        (b["r2agey"] >= 60) & (b["r2agey"] < 70),
                        (b["r2agey"] >= 70) & (b["r2agey"] < 80),
                        b["r2agey"] >= 80], [1, 2, 3, 4], default=np.nan)
    for a, lab in ((1, "50-59"), (2, "60-69"), (3, "70-79"), (4, "80+")):
        cnt = col_counts(pd.Series(agecat == a, index=b.index))
        p = pct(cnt, denoms)
        lines.append(f"Age group,{lab}," + ",".join(f"{cnt[i]},{p[i]}" for i in range(4)))

    binvars = [("Female", "female"), ("White", "white"), ("Married/cohabiting", "married"),
               ("Employed", "working"), ("CVD (any)", "cvd_any"), ("Cancer", "r2cancre"),
               ("Lung disease", "r2lunge"), ("Psychiatric condition", "r2psyche"),
               ("Any mobility limitation", "any_mobil"), ("Any ADL limitation", "any_adl"),
               ("Any IADL limitation", "any_iadl"), ("Poor eyesight", "poor_sight"),
               ("Poor hearing", "poor_hearing"), ("Current smoker", "smoke_now")]
    for lab, v in binvars:
        cnt = col_counts(b[v] == 1)
        p = pct(cnt, denoms)
        lines.append(f"{lab}," + "," + ",".join(f"{cnt[i]},{p[i]}" for i in range(4)))

    for e, lab in ((1, "No qualification"), (2, "Age-16 qualification"),
                   (3, "Age-18 qualification"), (4, "Degree")):
        cnt = col_counts(b["edu4"] == e)
        p = pct(cnt, denoms)
        lines.append(f"Education,{lab}," + ",".join(f"{cnt[i]},{p[i]}" for i in range(4)))

    lines.append(mean_sd_row("CES-D (mean (SD))", "cesd"))
    lines.append(mean_sd_row("Cognition z-score (mean (SD))", "cog_mean", dec=2))

    cnt = col_counts(b["died"] == 1)
    p = pct(cnt, denoms)
    lines.append("Died during follow-up," + "," + ",".join(f"{cnt[i]},{p[i]}" for i in range(4)))

    lines.append(mean_sd_row("Follow-up years (mean (SD))", "fu_years"))

    C.TABLES.mkdir(parents=True, exist_ok=True)
    (C.TABLES / "table1.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- transition matrix ----
    p = io.read_dta(C.DATA / "fancourt_panel.dta").sort_values(["idauniq", "wave"])
    p["arts3_prev"] = p.groupby("idauniq")["arts3"].shift(1)
    p = p[p["arts3_prev"].notna() & p["arts3"].notna() & (p["observed"] == 1)]
    names = {0: "Never", 1: "Infrequent", 2: "Frequent"}
    tl = ["From,To,N,Pct_of_from"]
    for fr in (0, 1, 2):
        nfrom = int((p["arts3_prev"] == fr).sum())
        for to in (0, 1, 2):
            c = int(((p["arts3_prev"] == fr) & (p["arts3"] == to)).sum())
            tl.append(f"{names[fr]},{names[to]},{c},{sfmt(100 * c / nfrom)}")
    (C.TABLES / "transitions.csv").write_text("\n".join(tl) + "\n", encoding="utf-8")
    print("06 complete: table1.csv, transitions.csv")


if __name__ == "__main__":
    build()
