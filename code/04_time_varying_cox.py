"""04_time_varying_cox — supplementary time-varying Cox (age timescale, cluster-
robust). Display/log only; the table2 time-varying-Cox row is written by 05.

Categorical Model C.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C
from pyelsa import io

# The categorical time-varying Cox (Model C) is estimated by the shared helper
# in 05 so the specification lives in one place.
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "m05", str(Path(__file__).resolve().parent / "05_msm_iptw.py"))
_m05 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m05)


def main():
    base = io.read_dta(C.DATA / "fancourt_baseline.dta")
    out = _m05.tv_cox(base)
    hr, lo, hi, n, d = out[2]
    print(f"Time-varying Cox Model C (N={n}, deaths={d}):")
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        hr, lo, hi, n, d = out[lev]
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
