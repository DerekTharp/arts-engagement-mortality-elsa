"""
build_manuscript.py

Reads canonical CSV outputs and populates the manuscript, supplement, STROBE,
and cover-letter templates with current values. Every data-derived reporting
number comes through this script.

Usage:
    python3 code/build_manuscript.py

Inputs:
    output/tables/table1.csv
    output/tables/table2.csv
    output/tables/transitions.csv
    output/tables/weight_diagnostics.csv
    output/tables/table_pgs.csv

Outputs:
    manuscript/manuscript.md
    manuscript/supplement.md
    manuscript/strobe_checklist.md
    manuscript/cover_letter.md
"""

import argparse
import csv
import re
import sys
from pathlib import Path

from pyelsa import config as C

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "output" / "tables"
TEMPLATE = ROOT / "manuscript" / "manuscript_template.md"
OUTPUT = ROOT / "manuscript" / "manuscript.md"
SUPPLEMENT_TEMPLATE = ROOT / "manuscript" / "supplement_template.md"
SUPPLEMENT_OUTPUT = ROOT / "manuscript" / "supplement.md"
STROBE_TEMPLATE = ROOT / "manuscript" / "strobe_checklist_template.md"
STROBE_OUTPUT = ROOT / "manuscript" / "strobe_checklist.md"
COVER_TEMPLATE = ROOT / "manuscript" / "cover_letter_template.md"
COVER_OUTPUT = ROOT / "manuscript" / "cover_letter.md"


