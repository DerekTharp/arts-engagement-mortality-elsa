---
title: |
  Technical Supplement\
  \large Checking that the weights worked: a tutorial on balance diagnostics for marginal structural models, using arts engagement and mortality in the English Longitudinal Study of Ageing
author: |
  Derek Tharp, PhD\
  University of Southern Maine
---

## S1. Monotone Censoring Panel Design

The person-wave panel was constructed under strict monotone censoring. Each participant contributed observed intervals from wave 2 (2004-05) until the first wave at which they were either:

- not interviewed (iwstat != 1), or
- did not complete the self-completion arts engagement items (both scactc and scactd missing after valid interview; if either item is observed, the composite is built from the available item via the maximum-frequency rule used in the baseline construction)

whichever came first. All subsequent waves were permanently censored regardless of whether the participant later returned to the study.

Wave 10 could not start a new interval (no wave 11 endpoint), so the last standard interval was wave 9 to wave 10. As a single exception, wave-10 rows are retained as terminal death intervals when a wave-10 end-of-life record (HCAP2) places the death after the wave-10 interview reference year; wave-10 rows without an attributable death are dropped. Death timing used the midpoint between the last known alive wave and the first death-coded wave, matching the interval-censoring approach in the baseline sample construction. Cases with iwstat==9 (non-respondent, vital status unknown) are not treated as alive for the purposes of last-known-alive timing.

### Terminal-censoring sensitivity

A terminal censored interval contributes a no-death interval running to the next scheduled wave. At that next wave the harmonised interview status is interviewed (iwstat=1) or alive non-response (iwstat=4) for {sens_known_alive_pct}% of these intervals, confirming survival across the interval. For the remaining {sens_unknown_pct}%, the next-wave status is iwstat=9 (vital status unknown), so survival across the interval is assumed rather than observed. As a sensitivity check, we refitted the marginal structural model with those unknown-status terminal intervals censored at the last known-alive interview ({sens_cens_removed} intervals dropped, leaving {sens_cens_n}). The frequent-versus-never hazard ratio was {sens_cens_hr} ({sens_cens_lo} to {sens_cens_hi}), compared with {or_msm_frequent} ({ci_msm_frequent_lo} to {ci_msm_frequent_hi}) in the primary analysis.

---

## S2. Weight Model Specifications

### Treatment weights (IPTW)

Stabilised multinomial logistic regression weights for 3-category arts engagement (never/infrequent/frequent):

- **Numerator**: P(A~t~ | A~t-1~, age, age^2^, V) where V = full baseline covariates
- **Denominator**: P(A~t~ | A~t-1~, age, age^2^, V, L~t~) where L~t~ = time-varying confounders

Treatment weights were computed from wave 3 onward (wave 2 = baseline, no lagged exposure). Wave 2 treatment weight = 1.

### Censoring weights (IPCW)

Stabilised logistic regression weights for P(continued observation at wave t+1):

- **Numerator**: P(observed at t+1 | A~t~, age, age^2^, V)
- **Denominator**: P(observed at t+1 | A~t~, age, age^2^, V, L~t~)

The censoring model used concurrent (wave t) exposure and time-varying confounders to predict observation at wave t+1. The resulting weight was shifted forward one row within person, so that the weight applied at wave t+1 reflected P(observed at t+1 | history through t).

### Combined weights

Per-wave combined weight = w~trt~ x w~cens~. Cumulative weight = running product within person across waves. Truncated at 1st and 99th percentiles.

### Weight diagnostics

| Statistic | Value |
|---|---|
| Mean | {wt_mean} |
| SD | {wt_sd} |
| Min (1st percentile) | {wt_min} |
| Max (99th percentile) | {wt_max} |
| Median | {wt_p50} |
| 5th percentile | {wt_p5} |
| 95th percentile | {wt_p95} |
| Person-waves in outcome models | {n_panel_intervals} |
| Excluded for missing weights | {n_missing_weight} |
| Kish's effective sample size (ESS) | {ess} |
| ESS / N ratio | {ess_ratio} |

The mean stabilised weight near 1.0 and the high ESS/N ratio indicate limited weight variability on this panel. This is consistent with the small difference between the unweighted and IPTW-IPCW estimates in Table 1 of the main manuscript, but neither feature establishes covariate balance. The ESS approximates the equivalent unweighted sample size after accounting for the variability the weights introduce.

### Raw marginal balance audit

The table below reports unadjusted marginal standardised mean differences (SMDs) between current frequent and never engagement, before and after IPTW-IPCW weighting. Each mean difference is divided by the pooled standard deviation in the unweighted comparison sample. Thresholds used for description are |SMD| > {smd_imbalance_threshold} and |SMD| > {smd_substantial_threshold}.

