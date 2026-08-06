"""Single source of truth for paths, variable names, covariate sets, and
recoding conventions for the ELSA arts-engagement pipeline.

Nothing downstream should redefine a path, covariate list, or recode rule;
import from here.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths. PROJ is the repository root (parent of code/). One editable anchor,
# everything else derived.
# ---------------------------------------------------------------------------
PROJ = Path(__file__).resolve().parents[2]

ELSA_ROOT = PROJ / "ELSA (English Longitudinal Study of Aging)" / "UKDA-5050-stata"
WAVES = ELSA_ROOT / "stata" / "stata13_se"
HARM = WAVES / "gh_elsa_h.dta"
EOL = WAVES / "h_elsa_eol_a2.dta"
EOL_W10 = WAVES / "elsa_endoflife_hcap2_w10.dta"
PGS_ROOT = (PROJ / "ELSA (English Longitudinal Study of Aging)" /
            "UKDA-8773-stata" / "UKDA-8773-stata" / "stata" / "stata13")

DATA = PROJ / "data"
OUT = PROJ / "output"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"
LOGS = OUT / "logs"

# Wave-specific core files carrying the self-completion arts items.
WAVE_FILES = {
    2: "wave_2_core_data_v4.dta",
    3: "wave_3_elsa_data_v4.dta",
    4: "wave_4_elsa_data_v3.dta",
    5: "wave_5_elsa_data_v4.dta",
    6: "wave_6_elsa_data_v2.dta",
    7: "wave_7_elsa_data.dta",
    8: "wave_8_elsa_data_eul_v2.dta",
    9: "wave_9_elsa_data_eul_v2.dta",
    10: "wave_10_elsa_data_eul_v4.dta",
}

# Calendar midpoints of each wave's fieldwork (from 01/03_build).
WAVE_YEAR = {2: 2004.5, 3: 2006.5, 4: 2008.5, 5: 2010.5, 6: 2012.5,
             7: 2014.5, 8: 2016.5, 9: 2018.5, 10: 2022.0}
BASELINE_YEAR = 2004.5
BASELINE_MIN_AGE = 50

# ---------------------------------------------------------------------------
# Covariate sets for the outcome/weight models. FACTOR entries are expanded to
# dummies dropping the base level; CONT entries enter linearly. This matches
# the `i.` / bare-continuous distinction in the Stata specifications.
# ---------------------------------------------------------------------------
# Full baseline covariate set (time-invariant), as in every outcome model.
BASELINE_FACTORS = [
    "female", "white", "married", "edu4", "wealth5", "working",
    "poor_sight", "poor_hearing", "r2psyche", "r2cancre", "r2lunge",
    "cvd_any", "other_ltc", "smoke_now", "any_mobil", "any_adl", "any_iadl",
]
BASELINE_CONT = ["cesd", "alcfreq", "cog_mean"]
# Multi-level factors and their ordered levels (base = first, dropped).
FACTOR_LEVELS = {
    "arts3": [0, 1, 2],
    "arts3_lag": [0, 1, 2],
    "edu4": [1, 2, 3, 4],
    "wealth5": [1, 2, 3, 4, 5],
}

# Time-varying confounders L_t (concurrent), as in the MSM denominator models.
TV_FACTORS = ["any_mobil_tv", "any_adl_tv", "any_iadl_tv", "cancre", "lunge",
              "cvd_any_tv", "smoke_now_tv", "poor_sight_tv", "poor_hear_tv"]
TV_CONT = ["cog_tv", "cesd_w"]

# The 11 time-varying confounders reported in the balance diagnostics, in the
# order used by weight_balance.csv / weight_balance_stratified.csv.
BALANCE_CONFOUNDERS = ["any_mobil_tv", "any_adl_tv", "any_iadl_tv", "cog_tv",
                       "cancre", "lunge", "cvd_any_tv", "smoke_now_tv",
                       "cesd_w", "poor_sight_tv", "poor_hear_tv"]

# Genetic sensitivity-analysis design.
PGS_N_PCS = 10

# Grouped discrete-time hazard periods (baseline hazard).
def hazard_period(wave):
    if wave in (6, 7, 8):
        return 68
    if wave in (9, 10):
        return 910
    return int(wave)

# Published Fancourt & Steptoe NHS-linked benchmark (external reference).
PUBLISHED_DEATHS = 2001
FANCOURT_HR_FREQUENT = 0.69
FANCOURT_HR_FREQUENT_CI = (0.59, 0.80)
FANCOURT_HR_INFREQUENT = 0.86
FANCOURT_HR_INFREQUENT_CI = (0.77, 0.96)

# Reporting/diagnostic conventions. These are design thresholds, not expected
# result directions, and are shared by the manuscript and figures.
SMD_IMBALANCE_THRESHOLD = 0.10
SMD_SUBSTANTIAL_THRESHOLD = 0.25

# Reproducibility.
UNDERCOUNT_SEED = 26461022