def read_csv_dict(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_values():
    v = {}

    # --- Table 1: baseline characteristics ---
    t1 = read_csv_dict(TABLES / "table1.csv")
    t1_by_var = {}
    for row in t1:
        key = (row["Variable"], row.get("Level", ""))
        t1_by_var[key] = row

    n_row = t1_by_var[("N", "")]
    v["n_baseline"] = f"{int(float(n_row['Total (N=)'])):,}"
    v["n_never"] = f"{int(float(n_row['Never (N=)'])):,}"
    v["n_infrequent"] = f"{int(float(n_row['Infrequent (N=)'])):,}"
    v["n_frequent"] = f"{int(float(n_row['Frequent (N=)'])):,}"

    # Age means
    age_row = t1_by_var[("Age (mean (SD))", "")]
    v["age_mean_never"] = age_row["Never %"].split(" ")[0]
    v["age_mean_frequent"] = age_row["Frequent %"].split(" ")[0]

    # Binary variable percentages
    def get_pct(varname, cat):
        row = t1_by_var.get((varname, ""), None)
        if row is None:
            return "?"
        return row[f"{cat} %"]

    v["mobil_pct_never"] = get_pct("Any mobility limitation", "Never")
    v["mobil_pct_frequent"] = get_pct("Any mobility limitation", "Frequent")
    v["adl_pct_never"] = get_pct("Any ADL limitation", "Never")
    v["adl_pct_frequent"] = get_pct("Any ADL limitation", "Frequent")
    v["sight_pct_never"] = get_pct("Poor eyesight", "Never")
    v["sight_pct_frequent"] = get_pct("Poor eyesight", "Frequent")
    v["died_pct_never"] = get_pct("Died during follow-up", "Never")
    v["died_pct_frequent"] = get_pct("Died during follow-up", "Frequent")

    # Deaths count
    died_row = t1_by_var[("Died during follow-up", "")]
    v["n_deaths_baseline"] = f"{int(float(died_row['Total (N=)'])):,}"

    # --- Table 2: model comparison ---
    t2 = read_csv_dict(TABLES / "table2.csv")

    def get_t2(model, exposure):
        for row in t2:
            if row["Model"] == model and row["Exposure"] == exposure:
                return row
        return None

    # Baseline-fixed Cox
    r = get_t2("Baseline-fixed Cox", "Frequent")
    v["hr_baseline_frequent"] = r["HR"]
    v["ci_baseline_frequent_lo"] = r["CI_low"]
    v["ci_baseline_frequent_hi"] = r["CI_high"]
    r = get_t2("Baseline-fixed Cox", "Infrequent")
    v["hr_baseline_infrequent"] = r["HR"]
    v["ci_baseline_infrequent_lo"] = r["CI_low"]
    v["ci_baseline_infrequent_hi"] = r["CI_high"]

    # Baseline-fixed cloglog (same panel)
    r = get_t2("Baseline-fixed cloglog (panel)", "Frequent")
    v["hr_bfcl_frequent"] = r["HR"]
    v["ci_bfcl_frequent_lo"] = r["CI_low"]
    v["ci_bfcl_frequent_hi"] = r["CI_high"]
    r = get_t2("Baseline-fixed cloglog (panel)", "Infrequent")
    v["hr_bfcl_infrequent"] = r["HR"]
    v["ci_bfcl_infrequent_lo"] = r["CI_low"]
    v["ci_bfcl_infrequent_hi"] = r["CI_high"]

    # Time-varying Cox
    r = get_t2("Time-varying Cox", "Frequent")
    v["hr_tvcox_frequent"] = r["HR"]
    v["ci_tvcox_frequent_lo"] = r["CI_low"]
    v["ci_tvcox_frequent_hi"] = r["CI_high"]
    # Time-varying Cox uses a different sample from the monotone-censored panel:
    # the stcox specification retains intervals based on time-varying covariate
    # observation rather than the strict monotone-censoring rule applied to the
    # discrete-time panel models.
    v["n_tvcox_intervals"] = f"{int(float(r['N'])):,}"
    v["n_tvcox_deaths"] = f"{int(float(r['Deaths'])):,}"

    # Unweighted discrete-time PH
    r = get_t2("Unweighted discrete-time PH", "Frequent")
    v["or_uwt_frequent"] = r["HR"]
    v["ci_uwt_frequent_lo"] = r["CI_low"]
    v["ci_uwt_frequent_hi"] = r["CI_high"]

    # Concurrent-confounder-adjusted PH (concurrent L_t in the outcome model).
    # Reported as a conventional comparison on the same panel.
    r = get_t2("Concurrent-confounder-adjusted PH", "Frequent")
    if r is not None:
        v["or_naive_frequent"] = r["HR"]
        v["ci_naive_frequent_lo"] = r["CI_low"]
        v["ci_naive_frequent_hi"] = r["CI_high"]
        r_inf = get_t2("Concurrent-confounder-adjusted PH", "Infrequent")
        v["or_naive_infrequent"] = r_inf["HR"]
        v["ci_naive_infrequent_lo"] = r_inf["CI_low"]
        v["ci_naive_infrequent_hi"] = r_inf["CI_high"]
    else:
        # Sentinel so the build fails loudly until the model is estimated.
        for k in ["or_naive_frequent", "ci_naive_frequent_lo", "ci_naive_frequent_hi",
                  "or_naive_infrequent", "ci_naive_infrequent_lo", "ci_naive_infrequent_hi"]:
            v[k] = "?"

    # MSM IPTW
    r = get_t2("MSM IPTW+IPCW cloglog", "Frequent")
    v["or_msm_frequent"] = r["HR"]
    v["ci_msm_frequent_lo"] = r["CI_low"]
    v["ci_msm_frequent_hi"] = r["CI_high"]
    r = get_t2("MSM IPTW+IPCW cloglog", "Infrequent")
    v["or_msm_infrequent"] = r["HR"]
    v["ci_msm_infrequent_lo"] = r["CI_low"]
    v["ci_msm_infrequent_hi"] = r["CI_high"]

    # Panel intervals and deaths (taken from MSM IPTW row, since all three panel
    # models share the same monotone-censored sample after weight-model exclusions)
    v["n_panel_intervals"] = f"{int(float(r['N'])):,}"
    v["n_panel_deaths"] = f"{int(float(r['Deaths'])):,}"

    # --- Terminal-censoring sensitivity (Suppl. S2) ---
    # Refit of the MSM with unknown-next-status terminal intervals censored at
    # last known-alive interview instead of carried to the next scheduled wave.
    sc_path = TABLES / "sensitivity_censoring.csv"
    v["sens_cens_hr"] = v["sens_cens_lo"] = v["sens_cens_hi"] = "TBD"
    v["sens_cens_n"] = v["sens_cens_removed"] = "TBD"
    v["sens_known_alive_pct"] = v["sens_unknown_pct"] = "TBD"
    if sc_path.exists():
        for row in read_csv_dict(sc_path):
            if row["spec"].startswith("MSM primary"):
                v["sens_known_alive_pct"] = row.get("known_alive_pct", "TBD")
                v["sens_unknown_pct"] = row.get("unknown_pct", "TBD")
            if row["spec"].startswith("MSM unknown"):
                v["sens_cens_hr"] = row["HR"]
                v["sens_cens_lo"] = row["CI_low"]
                v["sens_cens_hi"] = row["CI_high"]
                v["sens_cens_n"] = f"{int(float(row['N'])):,}"
                v["sens_cens_removed"] = f"{int(float(row['n_removed'])):,}"

    # --- Weight-truncation sensitivity (Suppl. S3) ---
    sw_path = TABLES / "sensitivity_weights.csv"
    v["wt_trunc_table_md"] = (
        "_Weight-truncation sensitivity is generated by "
        "`code/05_msm_iptw.py`; rerun `code/run_all.py`._"
    )
    v["wt_untrunc_max"] = "TBD"
    if sw_path.exists():
        sw_rows = read_csv_dict(sw_path)
        lines = ["| Weight truncation | HR (95% CI), frequent vs never | Max weight |",
                 "|---|---:|---:|"]
        for r in sw_rows:
            lines.append(f"| {r['truncation']} | {r['HR']} ({r['CI_low']} to "
                         f"{r['CI_high']}) | {r['max_weight']} |")
            if r["truncation"].startswith("Untruncated"):
                v["wt_untrunc_max"] = r["max_weight"]
        v["wt_trunc_table_md"] = "\n".join(lines)

    # --- Positivity diagnostic (Suppl. S3): min predicted treatment probability ---
    pos_path = TABLES / "positivity.csv"
    v["positivity_min"] = "TBD"
    if pos_path.exists():
        pos_mins = [float(r["min_pred_prob"]) for r in read_csv_dict(pos_path)
                    if _is_number(r.get("min_pred_prob", ""))]
        if pos_mins:
            v["positivity_min"] = f"{min(pos_mins):.4f}"

    # --- Weight diagnostics ---
    wd = read_csv_dict(TABLES / "weight_diagnostics.csv")
    wd_dict = {row["stat"]: row["value"] for row in wd}
    v["wt_mean"] = wd_dict["mean"]
    v["wt_sd"] = wd_dict["sd"]
    v["wt_min"] = wd_dict["min"]
    v["wt_max"] = wd_dict["max"]
    v["wt_p5"] = wd_dict["p5"]
    v["wt_p50"] = wd_dict["p50"]
    v["wt_p95"] = wd_dict["p95"]
    v["n_missing_weight"] = wd_dict.get("n_missing_weight", "0")
    # Effective sample size (Kish): (Σw)² / Σw². ess_ratio = ESS / n_outcome.
    v["ess"] = f"{int(float(wd_dict.get('ess', 0))):,}" if "ess" in wd_dict else "TBD"
    v["ess_ratio"] = wd_dict.get("ess_ratio", "TBD")

    # Panel intervals before weight-model exclusions = outcome + missing
    n_panel_pre = int(float(wd_dict["n_outcome"])) + int(float(wd_dict["n_missing_weight"]))
    v["n_panel_pre_weight"] = f"{n_panel_pre:,}"

    # --- Transitions ---
    tr = read_csv_dict(TABLES / "transitions.csv")
    tr_dict = {}
    for row in tr:
        tr_dict[(row["From"], row["To"])] = row

    v["transition_frequent_stay"] = tr_dict[("Frequent", "Frequent")]["Pct_of_from"]
    v["transition_frequent_to_infreq"] = tr_dict[("Frequent", "Infrequent")]["Pct_of_from"]
    v["transition_frequent_to_never"] = tr_dict[("Frequent", "Never")]["Pct_of_from"]
    v["transition_never_stay"] = tr_dict[("Never", "Never")]["Pct_of_from"]
    v["transition_never_to_infreq"] = tr_dict[("Never", "Infrequent")]["Pct_of_from"]
    v["transition_never_to_frequent"] = tr_dict[("Never", "Frequent")]["Pct_of_from"]
    v["transition_infreq_stay"] = tr_dict[("Infrequent", "Infrequent")]["Pct_of_from"]
    v["transition_infreq_to_never"] = tr_dict[("Infrequent", "Never")]["Pct_of_from"]
    v["transition_infreq_to_frequent"] = tr_dict[("Infrequent", "Frequent")]["Pct_of_from"]

    # Compute change percentages (100 - stay%)
    change_pcts = []
    for cat in ["Never", "Infrequent", "Frequent"]:
        stay = float(tr_dict[(cat, cat)]["Pct_of_from"])
        change_pcts.append(100 - stay)
    v["transition_pct_change_min"] = f"{min(change_pcts):.0f}"
    v["transition_pct_change_max"] = f"{max(change_pcts):.0f}"

    # --- PGS ---
    pgs = read_csv_dict(TABLES / "table_pgs.csv")

    def get_pgs(model, exposure=None):
        for row in pgs:
            if row["Model"] == model:
                if exposure is None or row.get("Exposure", "") == exposure:
                    return row
        return None

    r = get_pgs("Cox (no PGS; genotyped)", "Frequent")
    v["n_pgs_sample"] = f"{int(float(r['N'])):,}"
    v["n_pgs_deaths"] = f"{int(float(r['Deaths'])):,}"
    v["hr_pgs_ref_frequent"] = r["HR"]
    v["ci_pgs_ref_frequent_lo"] = r["CI_low"]
    v["ci_pgs_ref_frequent_hi"] = r["CI_high"]
    r = get_pgs("Cox (no PGS; genotyped)", "Infrequent")
    v["hr_pgs_ref_infrequent"] = r["HR"]
    v["ci_pgs_ref_infrequent_lo"] = r["CI_low"]
    v["ci_pgs_ref_infrequent_hi"] = r["CI_high"]

    r = get_pgs("Cox + PGS-education", "Frequent")
    v["hr_pgs_ea_frequent"] = r["HR"]
    v["ci_pgs_ea_frequent_lo"] = r["CI_low"]
    v["ci_pgs_ea_frequent_hi"] = r["CI_high"]
    r = get_pgs("Cox + PGS-education", "Infrequent")
    v["hr_pgs_ea_infrequent"] = r["HR"]
    v["ci_pgs_ea_infrequent_lo"] = r["CI_low"]
    v["ci_pgs_ea_infrequent_hi"] = r["CI_high"]

    r = get_pgs("Cox + PGS-education/cognition/deprivation", "Frequent")
    v["hr_pgs_multi_frequent"] = r["HR"]
    v["ci_pgs_multi_frequent_lo"] = r["CI_low"]
    v["ci_pgs_multi_frequent_hi"] = r["CI_high"]
    r = get_pgs("Cox + PGS-education/cognition/deprivation", "Infrequent")
    v["hr_pgs_multi_infrequent"] = r["HR"]
    v["ci_pgs_multi_infrequent_lo"] = r["CI_low"]
    v["ci_pgs_multi_infrequent_hi"] = r["CI_high"]

    r = get_pgs("PGS-education own effect")
    hr_raw = float(r["HR"])
    ci_lo_raw = float(r["CI_low"])
    ci_hi_raw = float(r["CI_high"])
    v["hr_pgs_ea_own"] = f"{hr_raw:.2f}"
    v["ci_pgs_ea_own_lo"] = f"{ci_lo_raw:.2f}"
    v["ci_pgs_ea_own_hi"] = f"{ci_hi_raw:.2f}"

    # PGS-height negative control: read directly from the sub-table in table_pgs.csv
    # The PGS-height block sits below the main HR block under a different header
    # ("Exposure,Coeff_SD,SE,P_value,Note"). Parse manually since csv.DictReader
    # over the whole file would mis-align after the blank line.
    v["pgs_height_coeff_frequent"] = "?"
    v["pgs_height_p_frequent"] = "?"
    v["pgs_height_coeff_infrequent"] = "?"
    v["pgs_height_p_infrequent"] = "?"
    pgs_csv_text = (TABLES / "table_pgs.csv").read_text(encoding="utf-8").splitlines()
    in_height_block = False
    for line in pgs_csv_text:
        if "PGS-height negative control" in line:
            in_height_block = True
            continue
        if not in_height_block:
            continue
        if line.startswith("Frequent vs never,"):
            parts = line.split(",")
            v["pgs_height_coeff_frequent"] = parts[1]
            v["pgs_height_p_frequent"] = parts[3]
        elif line.startswith("Infrequent vs never,"):
            parts = line.split(",")
            v["pgs_height_coeff_infrequent"] = parts[1]
            v["pgs_height_p_infrequent"] = parts[3]

    # PGS-education ordered-logit OR for arts engagement: read directly from
    # table_pgs.csv (row "PGS-education predicting arts engagement").
    v["pgs_ea_or_arts"] = "?"
    v["pgs_ea_p_arts"] = "?"
    r_arts = get_pgs("PGS-education predicting arts engagement")
    if r_arts is not None:
        v["pgs_ea_or_arts"] = r_arts["HR"]
        p_arts = float(r_arts["P_value"])
        v["pgs_ea_p_arts"] = (
            "<0.001" if p_arts < 0.001 else f"={p_arts:.3f}"
        )

    # --- Baseline per-variable missingness table (consumed by supplement S7) ---
    v["baseline_missingness_table"] = build_missingness_table()

    # --- Death-undercount sensitivity (Suppl. §S8) -------------------------
    # Summary placeholders the main-text Discussion can reference. We expose
    # the simulation-median HR at the published-data death-count gap
    # under each rr_alloc level, plus a min/max bound across the whole grid.
    # If the sensitivity CSV is still in its bootstrap state (no numeric HRs),
    # fall back to "TBD" placeholders so the build still succeeds; the values
    # populate properly once 09_death_undercount_sensitivity.py has been run.
    uc_path = TABLES / "death_undercount_sensitivity.csv"
    uc_min_med = uc_max_med = uc_fancourt_rr1 = uc_fancourt_rr3 = "TBD"
    uc_fancourt_rr05 = "TBD"
    uc_n_cells = "TBD"
    uc_rr_min = uc_rr_max = "TBD"
    uc_n_extra_levels = uc_rr_levels = uc_n_reps = "TBD"
    uc_n_median_ge_null = uc_n_intervals_cross_null = "TBD"
    uc_calibration_extra = C.PUBLISHED_DEATHS - int(float(died_row["Total (N=)"]))
    if uc_path.exists():
        uc_rows = [r for r in read_csv_dict(uc_path) if r.get("exposure") == "Frequent"]
        numeric = [r for r in uc_rows if _is_number(r.get("HR_median", ""))]
        if numeric:
            medians = [float(r["HR_median"]) for r in numeric]
            uc_min_med = f"{min(medians):.2f}"
            uc_max_med = f"{max(medians):.2f}"
            uc_n_cells = str(len(numeric))
            rr_levels = sorted({float(r["rr_alloc"]) for r in numeric})
            n_extra_levels = sorted({int(r["n_extra"]) for r in numeric})
            n_reps = sorted({int(r["n_reps"]) for r in numeric})
            uc_rr_min = f"{rr_levels[0]:g}"
            uc_rr_max = f"{rr_levels[-1]:g}"
            uc_n_extra_levels = ", ".join(str(x) for x in n_extra_levels)
            uc_rr_levels = ", ".join(f"{x:g}" for x in rr_levels)
            if len(n_reps) != 1:
                raise ValueError(
                    "death-undercount CSV has inconsistent repetition counts"
                )
            uc_n_reps = str(n_reps[0])
            uc_n_median_ge_null = str(
                sum(float(r["HR_median"]) >= 1.0 for r in numeric)
            )
            uc_n_intervals_cross_null = str(
                sum(
                    float(r["HR_p2_5"]) <= 1.0 <= float(r["HR_p97_5"])
                    for r in numeric
                )
            )
            for r in numeric:
                if int(r["n_extra"]) == uc_calibration_extra and float(r["rr_alloc"]) == 1.0:
                    uc_fancourt_rr1 = f"{float(r['HR_median']):.2f}"
                if int(r["n_extra"]) == uc_calibration_extra and float(r["rr_alloc"]) == 3.0:
                    uc_fancourt_rr3 = f"{float(r['HR_median']):.2f}"
                if int(r["n_extra"]) == uc_calibration_extra and float(r["rr_alloc"]) == 0.5:
                    uc_fancourt_rr05 = f"{float(r['HR_median']):.2f}"

    v["uc_grid_min_hr"]      = uc_min_med
    v["uc_grid_max_hr"]      = uc_max_med
    v["uc_fancourt_rr1_hr"]  = uc_fancourt_rr1
    v["uc_fancourt_rr3_hr"]  = uc_fancourt_rr3
    v["uc_fancourt_rr05_hr"] = uc_fancourt_rr05
    v["uc_n_cells"]          = uc_n_cells
    v["uc_rr_min"]           = uc_rr_min
    v["uc_rr_max"]           = uc_rr_max
    v["uc_n_extra_levels"]   = uc_n_extra_levels
    v["uc_rr_levels"]        = uc_rr_levels
    v["uc_n_reps"]           = uc_n_reps
    v["uc_seed"]             = str(C.UNDERCOUNT_SEED)
    v["uc_calibration_extra"] = str(uc_calibration_extra)
    v["uc_n_median_ge_null"] = uc_n_median_ge_null
    v["uc_n_intervals_cross_null"] = uc_n_intervals_cross_null
    v["uc_intervals_cross_null_cells"] = (
        "one cell"
        if uc_n_intervals_cross_null == "1"
        else f"{uc_n_intervals_cross_null} cells"
    )

    # --- Display items (Table 1, Table 2 markdown rendered from CSVs) -------
    v["table1_md"] = render_table1_md()
    v["table2_md"] = render_table2_md()
    v["ladder_table_md"] = render_ladder_table_md()

    # --- Covariate balance table for Suppl. §S3 ----------------------------
    v["weight_balance_md"] = render_balance_md()

    # --- Stratified covariate balance (JECH R&R centrepiece) ---------------
    # SMDs before/after weighting, stratified by prior-wave exposure (A_{t-1})
    # and regression-adjusted for the remaining stabilised-numerator terms.
    v.update(build_stratified_balance())
    v["balance_stratified_summary_md"] = render_balance_stratified_summary()
    v["balance_freq_adjusted_full_md"] = render_balance_stratified_full(
        "freq_vs_never"
    )
    v["balance_infreq_adjusted_full_md"] = render_balance_stratified_full(
        "infreq_vs_never"
    )

    # Published NHS-linked death count from the original mortality analysis
    # (external published figure, not a project estimate).
    v["published_deaths"] = f"{C.PUBLISHED_DEATHS:,}"
    v["published_hr_frequent"] = f"{C.FANCOURT_HR_FREQUENT:.2f}"
    v["published_hr_frequent_lo"] = f"{C.FANCOURT_HR_FREQUENT_CI[0]:.2f}"
    v["published_hr_frequent_hi"] = f"{C.FANCOURT_HR_FREQUENT_CI[1]:.2f}"
    v["smd_imbalance_threshold"] = f"{C.SMD_IMBALANCE_THRESHOLD:.2f}"
    v["smd_substantial_threshold"] = (
        f"{C.SMD_SUBSTANTIAL_THRESHOLD:.2f}"
    )
    v["baseline_min_age"] = str(C.BASELINE_MIN_AGE)
    v["n_balance_confounders"] = str(len(C.BALANCE_CONFOUNDERS))
    v["n_pgs_pcs"] = str(C.PGS_N_PCS)

    return v


# --- Stratified balance (weight_balance_stratified.csv, from 05_msm_iptw.py) --
STRAT_LABELS = [
    ("lag_never", "Never"),
    ("lag_infrequent", "Infrequent"),
    ("lag_frequent", "Frequent"),
]
CONTRAST_LABELS = [
    ("freq_vs_never", "Frequent vs never", "Frequent"),
    ("infreq_vs_never", "Infrequent vs never", "Infrequent"),
]


def _load_stratified():
    rows = read_csv_dict(TABLES / "weight_balance_stratified.csv")
    d = {}
    for r in rows:
        d.setdefault((r["stratum"], r["contrast"]), {})[r["covariate"]] = r
    return d


def _mean_abs(recs, field):
    vals = [abs(float(r[field])) for r in recs.values() if _is_number(r.get(field, ""))]
    return sum(vals) / len(vals) if vals else float("nan")


def _strat_cells(d, stratum, contrast):
    r = next(iter(d[(stratum, contrast)].values()))
    return int(float(r["n_hi"])), int(float(r["n_lo"]))


def build_stratified_balance():
    d = _load_stratified()
    out = {}

    def sm(stratum, contrast, field):
        return _mean_abs(d.get((stratum, contrast), {}), field)

    # Retain the raw marginal frequent-versus-never summary only to illustrate
    # why it is not a diagnostic target for these stabilised weights.
    out["bal_raw_pooled_mean_unw"] = (
        f"{sm('pooled', 'freq_vs_never', 'smd_raw_unweighted'):.2f}"
    )
    out["bal_raw_pooled_mean_wt"] = (
        f"{sm('pooled', 'freq_vs_never', 'smd_raw_weighted'):.2f}"
    )

    stratum_short = {
        "lag_never": "never",
        "lag_infrequent": "infreq",
        "lag_frequent": "freq",
    }
    contrast_short = {
        "freq_vs_never": "freq",
        "infreq_vs_never": "infreq",
    }
    weighted_residuals = []
    for contrast, _, _ in CONTRAST_LABELS:
        cshort = contrast_short[contrast]
        for stratum, _ in STRAT_LABELS:
            sshort = stratum_short[stratum]
            out[f"bal_{cshort}_prior_{sshort}_adj_unw"] = (
                f"{sm(stratum, contrast, 'smd_adjusted_unweighted'):.2f}"
            )
            out[f"bal_{cshort}_prior_{sshort}_adj_wt"] = (
                f"{sm(stratum, contrast, 'smd_adjusted_weighted'):.2f}"
            )
            nh, nl = _strat_cells(d, stratum, contrast)
            out[f"n_{cshort}_prior_{sshort}"] = f"{nh:,}"
            out[f"n_never_prior_{sshort}"] = f"{nl:,}"
            weighted_residuals.extend(
                abs(float(r["smd_adjusted_weighted"]))
                for r in d[(stratum, contrast)].values()
                if _is_number(r.get("smd_adjusted_weighted", ""))
            )

    out["bal_adjusted_max_wt"] = f"{max(weighted_residuals):.2f}"
    out["bal_adjusted_n_above_threshold"] = str(
        sum(x > C.SMD_IMBALANCE_THRESHOLD for x in weighted_residuals)
    )
    return out


def render_balance_stratified_summary():
    d = _load_stratified()
    out = [
        "| Current-exposure contrast | Prior-wave exposure (A~t-1~) | "
        "Group _n_ | Never _n_ | Mean \\|adjusted SMD\\| before weighting | "
        "Mean \\|adjusted SMD\\| after weighting |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for contrast, contrast_label, _ in CONTRAST_LABELS:
        for stratum, stratum_label in STRAT_LABELS:
            nh, nl = _strat_cells(d, stratum, contrast)
            mu = _mean_abs(
                d[(stratum, contrast)], "smd_adjusted_unweighted"
            )
            mw = _mean_abs(d[(stratum, contrast)], "smd_adjusted_weighted")
            out.append(
                f"| {contrast_label} | {stratum_label} | {nh:,} | {nl:,} | "
                f"{mu:.2f} | {mw:.2f} |"
            )
    return "\n".join(out)


def render_balance_stratified_full(contrast):
    d = _load_stratified()
    cols = [
        ("lag_never", "Prior never"),
        ("lag_infrequent", "Prior infrequent"),
        ("lag_frequent", "Prior frequent"),
    ]
    header = "| Confounder | " + " | ".join(
        f"{lab} before | {lab} after" for _, lab in cols
    ) + " |"
    sep = "|---|" + "".join("---:|---:|" for _ in cols)
    out = [header, sep]
    for cov, label in BALANCE_LABELS.items():
        cells = [label]
        for stratum, _ in cols:
            r = d.get((stratum, contrast), {}).get(cov, {})
            for field in (
                "smd_adjusted_unweighted",
                "smd_adjusted_weighted",
            ):
                value = r.get(field, "")
                cells.append(f"{float(value):.3f}" if _is_number(value) else value)
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


BALANCE_LABELS = {
    "any_mobil_tv":  "Any mobility limitation",
    "any_adl_tv":    "Any ADL limitation",
    "any_iadl_tv":   "Any IADL limitation",
    "cog_tv":        "Cognition composite (z)",
    "cancre":        "Cancer (ever)",
    "lunge":         "Lung disease (ever)",
    "cvd_any_tv":    "Cardiovascular disease (any)",
    "smoke_now_tv":  "Current smoker",
    "cesd_w":        "Depressive symptoms (CES-D)",
    "poor_sight_tv": "Poor eyesight",
    "poor_hear_tv":  "Poor hearing",
}


def render_balance_md():
    """Render the covariate-balance CSV as a markdown table. Falls back to a
    short bootstrap note if the CSV is not yet generated."""
    csv_path = TABLES / "weight_balance.csv"
    if not csv_path.exists():
        return (
            "_Covariate balance table is generated by `code/05_msm_iptw.py`; "
            "rerun `code/run_all.py` to populate._"
        )
    rows = read_csv_dict(csv_path)
    if not rows:
        return "_(weight_balance.csv is empty)_"
    out = []
    out.append("| Time-varying confounder | SMD (unweighted) | SMD (IPTW-IPCW weighted) |")
    out.append("|---|---:|---:|")
    for r in rows:
        label = BALANCE_LABELS.get(r["covariate"], r["covariate"])
        smd_uw = r["smd_unweighted"]
        smd_w = r["smd_weighted"]
        out.append(f"| {label} | {smd_uw} | {smd_w} |")
    return "\n".join(out)


def render_table1_md():
    """Render output/tables/table1.csv as a markdown table for the manuscript.

    Source CSV columns: Variable, Level, Never (N=), Never %, Infrequent (N=),
    Infrequent %, Frequent (N=), Frequent %, Total (N=), Total %. We collapse
    each row into one of two display forms: a single-summary row (mean (SD),
    or % of total) or a multi-level row (one sub-row per level).
    """
    rows = read_csv_dict(TABLES / "table1.csv")
    out = []
    out.append("| Variable | Never | Infrequent | Frequent | Total |")
    out.append("|---|---:|---:|---:|---:|")

    def fmt(n, pct, is_mean_sd):
        n = (n or "").strip()
        pct = (pct or "").strip()
        if is_mean_sd:
            # "%" column already holds the formatted "mean (SD)" string; N is
            # the column denominator and is reported in the N row above.
            return pct
        if not pct:
            return n or ""
        if not n:
            return pct
        return f"{n} ({pct})"

    for r in rows:
        var = (r.get("Variable", "") or "").strip()
        lvl = (r.get("Level", "") or "").strip()
        label = f"{var}, {lvl}" if lvl else var
        is_mean_sd = "(mean" in var.lower()
        never = fmt(r.get("Never (N=)"), r.get("Never %"), is_mean_sd)
        infreq = fmt(r.get("Infrequent (N=)"), r.get("Infrequent %"), is_mean_sd)
        freq = fmt(r.get("Frequent (N=)"), r.get("Frequent %"), is_mean_sd)
        total = fmt(r.get("Total (N=)"), r.get("Total %"), is_mean_sd)
        out.append(f"| {label} | {never} | {infreq} | {freq} | {total} |")
    return "\n".join(out)


LADDER = [
    ("Baseline-fixed cloglog (panel)", "(i) Baseline-fixed", "Frozen at wave 2"),
    ("Unweighted discrete-time PH", "(ii) Time-varying, unadjusted", "Updated each wave"),
    (
        "Concurrent-confounder-adjusted PH",
        "(iii) Time-varying + concurrent adjustment",
        "Updated each wave",
    ),
    ("MSM IPTW+IPCW cloglog", "(iv) Marginal structural model", "Updated each wave"),
]


def render_ladder_table_md():
    """Render the four common-panel models (steps i-iv of the tutorial ladder)
    from table2.csv. Full-sample and continuous-time Cox estimates are reported
    in the supplement, not here, to keep the ladder on one comparable sample."""
    rows = read_csv_dict(TABLES / "table2.csv")
    by = {(r["Model"], r["Exposure"]): r for r in rows}
    out = ["| Step (exposure handling) | Contrast | HR (95% CI) | N (person-waves) | Deaths |",
           "|---|---|---:|---:|---:|"]
    for model, label, handling in LADDER:
        first = True
        for exposure in ("Frequent", "Infrequent"):
            r = by.get((model, exposure))
            if r is None:
                continue
            step = f"{label} ({handling.lower()})" if first else ""
            hr_ci = f"{r['HR']} ({r['CI_low']}–{r['CI_high']})"
            n = f"{int(float(r['N'])):,}"
            d = f"{int(float(r['Deaths'])):,}"
            out.append(f"| {step} | {exposure} vs never | {hr_ci} | {n} | {d} |")
            first = False
    return "\n".join(out)


def render_table2_md():
    """Render output/tables/table2.csv as a markdown table for the manuscript."""
    rows = read_csv_dict(TABLES / "table2.csv")
    out = []
    out.append("| Model | Exposure | HR (95% CI) | N | Deaths |")
    out.append("|---|---|---:|---:|---:|")
    for r in rows:
        model = r["Model"]
        exposure = r["Exposure"]
        hr_ci = f"{r['HR']} ({r['CI_low']}–{r['CI_high']})"
        n = f"{int(float(r['N'])):,}"
        d = f"{int(float(r['Deaths'])):,}"
        out.append(f"| {model} | {exposure} | {hr_ci} | {n} | {d} |")
    return "\n".join(out)


# Friendly labels for the baseline-missingness table (matches the variable names
# emitted by code/01_build_sample.py into output/tables/baseline_missingness.csv).
MISSINGNESS_LABELS = {
    "arts3":         ("Arts engagement (composite)",       "scactc, scactd"),
    "female":        ("Sex",                                "ragender"),
    "white":         ("Ethnicity (white)",                  "raracem"),
    "married":       ("Marital status",                     "r2mstat"),
    "edu4":          ("Education (4 categories)",           "raeduc_e"),
    "wealth5":       ("Wealth quintile",                    "h2atotb"),
    "working":       ("Employment",                         "r2lbrf_e"),
    "poor_sight":    ("Poor eyesight",                      "r2sight"),
    "poor_hearing":  ("Poor hearing",                       "r2hearing"),
    "cesd":          ("Depressive symptoms (CES-D)",        "r2cesd"),
    "r2psyche":      ("Psychiatric history",                "r2psyche"),
    "r2cancre":      ("Cancer (ever)",                      "r2cancre"),
    "r2lunge":       ("Lung disease (ever)",                "r2lunge"),
    "cvd_any":       ("Cardiovascular (any of HT/heart/stroke/diabetes)",
                                                            "r2hibpe, r2hearte, r2stroke, r2diabe"),
    "other_ltc":     ("Other long-term conditions",         "r2arthre, r2osteoe"),
    "smoke_now":     ("Current smoker",                     "r2smoken"),
    "alcfreq":       ("Alcohol frequency",                  "r2drinkd_e"),
    "any_mobil":     ("Mobility limitation (any)",          "r2mobilba"),
    "any_adl":       ("ADL limitation (any)",               "r2adlwaa"),
    "any_iadl":      ("IADL limitation (any)",              "r2iadlaa"),
    "cog_mean":      ("Cognition composite",                "r2imrc, r2dlrc, r2orient"),
}


def build_missingness_table():
    """Render the per-variable missingness markdown table from baseline_missingness.csv.
    Falls back to a placeholder note if the CSV is in its bootstrap state
    (the canonical pipeline has not been rerun since 01_build_sample.py was
    extended)."""
    csv_path = TABLES / "baseline_missingness.csv"
    if not csv_path.exists():
        return ("| Covariate | Source variable | % missing in wave-2 eligible pool |\n"
                "|---|---|---|\n"
                "| _(per-variable missingness CSV not yet generated; rerun `code/run_all.py`)_ | | |")

    rows = read_csv_dict(csv_path)
    # Detect bootstrap state: any pct_missing value that is not numeric
    bootstrap = any(not _is_number(r["pct_missing"]) for r in rows)

    raw_n_eligible = rows[0]["n_eligible"] if rows and rows[0]["n_eligible"] else ""
    n_eligible = (
        f"{int(float(raw_n_eligible)):,}"
        if _is_number(raw_n_eligible)
        else "TBD"
    )
    lines = ["| Covariate | Source variable | % missing in wave-2 eligible pool (N={n_elig}) |".format(
                 n_elig=n_eligible),
             "|---|---|---|"]
    for r in rows:
        var = r["variable"]
        label, source = MISSINGNESS_LABELS.get(var, (var, ""))
        pct = r["pct_missing"]
        if bootstrap:
            pct_display = "_pending_"
        else:
            pct_display = f"{float(pct):.2f}%"
        lines.append(f"| {label} | `{source}` | {pct_display} |")
    if bootstrap:
        lines.append("")
        lines.append(
            "_Note: per-variable percentages will populate on the next pipeline "
            "run. The CSV is currently in its bootstrap state because "
            "`01_build_sample.py` was updated to emit "
            "`baseline_missingness.csv` but has not yet been rerun._"
        )
    return "\n".join(lines)


def _is_number(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _count_words(span):
    """Word count of a text span, excluding markdown table rows, headers,
    horizontal rules, and table/figure captions."""
    words = []
    for ln in span.splitlines():
        s = ln.strip()
        if not s or s == "---" or s.startswith("|") or s.startswith("#"):
            continue
        if s.startswith("**Table") or s.startswith("**Figure"):
            continue
        words.extend(s.replace("*", "").split())
    return len(words)


def compute_word_counts(rendered):
    """Main-text count (Introduction through end of Discussion, per JECH:
    excludes title page, abstract, key messages, tables, references,
    declarations) and abstract count, from the fully rendered manuscript."""
    def span(start, end):
        i = rendered.index(start)
        j = rendered.index(end, i)
        return rendered[i:j]

    main = span("## Introduction", "## Declarations")
    abstract = span("## Abstract", "## Key messages").replace("## Abstract", "")
    return _count_words(main), _count_words(abstract)


def populate_text(template_path, values):
    """Render one template without writing it.

    Returns ``(text, n_subs, unresolved_placeholders, sentinel_keys)``.
    Keeping rendering pure lets the reporting gate compare the working files
    with a fresh build without first overwriting the evidence it is checking.
    """
    template = template_path.read_text(encoding="utf-8")
    result = template
    n_subs = 0
    sentinel_q = []

    for key, val in values.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            result = result.replace(placeholder, str(val))
            n_subs += 1
            if val in ("?", "TBD"):
                sentinel_q.append(key)

    # Detect unresolved placeholders that remain in the rendered output.
    # Allow only the literal {placeholder} pattern matching our naming convention.
    remaining = sorted(set(re.findall(r"\{([a-z_][a-z0-9_]*)\}", result)))
    return result, n_subs, remaining, sentinel_q


def _count_references(rendered):
    """Count numbered entries in the manuscript reference section."""
    start = rendered.index("## References")
    end = rendered.index("## Figure legends", start)
    block = rendered[start:end]
    return len(re.findall(r"^\d+\.\s", block, flags=re.MULTILINE))


def _count_display_items(rendered):
    """Count main-paper tables and figures from their caption anchors."""
    return len(re.findall(r"^\*\*(?:Table|Figure) \d+\.", rendered,
                          flags=re.MULTILINE))


def render_outputs():
    """Return freshly rendered reporting files and the values used to build them."""
    required_templates = [
        TEMPLATE,
        SUPPLEMENT_TEMPLATE,
        STROBE_TEMPLATE,
        COVER_TEMPLATE,
    ]
    missing_templates = [str(path) for path in required_templates if not path.exists()]
    if missing_templates:
        raise FileNotFoundError(f"Missing reporting templates: {missing_templates}")

    v = build_values()

    # Word counts are self-referential: render the manuscript once with all
    # other values, count, then substitute the two count tokens on the real pass.
    v["main_word_count"] = v["abstract_word_count"] = "0"
    trial, _, unresolved_trial, sentinel_trial = populate_text(TEMPLATE, v)
    if unresolved_trial or sentinel_trial:
        raise ValueError(
            "Cannot compute word counts with unresolved reporting values: "
            f"placeholders={unresolved_trial}, sentinels={sentinel_trial}"
        )
    main_wc, abs_wc = compute_word_counts(trial)
    v["main_word_count"] = f"{main_wc:,}"
    v["abstract_word_count"] = str(abs_wc)

    # Cover-letter package counts are derived from the same rendered manuscript,
    # not maintained as a second set of hand-typed values.
    main_trial, _, unresolved_main, sentinel_main = populate_text(TEMPLATE, v)
    if unresolved_main or sentinel_main:
        raise ValueError(
            "Cannot derive document metadata with unresolved reporting values: "
            f"placeholders={unresolved_main}, sentinels={sentinel_main}"
        )
    v["reference_count"] = str(_count_references(main_trial))
    v["display_count"] = str(_count_display_items(main_trial))

    specs = [
        ("manuscript", TEMPLATE, OUTPUT),
        ("supplement", SUPPLEMENT_TEMPLATE, SUPPLEMENT_OUTPUT),
        ("strobe", STROBE_TEMPLATE, STROBE_OUTPUT),
        ("cover", COVER_TEMPLATE, COVER_OUTPUT),
    ]
    rendered = {}
    failures = []
    for label, template_path, output_path in specs:
        text, n_subs, unresolved, sentinels = populate_text(template_path, v)
        rendered[output_path] = {
            "label": label,
            "text": text,
            "n_subs": n_subs,
        }
        if unresolved:
            failures.append(
                f"{output_path.name} unresolved placeholders: {unresolved}"
            )
        if sentinels:
            failures.append(
                f"{output_path.name} sentinel ('?'/'TBD') values: {sentinels}"
            )

    if failures:
        raise ValueError("; ".join(failures))
    return rendered, v


def _normalise_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def write_outputs(rendered):
    """Write a rendered report bundle to its canonical working paths."""
    for output_path, record in rendered.items():
        output_path.write_text(record["text"], encoding="utf-8")
        print(
            f"{record['label']}: wrote {output_path.relative_to(ROOT)} "
            f"({record['n_subs']} substitutions)"
        )


def check_outputs(rendered):
    """Fail if any working report differs from a fresh in-memory render."""
    stale = []
    for output_path, record in rendered.items():
        if not output_path.exists():
            stale.append(f"missing {output_path.relative_to(ROOT)}")
            continue
        actual = _normalise_newlines(output_path.read_text(encoding="utf-8"))
        expected = _normalise_newlines(record["text"])
        if actual != expected:
            stale.append(f"stale {output_path.relative_to(ROOT)}")
    if stale:
        raise ValueError("; ".join(stale))
    for output_path, record in rendered.items():
        print(
            f"{record['label']}: current {output_path.relative_to(ROOT)} "
            f"matches fresh render"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build or verify manuscript reporting files from output CSVs."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare working reports with a fresh render without writing them.",
    )
    args = parser.parse_args(argv)

    required = ["table1.csv", "table2.csv", "transitions.csv",
                "weight_diagnostics.csv", "table_pgs.csv",
                "weight_balance_stratified.csv"]
    missing = [f for f in required if not (TABLES / f).exists()]
    if missing:
        print(f"ERROR: Missing output files: {missing}", file=sys.stderr)
        print("Run the canonical pipeline first: python3 code/run_all.py",
              file=sys.stderr)
        sys.exit(1)

    try:
        rendered, values = render_outputs()
        if args.check:
            check_outputs(rendered)
        else:
            write_outputs(rendered)
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        sys.exit(2)

    counts = ", ".join(
        f"{record['label']} {record['n_subs']} subs"
        for record in rendered.values()
    )
    print(f"OK: {len(values)} unique values available; {counts}")


if __name__ == "__main__":
    main()