{weight_balance_md}

These values are an audit, not the target diagnostic. The stabilised numerator retains associations between current exposure, prior exposure, age and baseline V. The marginal comparison mixes exposure histories and does not condition on those numerator terms, so either persistence or reduction of these SMDs is insufficient evidence about weight performance.

### Numerator-conditioned balance within prior-exposure strata

Because the stabilised numerator contains baseline covariates as well as prior exposure, stratifying on A~t-1~ alone does not fully condition the diagnostic. Following Jackson's regression approach, each time-varying confounder was regressed, separately within each prior-exposure stratum, on an indicator for the current-exposure contrast, current age, age squared and the full baseline covariate set V. The regression was fitted once without weights and once by weighted least squares using the cumulative IPTW-IPCW weight. The current-exposure coefficient was divided by the pooled standard deviation in the unweighted contrast-specific sample. This denominator was held fixed before and after weighting. Complete observations were identical for the two fits and are recorded as `n_adjusted` in the machine-readable output.

The diagnostic includes both non-reference exposure contrasts. Main-text Table 2 reports mean absolute adjusted SMDs and transition cell sizes; Figure 2 plots the signed per-covariate values. Tables S1 and S2 report the full values below.

**Table S1.** Regression-adjusted SMDs for current frequent versus never engagement, before and after weighting, by prior-wave exposure.

{balance_freq_adjusted_full_md}

**Table S2.** Regression-adjusted SMDs for current infrequent versus never engagement, before and after weighting, by prior-wave exposure.

{balance_infreq_adjusted_full_md}

In the prior-infrequent stratum, mean absolute adjusted SMD fell from {bal_freq_prior_infreq_adj_unw} to {bal_freq_prior_infreq_adj_wt} for frequent versus never and from {bal_infreq_prior_infreq_adj_unw} to {bal_infreq_prior_infreq_adj_wt} for infrequent versus never. The {bal_adjusted_n_above_threshold} post-weighting adjusted SMDs above {smd_imbalance_threshold} were confined to boundary comparisons containing only {n_freq_prior_never} current-frequent or {n_never_prior_freq} current-never person-waves. The largest residual adjusted SMD was {bal_adjusted_max_wt}. This pattern identifies limited overlap and imprecision in specific exposure histories; it does not identify a unique cause of the exposure change. The regression diagnostic is a model-based conditional-mean summary: it relies on the specified main effects and may extrapolate in sparse cells, while balanced means do not guarantee balance of joint distributions.

### Positivity

Predicted probabilities from the denominator treatment model were non-zero for all three engagement categories in every person-wave. The smallest was {positivity_min}. These low probabilities did not produce extreme weights: the untruncated cumulative weight reached {wt_untrunc_max} (mean {wt_mean}). The sparse boundary cells in the conditional balance diagnostic nevertheless show that non-extreme weights do not guarantee adequate empirical overlap for every history and contrast.

### Weight-truncation sensitivity

The primary models truncate the cumulative stabilised weight at the 1st and 99th percentiles. Because the weights are already tight, the frequent-versus-never estimate is insensitive to this choice: refitting the marginal structural model with untruncated weights and with 5th/95th-percentile truncation leaves the hazard ratio essentially unchanged (table below).

{wt_trunc_table_md}

---

## S3. Baseline Covariates

### Baseline characteristics of the worked example

Table S3 gives the baseline (wave 2) characteristics of the analytic sample by arts-engagement category. Participants who never engaged were older (mean age {age_mean_never} vs {age_mean_frequent} years), less educated, less wealthy, and had higher rates of mobility limitation ({mobil_pct_never}% vs {mobil_pct_frequent}%), ADL impairment ({adl_pct_never}% vs {adl_pct_frequent}%), and poor eyesight ({sight_pct_never}% vs {sight_pct_frequent}%) than frequent engagers; mortality over follow-up was {died_pct_never}% versus {died_pct_frequent}%. This baseline health gradient motivates examining exposure and health repeatedly rather than assuming that their relationship remains fixed.

**Table S3.** Baseline characteristics by arts engagement category at wave 2 (N = {n_baseline}). Counts (column percentages) for categorical variables; mean (SD) for continuous variables.

{table1_md}

### Covariates in the outcome models

All outcome models (baseline-fixed Cox, baseline-fixed cloglog, unweighted cloglog, MSM cloglog) adjusted for the following baseline (wave 2) covariates:

