"""09_death_undercount_sensitivity — quantitative bias analysis for the
public-data death undercount.

Port of 09_death_undercount_sensitivity.do. Produces
output/tables/death_undercount_sensitivity.csv.

Note: this is a stochastic simulation. The n_extra=0 rows are deterministic and
reproduce the Stata output exactly; the n_extra>0 cells are simulation medians
over 200 reps and differ from the Stata run within simulation noise, because
numpy's RNG draws differ from Stata's. The seed fixes the Python run.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C
from pyelsa import io
from pyelsa import models as M

N_EXTRA_GRID = [0, 200, 400, 600, 800, 979, 1000]
RR_GRID = ["0.5", "0.67", "1.0", "1.5", "2.0", "3.0", "5.0"]
NREPS = 200
NOTE = (
    f"deterministic grid; sim intervals over {NREPS} reps with extras allocated "
    "by RR"
)


def build():
    b = io.read_dta(C.DATA / "fancourt_baseline.dta")
    admin = float(b["exit_year"].max())

    died = (b["died"] == 1).values
    arts3 = b["arts3"].values
    r2agey = b["r2agey"].values.astype(float)
    baseline_year = b["baseline_year"].values.astype(float)
    fu_years = b["fu_years"].values.astype(float)
    exit_year = b["exit_year"].values.astype(float)

    unobs_lo = np.where(~died, exit_year + 1, np.nan)
    unobs_win = np.where(~died, admin - unobs_lo + 1, np.nan)
    eligible = (~died) & (unobs_win >= 1)

    # design matrix (constant across reps)
    X = io.build_design(b, ["arts3"] + C.BASELINE_FACTORS, C.BASELINE_CONT)
    Xv = X.values
    ai = list(X.columns).index("arts3_1")
    fi = list(X.columns).index("arts3_2")

    rng = np.random.default_rng(C.UNDERCOUNT_SEED)

    # Observed-data fit; its beta warm-starts every simulated fit.
    keep0 = fu_years > 0
    beta_obs = M.cox_beta_fast(Xv[keep0], r2agey[keep0], (r2agey + fu_years)[keep0], died[keep0])
    inf0, freq0 = np.exp(beta_obs[ai]), np.exp(beta_obs[fi])

    def fit(new_died, new_fu):
        keep = new_fu > 0
        beta = M.cox_beta_fast(Xv[keep], r2agey[keep], r2agey[keep] + new_fu[keep],
                               new_died[keep], init=beta_obs)
        return np.exp(beta[ai]), np.exp(beta[fi])

    rows = []
    for n_extra in N_EXTRA_GRID:
        for rr in RR_GRID:
            if n_extra == 0:
                inf_list = [inf0]; freq_list = [freq0]
            else:
                rrf = float(rr)
                w = np.where(arts3 == 0, rrf, np.where(arts3 == 1, np.sqrt(rrf), 1.0))
                inf_list, freq_list = [], []
                elig_idx = np.where(eligible)[0]
                for _ in range(NREPS):
                    u = rng.random(len(elig_idx))
                    key = -np.log(u) / w[elig_idx]
                    chosen = elig_idx[np.argsort(key)[:n_extra]]
                    nd = died.copy()
                    nx = exit_year.copy()
                    off = np.floor(rng.random(len(chosen)) * unobs_win[chosen])
                    nx[chosen] = unobs_lo[chosen] + off
                    nd[chosen] = True
                    nfu = nx - baseline_year
                    hi, hf = fit(nd, nfu)
                    inf_list.append(hi); freq_list.append(hf)
            for lab, vals in (("Infrequent", inf_list), ("Frequent", freq_list)):
                med = np.percentile(vals, 50)
                lo = np.percentile(vals, 2.5)
                hi = np.percentile(vals, 97.5)
                rows.append(f"{n_extra},{rr},{lab},{med:.3f},{lo:.3f},{hi:.3f},{NREPS},{NOTE}")
        print(f"  n_extra={n_extra} done")

    C.TABLES.mkdir(parents=True, exist_ok=True)
    header = "n_extra,rr_alloc,exposure,HR_median,HR_p2_5,HR_p97_5,n_reps,note"
    (C.TABLES / "death_undercount_sensitivity.csv").write_text(
        header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print("09 complete: death_undercount_sensitivity.csv")


if __name__ == "__main__":
    build()
