"""02_cox_replication — reproduce the Fancourt & Steptoe baseline Cox model.

Display/log only; the table2 baseline-Cox row is written by 05 (single
source of truth).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C
from pyelsa import io
from pyelsa import models as M


def main():
    b = io.read_dta(C.DATA / "fancourt_baseline.dta")
    assert 5500 < len(b) < 8000
    X = io.build_design(b, ["arts3"] + C.BASELINE_FACTORS, C.BASELINE_CONT)
    keep = X.notna().all(axis=1).values
    r = M.cox_ph(X[keep].values, b["r2agey"].values[keep],
                 (b["r2agey"] + b["fu_years"]).values[keep], (b["died"] == 1).values[keep])
    print(f"Baseline-fixed Cox (N={r['n']}, deaths={r['n_events']}):")
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        i = list(X.columns).index(f"arts3_{lev}")
        hr, lo, hi = M.hr_ci(r["beta"][i], r["se"][i])
        print(f"  {lab} vs never: HR {hr:.2f} ({lo:.2f}-{hi:.2f})")
    print(
        "Fancourt 2019: "
        f"Frequent {C.FANCOURT_HR_FREQUENT:.2f} "
        f"({C.FANCOURT_HR_FREQUENT_CI[0]:.2f}-"
        f"{C.FANCOURT_HR_FREQUENT_CI[1]:.2f}); "
        f"Infrequent {C.FANCOURT_HR_INFREQUENT:.2f} "
        f"({C.FANCOURT_HR_INFREQUENT_CI[0]:.2f}-"
        f"{C.FANCOURT_HR_INFREQUENT_CI[1]:.2f})"
    )


if __name__ == "__main__":
    main()