- Sex (female)
- Ethnicity (white British)
- Marital status (married/cohabiting)
- Education (4 categories: no qualification, age-16 qualification, age-18 qualification, degree)
- Wealth quintile (from total household wealth)
- Employment (working full-time or part-time)
- Poor eyesight (self-rated poor/very poor)
- Poor hearing (self-rated poor/very poor)
- Depressive symptoms (CES-D 0-8 scale)
- Psychiatric condition (ever diagnosed)
- Cancer (ever diagnosed)
- Lung disease (ever diagnosed)
- Cardiovascular disease (hypertension, heart problems, stroke, or diabetes)
- Other long-term conditions (arthritis or osteoporosis)
- Current smoker
- Alcohol frequency (days per week)
- Any mobility limitation (binary)
- Any ADL limitation (binary)
- Any IADL limitation (binary)
- Cognition composite (mean of standardised immediate recall, delayed recall, and orientation)

The supplementary time-varying Cox used a subset of these covariates (omitting alcohol frequency and other long-term conditions, which were not available as time-varying in the harmonised panel) plus time-varying versions of health confounders.

### Auxiliary model estimates (referenced from main-text Table 1)

Two further specifications are reported here rather than in the main-text ladder, which is kept on the single common panel. The full-sample baseline-fixed Cox model is the closest reconstruction of the original design and uses age as the timescale on the wave-2 cross-section (N={n_baseline}; {n_deaths_baseline} deaths). The continuous-time time-varying Cox model updates exposure and uses age as the timescale on the panel ({n_tvcox_intervals} intervals; {n_tvcox_deaths} deaths); it is not subject to the discrete-time models' weight-model exclusions and uses a slightly different covariate set, so it is reported for continuity with the prior literature rather than as a ladder step.

| Model | Frequent vs never HR (95% CI) | Infrequent vs never HR (95% CI) | N | Deaths |
|---|---:|---:|---:|---:|
| Full-sample baseline-fixed Cox | {hr_baseline_frequent} ({ci_baseline_frequent_lo}–{ci_baseline_frequent_hi}) | {hr_baseline_infrequent} ({ci_baseline_infrequent_lo}–{ci_baseline_infrequent_hi}) | {n_baseline} | {n_deaths_baseline} |
| Continuous-time time-varying Cox | {hr_tvcox_frequent} ({ci_tvcox_frequent_lo}–{ci_tvcox_frequent_hi}) | (see main Table 1 companion) | {n_tvcox_intervals} | {n_tvcox_deaths} |

**Figure S3** plots all specifications, including these two auxiliary models and the four common-panel ladder models, with the original published estimate (HR {published_hr_frequent}, {published_hr_frequent_lo}–{published_hr_frequent_hi}) as a reference.

![](output/figures/figure_s3_model_ladder.png){width=6.2in}

---

## S4. Arts Engagement Transition Matrix

Transitions between arts engagement categories across consecutive observed waves (monotone-censored panel, observed transitions only):

| From | To Never | To Infrequent | To Frequent |
|---|---|---|---|
| Never | {transition_never_stay}% | {transition_never_to_infreq}% | {transition_never_to_frequent}% |
| Infrequent | {transition_infreq_to_never}% | {transition_infreq_stay}% | {transition_infreq_to_frequent}% |
| Frequent | {transition_frequent_to_never}% | {transition_frequent_to_infreq}% | {transition_frequent_stay}% |

Between consecutive waves, {transition_pct_change_min}-{transition_pct_change_max}% of participants changed arts engagement category, confirming that the exposure is not fixed over the follow-up period.

---

## S5. Polygenic Score Sensitivity Analysis

### PGS variables

| PGS | Source GWAS | Variable |
|---|---|---|
| Educational attainment | Lee et al. 2018 (Nat Genet) | EA_3 |
| General cognitive function | 2018 summary statistics | GC_2018 |
| Social deprivation | Summary statistics | SEC_DEP |
| Height (negative control) | Summary statistics | Height |

All PGS were standardised to mean 0 and SD 1. The analysis was restricted to white British participants (N={n_pgs_sample}) and adjusted for {n_pgs_pcs} genetic principal components to address population stratification. Age and age squared were included in all cross-sectional models.

### Results

