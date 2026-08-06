"""08_pgs_sensitivity — polygenic-score sensitivity analyses.

Produces output/tables/table_pgs.csv.
Restricted to genotyped white-British participants with the configured genetic
principal-component adjustment.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C
from pyelsa import io
from pyelsa import models as M

# PGS models drop `white` (sample is all white British).
PGS_FACTORS = [f for f in C.BASELINE_FACTORS if f != "white"]
PCS = [f"pc{i}" for i in range(1, C.PGS_N_PCS + 1)]


def build():
    b = io.read_dta(C.DATA / "fancourt_baseline.dta")
    pgs = io.read_dta(C.PGS_ROOT / "list_pgs_scores_elsa_2022.dta",
                      columns=["idauniq", "EA_3", "Height", "GC_2018", "SEC_DEP"])
    pcs = io.read_dta(C.PGS_ROOT / "principal_components_elsa_2022.dta",
                      columns=["idauniq"] + PCS)
    b = b.merge(pgs, on="idauniq", how="left").merge(pcs, on="idauniq", how="left")
    b = b[b["EA_3"].notna() & (b["white"] == 1)].copy()
    for v in ["EA_3", "Height", "GC_2018", "SEC_DEP"]:
        b[f"z_{v}"] = io.zstd(b[v])

    entry = b["r2agey"].values
    exit_ = (b["r2agey"] + b["fu_years"]).values
    event = (b["died"] == 1).values

    def cox(extra_cols):
        X = io.build_design(b, ["arts3"] + PGS_FACTORS, C.BASELINE_CONT,
                            extra=[(c, b[c].values) for c in extra_cols])
        keep = X.notna().all(axis=1).values
        r = M.cox_ph(X[keep].values, entry[keep], exit_[keep], event[keep])
        return X, r, int(keep.sum()), int(event[keep].sum())

    X0, r0, n0, d0 = cox([])
    X1, r1, n1, d1 = cox(["z_EA_3"] + PCS)
    X2, r2, n2, d2 = cox(["z_EA_3", "z_GC_2018", "z_SEC_DEP"] + PCS)

    def hr(X, r, name):
        i = list(X.columns).index(name)
        return M.hr_ci(r["beta"][i], r["se"][i])

    # ordered logit: arts3 ~ z_EA_3 + age + age^2 + covariates + PCs
    age = [("agey", b["r2agey"].values.astype(float)),
           ("agey2", b["r2agey"].values.astype(float) ** 2)]
    Xo = io.build_design(b, PGS_FACTORS, C.BASELINE_CONT,
                         extra=[("z_EA_3", b["z_EA_3"].values)] + age
                               + [(c, b[c].values) for c in PCS])
    keep = Xo.notna().all(axis=1).values
    ro = M.ologit(b["arts3"].values[keep], Xo[keep].values)
    ie = list(Xo.columns).index("z_EA_3")
    or_ea = np.exp(ro["beta"][ie]); se_ea = ro["se"][ie]
    or_lo = np.exp(ro["beta"][ie] - 1.96 * se_ea); or_hi = np.exp(ro["beta"][ie] + 1.96 * se_ea)
    z_ea = ro["beta"][ie] / se_ea
    p_arts = 2 * (1 - stats.norm.cdf(abs(z_ea)))

    # OLS: z_Height ~ arts3 + age + age^2 + covariates + PCs (with intercept)
    Xh = io.build_design(b, ["arts3"] + PGS_FACTORS, C.BASELINE_CONT,
                         extra=age + [(c, b[c].values) for c in PCS])
    keep = Xh.notna().all(axis=1).values
    Xh = Xh[keep]
    Xh_i = np.column_stack([np.ones(len(Xh)), Xh.values])
    rh = M.ols(b["z_Height"].values[keep], Xh_i)
    cols_i = ["_const"] + list(Xh.columns)
    ht = {}
    for lev, name in ((1, "arts3_1"), (2, "arts3_2")):
        i = cols_i.index(name)
        coef, se = rh["beta"][i], rh["se"][i]
        t = coef / se
        p = 2 * stats.t.sf(abs(t), rh["df_resid"])
        ht[lev] = (coef, se, p)

    lines = ["Model,Exposure,HR,CI_low,CI_high,N,Deaths,P_value,Note"]
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        h, lo, hi = hr(X0, r0, f"arts3_{lev}")
        lines.append(f"Cox (no PGS; genotyped),{lab},{h:.2f},{lo:.2f},{hi:.2f},{n0},{d0},,Reference")
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        h, lo, hi = hr(X1, r1, f"arts3_{lev}")
        lines.append(
            f"Cox + PGS-education,{lab},{h:.2f},{lo:.2f},{hi:.2f},"
            f"{n1},{d1},,+ EA_3 + {C.PGS_N_PCS} PCs"
        )
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        h, lo, hi = hr(X2, r2, f"arts3_{lev}")
        lines.append(
            f"Cox + PGS-education/cognition/deprivation,{lab},"
            f"{h:.2f},{lo:.2f},{hi:.2f},{n2},{d2},,"
            f"+ EA_3 + GC_2018 + SEC_DEP + {C.PGS_N_PCS} PCs"
        )
    ie1 = list(X1.columns).index("z_EA_3")
    hea, lea, hiea = M.hr_ci(r1["beta"][ie1], r1["se"][ie1])
    lines.append(f"PGS-education own effect,,{hea:.2f},{lea:.2f},{hiea:.2f},{n1},{d1},,HR per SD")
    lines.append(f"PGS-education predicting arts engagement,,{or_ea:.3f},{or_lo:.3f},{or_hi:.3f},"
                 f"{n1},,{p_arts:.6g},OR per SD (ordered logit)")
    lines.append("")
    lines.append("PGS-height negative control (arts predicting genetic height)")
    lines.append("Exposure,Coeff_SD,SE,P_value,Note")
    for lev, lab in ((1, "Infrequent vs never"), (2, "Frequent vs never")):
        coef, se, p = ht[lev]
        lines.append(f"{lab},{coef:.4f},{se:.4f},{p:.3f},OLS regression of z_Height on arts3")

    C.TABLES.mkdir(parents=True, exist_ok=True)
    (C.TABLES / "table_pgs.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"08 complete: table_pgs.csv (N={n0}, deaths={d0})")


if __name__ == "__main__":
    build()