| Model | Infrequent HR | Frequent HR | N | Deaths |
|---|---|---|---|---|
| Cox (no PGS) | {hr_pgs_ref_infrequent} ({ci_pgs_ref_infrequent_lo}-{ci_pgs_ref_infrequent_hi}) | {hr_pgs_ref_frequent} ({ci_pgs_ref_frequent_lo}-{ci_pgs_ref_frequent_hi}) | {n_pgs_sample} | {n_pgs_deaths} |
| + PGS-education | {hr_pgs_ea_infrequent} ({ci_pgs_ea_infrequent_lo}-{ci_pgs_ea_infrequent_hi}) | {hr_pgs_ea_frequent} ({ci_pgs_ea_frequent_lo}-{ci_pgs_ea_frequent_hi}) | {n_pgs_sample} | {n_pgs_deaths} |
| + PGS-edu/cog/dep | {hr_pgs_multi_infrequent} ({ci_pgs_multi_infrequent_lo}-{ci_pgs_multi_infrequent_hi}) | {hr_pgs_multi_frequent} ({ci_pgs_multi_frequent_lo}-{ci_pgs_multi_frequent_hi}) | {n_pgs_sample} | {n_pgs_deaths} |

PGS-education association with mortality: HR {hr_pgs_ea_own} per SD (95% CI {ci_pgs_ea_own_lo}-{ci_pgs_ea_own_hi}).

PGS-education association with arts engagement: ordered logit OR {pgs_ea_or_arts} per SD (p{pgs_ea_p_arts}).

PGS-height negative control: arts engagement coefficient on genetic height = {pgs_height_coeff_frequent} SD (p={pgs_height_p_frequent}) for frequent vs never; {pgs_height_coeff_infrequent} SD (p={pgs_height_p_infrequent}) for infrequent vs never.

---

## S6. Participant Flow and Baseline Missingness (STROBE 13(c) and 14(b))

**Figure S1** shows participant flow from the wave 2 eligible pool through the complete-case baseline analytic sample (N={n_baseline}), the monotone-censored person-wave panel ({n_panel_pre_weight} intervals before weight-model exclusions), and the outcome-model analytic sample ({n_panel_intervals} intervals; {n_missing_weight} person-wave intervals dropped for missing weight-model inputs; {n_panel_deaths} deaths).

![](output/figures/figure_s1_flow.png){width=6.2in}

The wave 2 eligible pool comprised ELSA respondents aged {baseline_min_age} years or older interviewed at wave 2 (2004-05). Exclusions to reach the N={n_baseline} baseline analytic sample were dominated by missing self-completion arts-engagement data: the two items, scactc and scactd, were both missing for a substantial minority because completion of the self-completion booklet was conditional on the main interview. If either item was observed, the composite used the available value and the maximum-frequency rule. Per-variable missingness in the wave-2 eligible pool, before complete-case exclusion, was as follows:

{baseline_missingness_table}

Negative-coded missing-data sentinels (-1, -8, -9) are converted to system missing by the centralised reader in `code/pyelsa/io.py` before any binary or composite indicator is constructed. The same reader is used by the sample, panel, time-varying Cox, and MSM scripts. Per-variable missingness counts are written by `code/01_build_sample.py` to `output/tables/baseline_missingness.csv` and consumed by this supplement. Complete-case exclusion was retained for comparability with the published baseline-fixed estimate. Informative attrition across follow-up is handled separately, through the IPCW component of the marginal structural model rather than through imputation.

---

## S7. Death-Undercount Sensitivity Analysis

The public-data reconstruction observes {n_deaths_baseline} deaths in the wave-2 baseline analytic sample (N={n_baseline}). Fancourt and Steptoe's NHS-linked endpoint captured approximately {published_deaths} deaths in its sample. We do not treat {published_deaths} - {n_deaths_baseline} as the true count of unobserved deaths for this complete-case sample: the harmonised file's death capture is structurally censored after approximately 2013, and the offset is best read as an order-of-magnitude calibration of the potential undercount.

### Design

We bound the baseline-fixed Cox HR for frequent-vs-never arts engagement under a deterministic two-dimensional grid:

- **`n_extra`** in {{uc_n_extra_levels}}: number of unobserved deaths added back to the analytic sample;
- **`rr_alloc`** in {{uc_rr_levels}}: relative risk of being assigned an unobserved death given never-engagement vs frequent-engagement; infrequent engagers receive the geometric mean of the two endpoints. Values above 1 concentrate the unobserved deaths among never-engagers; values below 1 concentrate them among frequent-engagers (the direction that would attenuate the inverse association), so the grid is two-sided.

For each of the {uc_n_cells} cells the procedure samples `n_extra` person-IDs from the currently never-observed-dead cohort without replacement, with selection probability proportional to allocation weights respecting `rr_alloc` by arts-engagement stratum; assigns each sampled person a death year drawn uniformly from that person's unobserved at-risk interval (last-observed-year + 1 through the administrative horizon); and refits the baseline-fixed Cox. The procedure is repeated {uc_n_reps} times per cell with a fixed seed ({uc_seed}). The reported simulation median, 2.5th, and 97.5th percentiles are *simulation intervals under the scenario*, not confidence intervals.

The full-sample baseline-fixed Cox is the target HR because the public-data vs NHS-linked discrepancy is at the full-sample level. The panel-based IPTW-IPCW MSM is not pseudo-refit under the grid. Adding deaths back to the monotone-censored panel would require additional assumptions about within-interval timing and the reintroduction of person-time that the design cannot defensibly support. The IPCW component of the MSM is instead intended to address the informative-attrition channel of the undercount.

### Results

**Figure S2** shows the full grid as a heatmap of simulation-median HRs. Across the {uc_n_cells}-cell grid the simulation-median HR for frequent vs never ranged from {uc_grid_min_hr} to {uc_grid_max_hr}. At the Fancourt-gap calibration row (n_extra={uc_calibration_extra}) the simulation-median HR was {uc_fancourt_rr05_hr} when unobserved deaths were concentrated among frequent-engagers (rr_alloc=0.5), {uc_fancourt_rr1_hr} under random allocation (rr_alloc=1), and {uc_fancourt_rr3_hr} under a 3-fold concentration on never-engagers (rr_alloc=3). The median HR was at least 1.0 in {uc_n_median_ge_null} grid cells; the simulation interval crossed 1.0 in {uc_intervals_cross_null_cells}. The full {uc_n_cells}-cell table is written to `output/tables/death_undercount_sensitivity.csv`.

![](output/figures/figure_s2_undercount_grid.png){width=6.2in}

### Interpretation

The grid is two-sided. Values of rr_alloc above 1 concentrate unobserved deaths among never-engagers, while values below 1 concentrate them among frequent-engagers. The inverse direction held across all {uc_n_cells} cells, but its magnitude depended on the allocation scenario. Concentrating undercount among never-engagers moved the association farther from the null; concentrating it among frequent-engagers at the Fancourt-gap magnitude moved the median estimate to {uc_fancourt_rr05_hr}, with a simulation interval including the null. The scenario grid was prespecified, and Monte Carlo draws are reproducible under the fixed seed. No probability distribution was assigned across `n_extra` or `rr_alloc`; these results are therefore a deterministic scenario analysis with within-scenario simulation, not a probabilistic bias analysis.

---

## S8. Pipeline and Reproducibility

All analyses were conducted in Python (numpy, scipy, pandas, matplotlib; see `requirements.txt`). The survival, discrete-time proportional-hazards, marginal-structural-model, and ordered-logit estimators are implemented directly on numpy/scipy, so no proprietary statistical software is required. The full pipeline is reproduced by placing the UK Data Service downloads under the repository root (paths are configured in `code/pyelsa/config.py`) and running:

```
pip install -r requirements.txt
python3 code/run_all.py
```

Scripts execute in order: 01 (baseline sample + per-variable missingness CSV) -> 02 (Cox replication) -> 03 (panel construction with iwstat-based death-boundary rule) -> 04 (time-varying Cox) -> 05 (MSM with IPTW+IPCW; also fits the conventional concurrent-confounder-adjusted contrast and writes raw and numerator-conditioned balance diagnostics for both non-reference exposure contrasts) -> 06 (Table 1 + transitions) -> 08 (PGS sensitivity) -> 09 (death-undercount sensitivity grid). The DAG, the numerator-conditioned balance plot (main-text Figure 2), the STROBE participant-flow diagram, the undercount sensitivity heatmap, and the model-comparison forest plot (Figure S3) are then generated via `make_dag.py`, `make_balance_figure.py`, `make_flow_diagram.py`, `make_undercount_figure.py`, and `07_figures.py`.

The original Stata pipeline (`code/stata_reference/*.do`) is retained as a reference implementation. The production reports and success manifest are generated by Python. A `validate.py` harness compares the overlapping deterministic outputs when Stata reference outputs are available; the stochastic death-undercount sensitivity is assessed against its declared scenario and reproducibility checks rather than by requiring identical draws from different random-number generators.

Every table, figure, and project-estimated numeric result is written to `output/tables/` (CSV) and `output/figures/` (PNG). Each figure parses its values from those CSVs or the shared external-benchmark configuration. The reporting gate verifies exact sample and cross-output identities, recreates all reporting Markdown in memory, and rejects any numeric literal added to a reporting template unless it is classified and sourced in the reviewed numeric-literal ledger. A successful full run writes a cryptographic analysis manifest only after every declared output and report passes; `python3 code/run_all.py --submission` additionally rebuilds and verifies the Word files and staged figures.

Data: English Longitudinal Study of Ageing, UK Data Service studies 5050 (main) and 8773 (polygenic scores).
