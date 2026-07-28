*==============================================================================
* 05_msm_iptw.do
*
* Marginal structural model for arts engagement and mortality using
* stabilised inverse-probability-of-treatment weights (IPTW) and
* inverse-probability-of-censoring weights (IPCW).
*
* Input: data/fancourt_panel.dta (monotone-censoring panel from 03_build_panel.do)
*        data/fancourt_baseline.dta (wave 2 cross-section)
*
* Panel structure: all rows are observed (interviewed and arts items completed). No LOCF, no
* unobserved rows. censored_next == 1 flags dropout at the person's
* last observed wave. died_in_interval == 1 flags death in the interval
* starting at that wave. Most rows are waves 2-9; 03_build_panel.do also keeps
* a small number of wave-10 terminal death intervals when death timing is known.
*
* Treatment models: multinomial logit for 3-category arts engagement.
* Censoring models: logit for P(continuing) given concurrent covariates,
*   shifted forward one row so weight at t = P(observed at t | t-1).
* Outcome models: discrete-time proportional hazards (cloglog link)
*   with combined IPTW x IPCW weights and log(interval_years) offset.
*
* Output: $out/tables/table2.csv, $out/tables/weight_diagnostics.csv
*==============================================================================

capture log close
log using "$out/logs/05_msm_iptw.log", replace text

use "$data/fancourt_panel.dta", clear

*------------------------------------------------------------------------------
* 1. Merge time-invariant baseline covariates (full set)
*------------------------------------------------------------------------------
merge m:1 idauniq using "$data/fancourt_baseline.dta", ///
    keepusing(female white married edu4 wealth5 working poor_sight poor_hearing ///
              cesd r2psyche r2cancre r2lunge cvd_any other_ltc ///
              smoke_now alcfreq any_mobil any_adl any_iadl cog_mean ///
              r2agey) ///
    keep(master match) nogen

sort idauniq wave

*------------------------------------------------------------------------------
* 2. Time-varying confounder construction
*------------------------------------------------------------------------------
gen cvd_any_tv = (hibpe == 1 | hearte == 1 | stroke == 1 | diabe == 1)
replace cvd_any_tv = . if missing(hibpe) & missing(hearte) & missing(stroke) & missing(diabe)

gen smoke_now_tv = (smoken == 1) if !missing(smoken)
gen any_mobil_tv = (mobilba == 1) if !missing(mobilba)
gen any_adl_tv   = (adlwaa  == 1) if !missing(adlwaa)
gen any_iadl_tv  = (iadlaa  == 1) if !missing(iadlaa)

gen poor_sight_tv = inrange(sight, 4, 6) if !missing(sight)
gen poor_hear_tv  = inrange(hearing, 4, 6) if !missing(hearing)

foreach v in imrc dlrc orient {
    capture confirm numeric variable `v'
    if !_rc quietly replace `v' = . if `v' < 0
}
egen zimrc_tv   = std(imrc)
egen zdlrc_tv   = std(dlrc)
egen zorient_tv = std(orient)
egen cog_tv     = rowmean(zimrc_tv zdlrc_tv zorient_tv)

*------------------------------------------------------------------------------
* 3. Lagged exposure and lagged time-varying covariates
*
* Panel is monotone-censored: every row is an observed interview. The lag
* is therefore the actual prior observed value, not an LOCF imputation.
*------------------------------------------------------------------------------
sort idauniq wave
by idauniq: gen arts3_lag = arts3[_n-1]

* Lagged TV confounders for the IPCW denominator model
foreach v in any_mobil_tv any_adl_tv any_iadl_tv cog_tv ///
             cancre lunge cvd_any_tv smoke_now_tv cesd_w ///
             poor_sight_tv poor_hear_tv {
    by idauniq: gen `v'_lag = `v'[_n-1]
}

*------------------------------------------------------------------------------
* 4. Treatment weight models (IPTW) -- multinomial logit, 3 exposure categories
*
* Numerator: P(arts3 | arts3_lag, age, FULL baseline covariates)
* Denominator: P(arts3 | arts3_lag, age, FULL baseline covariates + TV confounders)
*
* Stabilised weights per Cole & Hernan (2008). Estimation begins at wave 3
* (first wave with a lagged exposure).
*------------------------------------------------------------------------------

gen in_trt_sample = (wave >= 3) & !missing(arts3) & !missing(arts3_lag) & !missing(agey)

display _newline "=== IPTW numerator model: arts3 on arts3_lag + age + FULL baseline ==="
mlogit arts3 i.arts3_lag c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    if in_trt_sample, nolog

predict nump_0 nump_1 nump_2 if e(sample), pr

gen p_num = .
replace p_num = nump_0 if arts3 == 0
replace p_num = nump_1 if arts3 == 1
replace p_num = nump_2 if arts3 == 2

display _newline "=== IPTW denominator model: arts3 on arts3_lag + age + FULL baseline + TV ==="
mlogit arts3 i.arts3_lag c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    i.any_mobil_tv i.any_adl_tv i.any_iadl_tv cog_tv ///
    i.cancre i.lunge i.cvd_any_tv i.smoke_now_tv cesd_w ///
    i.poor_sight_tv i.poor_hear_tv ///
    if in_trt_sample, nolog

predict denp_0 denp_1 denp_2 if e(sample), pr

gen p_den = .
replace p_den = denp_0 if arts3 == 0
replace p_den = denp_1 if arts3 == 1
replace p_den = denp_2 if arts3 == 2

* Per-wave treatment weight
gen w_trt = p_num / p_den if in_trt_sample

* Wave 2 has no lagged exposure; treatment weight = 1
replace w_trt = 1 if wave == 2

display _newline "Per-wave treatment weight distribution (before cumulation):"
summarize w_trt, detail

*------------------------------------------------------------------------------
* 5. Censoring weight models (IPCW) -- logit for P(continuing to next wave)
*
* censored_next == 1 at a person's last observed wave if they drop out.
* We model P(censored_next == 0 | covariates) = P(continuing past this wave).
*
* The model at wave t uses CONCURRENT wave-t exposure and health to predict
* observation at wave t+1. The resulting weight is then SHIFTED FORWARD one
* row: the prediction at wave t becomes the censoring weight applied at
* wave t+1. After shifting, wave t+1's weight reflects P(observed at t+1 |
* history through t), which is the standard MSM convention (Hernan & Robins).
*
* Using concurrent (not lagged) predictors avoids a double-lag: if we used
* lagged predictors at wave t to predict censoring at t+1, then shifted
* forward, wave t+1's weight would condition on wave t-1 data — missing
* the most proximal health information.
*
* Numerator: P(continuing | arts3, age, FULL baseline covariates)
* Denominator: P(continuing | arts3, age, FULL baseline + concurrent TV)
*------------------------------------------------------------------------------

gen not_censored = 1 - censored_next

gen in_cens_sample = !missing(arts3) & !missing(agey) & !missing(not_censored)

display _newline "=== IPCW numerator model: P(continuing) on arts3 + age + FULL baseline ==="
logit not_censored i.arts3 c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    if in_cens_sample, nolog

predict pc_num if e(sample), pr

display _newline "=== IPCW denominator model: P(continuing) on arts3 + age + FULL baseline + concurrent TV ==="
logit not_censored i.arts3 c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    i.any_mobil_tv i.any_adl_tv i.any_iadl_tv cog_tv ///
    i.cancre i.lunge i.cvd_any_tv i.smoke_now_tv cesd_w ///
    i.poor_sight_tv i.poor_hear_tv ///
    if in_cens_sample, nolog

predict pc_den if e(sample), pr

* Raw per-wave censoring weight (predicts continuation PAST this wave)
gen w_cens_raw = pc_num / pc_den if in_cens_sample

* Shift forward one row: prediction at wave t becomes weight at wave t+1
sort idauniq wave
by idauniq: gen w_cens = w_cens_raw[_n-1] if _n > 1
replace w_cens = 1 if wave == 2

display _newline "Per-wave censoring weight distribution (shifted):"
summarize w_cens, detail

*------------------------------------------------------------------------------
* 6. Combined weights (IPTW x IPCW), cumulation, truncation, diagnostics
*------------------------------------------------------------------------------

* Per-wave combined weight
gen w_combined = w_trt * w_cens

* Cumulative stabilised weight (product over waves within each person)
sort idauniq wave
by idauniq: gen cum_weight = w_combined if _n == 1
by idauniq: replace cum_weight = cum_weight[_n-1] * w_combined if _n > 1

display _newline "Cumulative combined weight distribution (before truncation):"
summarize cum_weight, detail

* Keep an untruncated copy and a 5th/95th-percentile-truncated copy for the
* weight-truncation sensitivity analysis (Suppl. S3). Both are derived from the
* raw cumulative weight before the primary 1st/99th truncation below.
gen cum_weight_raw = cum_weight
_pctile cum_weight_raw, percentiles(5 95)
gen cum_weight_t595 = cum_weight_raw
replace cum_weight_t595 = r(r1) if cum_weight_t595 < r(r1) & !missing(cum_weight_t595)
replace cum_weight_t595 = r(r2) if cum_weight_t595 > r(r2) & !missing(cum_weight_t595)

* Truncate at 1st/99th percentiles
_pctile cum_weight, percentiles(1 99)
local p1  = r(r1)
local p99 = r(r2)
display "Truncation thresholds: p1 = `p1', p99 = `p99'"
replace cum_weight = `p1'  if cum_weight < `p1'  & !missing(cum_weight)
replace cum_weight = `p99' if cum_weight > `p99' & !missing(cum_weight)

display _newline "Cumulative combined weight distribution (after truncation):"
summarize cum_weight, detail

* Log rows with missing combined weight (will be dropped, NOT set to 1)
count if missing(cum_weight)
local n_miss_wt = r(N)
display _newline "Rows with missing combined weight (will be excluded from outcome): `n_miss_wt'"
if `n_miss_wt' > 0 {
    tab wave if missing(cum_weight)
}

*------------------------------------------------------------------------------
* 7. Outcome models
*
* All pooled logistic models include age, FULL baseline confounders, and
* grouped interval indicators for the discrete-time baseline hazard.
* Sparse late deaths make fully saturated wave dummies unstable, so waves
* 6-8 and 9-10 are pooled. log(interval_years) enters as an offset for
* unequal wave spacing.
*
* Rows with missing combined weight or invalid intervals are excluded.
*------------------------------------------------------------------------------

gen ln_interval = ln(interval_years)

gen hazard_period = .
replace hazard_period = 2 if wave == 2
replace hazard_period = 3 if wave == 3
replace hazard_period = 4 if wave == 4
replace hazard_period = 5 if wave == 5
replace hazard_period = 68 if inlist(wave, 6, 7, 8)
replace hazard_period = 910 if inlist(wave, 9, 10)
label define hazper 2 "Wave 2" 3 "Wave 3" 4 "Wave 4" 5 "Wave 5" ///
    68 "Waves 6-8" 910 "Waves 9-10"
label values hazard_period hazper
tab hazard_period died_in_interval, missing

* Flag rows eligible for outcome models
gen in_outcome = !missing(cum_weight) & !missing(ln_interval) & interval_years > 0

* Log exclusions
count if missing(cum_weight) & !missing(ln_interval)
display "  Excluded for missing weight: " r(N)
count if missing(ln_interval) | interval_years <= 0
display "  Excluded for missing/invalid interval: " r(N)

display _newline "Outcome model sample:"
count if in_outcome
display "  Person-waves entering outcome models: " r(N)
count if in_outcome & died_in_interval == 1
display "  Deaths in outcome sample: " r(N)

* --- (a) Fancourt-style baseline-fixed Cox (display-only reference) ---
* This block fits the full-sample baseline Cox as a screen-display sanity check.
* The model is re-estimated quietly in section 8 below for CSV output, so we
* intentionally do not store coefficients or sample-size locals here.
display _newline "=== (a) Fancourt-style baseline-fixed Cox (reference) ==="
preserve
use "$data/fancourt_baseline.dta", clear
gen entry_age = r2agey
gen exit_age  = r2agey + fu_years
stset exit_age, failure(died==1) enter(time entry_age) origin(time 0)
stcox ib0.arts3 ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean, nolog
restore

* --- (a2) Baseline-fixed cloglog on the SAME monotone panel ---
* Arts engagement fixed at the wave 2 baseline value, but estimated on the
* same person-wave intervals as models (b) and (c). This is the cleanest
* comparator for assessing how much updating exposure changes the estimate,
* because it shares sample, follow-up, and covariate specification.
* Get baseline arts3 value — merge under a temp name to avoid clash with
* the panel's time-varying arts3
preserve
use idauniq arts3 using "$data/fancourt_baseline.dta", clear
rename arts3 arts3_baseline
tempfile baseline_arts
save `baseline_arts'
restore

merge m:1 idauniq using `baseline_arts', keep(master match) nogen
label variable arts3_baseline "Arts engagement fixed at wave 2 baseline"

display _newline "=== (a2) Baseline-fixed cloglog (same panel) ==="
cloglog died_in_interval ib0.arts3_baseline c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    i.hazard_period ///
    if in_outcome, offset(ln_interval) nolog vce(cluster idauniq)

foreach lev in 1 2 {
    local hr_bfcl_`lev'    = string(exp(_b[`lev'.arts3_baseline]), "%5.2f")
    local ci_bfcl_lo_`lev' = string(exp(_b[`lev'.arts3_baseline] - 1.96 * _se[`lev'.arts3_baseline]), "%5.2f")
    local ci_bfcl_hi_`lev' = string(exp(_b[`lev'.arts3_baseline] + 1.96 * _se[`lev'.arts3_baseline]), "%5.2f")
}
local n_bfcl = e(N)
quietly count if died_in_interval == 1 & e(sample)
local d_bfcl = r(N)

* --- (b) Unweighted discrete-time PH with time-varying exposure (cloglog) ---
* cloglog is the exact discrete-time analogue of the continuous-time Cox model,
* allowing direct comparison of HRs across all specifications.
display _newline "=== (b) Unweighted discrete-time PH (cloglog, time-varying exposure) ==="
cloglog died_in_interval ib0.arts3 c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    i.hazard_period ///
    if in_outcome, offset(ln_interval) nolog vce(cluster idauniq)

foreach lev in 1 2 {
    local or_uwt_`lev'    = string(exp(_b[`lev'.arts3]), "%5.2f")
    local ci_uwt_lo_`lev' = string(exp(_b[`lev'.arts3] - 1.96 * _se[`lev'.arts3]), "%5.2f")
    local ci_uwt_hi_`lev' = string(exp(_b[`lev'.arts3] + 1.96 * _se[`lev'.arts3]), "%5.2f")
}
local n_uwt = e(N)
quietly count if died_in_interval == 1 & e(sample)
local d_uwt = r(N)

* --- (b2) Concurrent-confounder-adjusted discrete-time PH (cloglog) ---
* Same cohort, same time-varying exposure, but conditioning DIRECTLY on
* concurrent time-varying L_t in the outcome model rather than handling
* L_t through inverse-probability weights. Under the DAG, this may block an
* earlier-exposure pathway or induce collider bias. It is reported as a
* conventional comparison on the same panel.
display _newline "=== (b2) Concurrent-confounder-adjusted PH (concurrent L_t in outcome model, unweighted) ==="
cloglog died_in_interval ib0.arts3 c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    i.any_mobil_tv i.any_adl_tv i.any_iadl_tv cog_tv ///
    i.cancre i.lunge i.cvd_any_tv i.smoke_now_tv cesd_w ///
    i.poor_sight_tv i.poor_hear_tv ///
    i.hazard_period ///
    if in_outcome, offset(ln_interval) nolog vce(cluster idauniq)

foreach lev in 1 2 {
    local or_naive_`lev'    = string(exp(_b[`lev'.arts3]), "%5.2f")
    local ci_naive_lo_`lev' = string(exp(_b[`lev'.arts3] - 1.96 * _se[`lev'.arts3]), "%5.2f")
    local ci_naive_hi_`lev' = string(exp(_b[`lev'.arts3] + 1.96 * _se[`lev'.arts3]), "%5.2f")
}
local n_naive = e(N)
quietly count if died_in_interval == 1 & e(sample)
local d_naive = r(N)

* --- (c) MSM: stabilised IPTW + IPCW discrete-time PH (cloglog) ---
display _newline "=== (c) MSM: IPTW + IPCW discrete-time PH (cloglog) ==="
cloglog died_in_interval ib0.arts3 c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    i.hazard_period ///
    if in_outcome [pweight=cum_weight], offset(ln_interval) nolog vce(cluster idauniq)

foreach lev in 1 2 {
    local or_msm_`lev'    = string(exp(_b[`lev'.arts3]), "%5.2f")
    local ci_msm_lo_`lev' = string(exp(_b[`lev'.arts3] - 1.96 * _se[`lev'.arts3]), "%5.2f")
    local ci_msm_hi_`lev' = string(exp(_b[`lev'.arts3] + 1.96 * _se[`lev'.arts3]), "%5.2f")
}
local n_msm = e(N)
quietly count if died_in_interval == 1 & e(sample)
local d_msm = r(N)

* --- (c-sensitivity) Terminal-censoring robustness ---
* A terminal censored interval contributes a no-death interval to the next
* scheduled wave. For some of these the next-wave harmonised status is iwstat==9
* (vital status unknown), so survival across that interval is assumed rather
* than observed. Here we instead censor those persons at their last
* known-alive interview (drop the interval) and refit the MSM to assess
* sensitivity to that coding choice.
display _newline "=== (c-sensitivity) MSM, unknown-status terminal intervals censored at last interview ==="
count if in_outcome & censored_next == 1 & next_iwstat == 9
local n_cens_unknown = r(N)
gen in_outcome_cens = in_outcome & !(censored_next == 1 & next_iwstat == 9)
cloglog died_in_interval ib0.arts3 c.agey##c.agey ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    i.hazard_period ///
    if in_outcome_cens [pweight=cum_weight], offset(ln_interval) nolog vce(cluster idauniq)
local hr_sens_frequent    = string(exp(_b[2.arts3]), "%5.2f")
local ci_sens_frequent_lo = string(exp(_b[2.arts3] - 1.96 * _se[2.arts3]), "%5.2f")
local ci_sens_frequent_hi = string(exp(_b[2.arts3] + 1.96 * _se[2.arts3]), "%5.2f")
local n_sens = e(N)

* --- (c-sensitivity 2) Weight-truncation robustness ---
* Refit the MSM with untruncated weights and with 5th/95th-percentile
* truncation to assess sensitivity to the 1st/99th choice.
quietly summarize cum_weight if in_outcome
local wtmax_t199 = string(r(max), "%6.2f")
foreach wv in raw t595 {
    display _newline "=== (c-sensitivity 2) MSM with `wv' weights ==="
    cloglog died_in_interval ib0.arts3 c.agey##c.agey ///
        i.female i.white i.married i.edu4 i.wealth5 i.working ///
        i.poor_sight i.poor_hearing cesd i.r2psyche ///
        i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
        i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
        i.hazard_period ///
        if in_outcome [pweight=cum_weight_`wv'], offset(ln_interval) nolog vce(cluster idauniq)
    local hr_wt_`wv'    = string(exp(_b[2.arts3]), "%5.2f")
    local ci_wt_`wv'_lo = string(exp(_b[2.arts3] - 1.96 * _se[2.arts3]), "%5.2f")
    local ci_wt_`wv'_hi = string(exp(_b[2.arts3] + 1.96 * _se[2.arts3]), "%5.2f")
    quietly summarize cum_weight_`wv' if in_outcome
    local wtmax_`wv' = string(r(max), "%6.2f")
}

* --- Positivity diagnostic ---
* Minimum predicted probability of each exposure category from the denominator
* treatment model. These values describe empirical overlap; they do not by
* themselves establish the positivity assumption.
foreach k in 0 1 2 {
    quietly summarize denp_`k' if in_trt_sample, detail
    local minp_`k' = string(r(min), "%6.4f")
}

*------------------------------------------------------------------------------
* 8. Write Table 2 CSV and weight diagnostics CSV
*
* Table 2 reports four models. All model estimation occurs in this script
* (single source of truth per project standards).
*------------------------------------------------------------------------------

* --- Table 2 ---
tempname fh
file open `fh' using "$out/tables/table2.csv", write replace
file write `fh' "Model,Exposure,HR,CI_low,CI_high,N,Deaths,Metric" _n

* (a) Baseline-fixed Cox (re-estimate for CSV output)
preserve
use "$data/fancourt_baseline.dta", clear
gen entry_age = r2agey
gen exit_age  = r2agey + fu_years
stset exit_age, failure(died==1) enter(time entry_age) origin(time 0)
* Age is the timescale (implicit adjustment via stset); not a covariate
quietly stcox ib0.arts3 ///
    i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean, nolog
local n_base = e(N)
local d_base = e(N_fail)
foreach lev in 1 2 {
    local hr    = string(exp(_b[`lev'.arts3]), "%5.2f")
    local ci_lo = string(exp(_b[`lev'.arts3] - 1.96 * _se[`lev'.arts3]), "%5.2f")
    local ci_hi = string(exp(_b[`lev'.arts3] + 1.96 * _se[`lev'.arts3]), "%5.2f")
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "Baseline-fixed Cox,`explab',`hr',`ci_lo',`ci_hi',`n_base',`d_base',HR" _n
}
restore

* (b) Time-varying Cox (re-estimate from panel with full TV covariates)
preserve
use "$data/fancourt_panel.dta", clear
keep if observed == 1
merge m:1 idauniq using "$data/fancourt_baseline.dta", ///
    keepusing(female white married edu4 wealth5 working poor_sight poor_hearing r2psyche) ///
    keep(master match) nogen
sort idauniq wave

* Build TV covariates matching 04_time_varying_cox.do
gen cvd_any = (hibpe == 1 | hearte == 1 | stroke == 1 | diabe == 1)
replace cvd_any = . if missing(hibpe) & missing(hearte) & missing(stroke) & missing(diabe)
gen smoke_now = (smoken == 1) if !missing(smoken)
gen any_mobil = (mobilba == 1) if !missing(mobilba)
gen any_adl   = (adlwaa == 1) if !missing(adlwaa)
gen any_iadl  = (iadlaa == 1) if !missing(iadlaa)
gen poor_sight_w = inrange(sight, 4, 6) if !missing(sight)
gen poor_hear_w  = inrange(hearing, 4, 6) if !missing(hearing)
foreach v in imrc dlrc orient {
    capture confirm numeric variable `v'
    if !_rc quietly replace `v' = . if `v' < 0
}
egen zimrc_w    = std(imrc)
egen zdlrc_w    = std(dlrc)
egen zorient_w  = std(orient)
egen cog_mean_w = rowmean(zimrc_w zdlrc_w zorient_w)

gen tv_entry_age = r2agey + (start_year - baseline_year)
gen tv_exit_age  = r2agey + (stop_year  - baseline_year)
drop if missing(tv_entry_age) | missing(tv_exit_age) | tv_exit_age <= tv_entry_age

stset tv_exit_age, id(idauniq) failure(died_in_interval==1) ///
    enter(time tv_entry_age) origin(time 0)

quietly stcox ib0.arts3 i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight_w i.poor_hear_w cesd_w i.r2psyche ///
    i.cancre i.lunge i.cvd_any ///
    i.smoke_now i.any_mobil i.any_adl i.any_iadl cog_mean_w, ///
    nolog vce(cluster idauniq)
local n_tv = e(N)
local d_tv = e(N_fail)
foreach lev in 1 2 {
    local hr    = string(exp(_b[`lev'.arts3]), "%5.2f")
    local ci_lo = string(exp(_b[`lev'.arts3] - 1.96 * _se[`lev'.arts3]), "%5.2f")
    local ci_hi = string(exp(_b[`lev'.arts3] + 1.96 * _se[`lev'.arts3]), "%5.2f")
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "Time-varying Cox,`explab',`hr',`ci_lo',`ci_hi',`n_tv',`d_tv',HR" _n
}
restore

* (b) Baseline-fixed cloglog (same panel)
foreach lev in 1 2 {
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "Baseline-fixed cloglog (panel),`explab',`hr_bfcl_`lev'',`ci_bfcl_lo_`lev'',`ci_bfcl_hi_`lev'',`n_bfcl',`d_bfcl',HR" _n
}

* (c) Unweighted discrete-time PH (time-varying exposure)
foreach lev in 1 2 {
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "Unweighted discrete-time PH,`explab',`or_uwt_`lev'',`ci_uwt_lo_`lev'',`ci_uwt_hi_`lev'',`n_uwt',`d_uwt',HR" _n
}

* (c2) Concurrent-confounder-adjusted discrete-time PH
foreach lev in 1 2 {
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "Concurrent-confounder-adjusted PH,`explab',`or_naive_`lev'',`ci_naive_lo_`lev'',`ci_naive_hi_`lev'',`n_naive',`d_naive',HR" _n
}

* (d) MSM IPTW + IPCW
foreach lev in 1 2 {
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "MSM IPTW+IPCW cloglog,`explab',`or_msm_`lev'',`ci_msm_lo_`lev'',`ci_msm_hi_`lev'',`n_msm',`d_msm',HR" _n
}

file close `fh'
display _newline "Table 2 written to $out/tables/table2.csv"

* --- Terminal-censoring sensitivity CSV ---
tempname fhs
file open `fhs' using "$out/tables/sensitivity_censoring.csv", write replace
file write `fhs' "spec,HR,CI_low,CI_high,N,n_removed" _n
file write `fhs' "MSM primary (full outcome sample),`or_msm_2',`ci_msm_lo_2',`ci_msm_hi_2',`n_msm',0" _n
file write `fhs' "MSM unknown-status terminal intervals censored at last interview,`hr_sens_frequent',`ci_sens_frequent_lo',`ci_sens_frequent_hi',`n_sens',`n_cens_unknown'" _n
file close `fhs'
display "Censoring sensitivity written to $out/tables/sensitivity_censoring.csv"

* --- Weight-truncation sensitivity CSV ---
tempname fhw2
file open `fhw2' using "$out/tables/sensitivity_weights.csv", write replace
file write `fhw2' "truncation,HR,CI_low,CI_high,max_weight" _n
file write `fhw2' "Untruncated,`hr_wt_raw',`ci_wt_raw_lo',`ci_wt_raw_hi',`wtmax_raw'" _n
file write `fhw2' "1st/99th percentile (primary),`or_msm_2',`ci_msm_lo_2',`ci_msm_hi_2',`wtmax_t199'" _n
file write `fhw2' "5th/95th percentile,`hr_wt_t595',`ci_wt_t595_lo',`ci_wt_t595_hi',`wtmax_t595'" _n
file close `fhw2'
display "Weight-truncation sensitivity written to $out/tables/sensitivity_weights.csv"

* --- Positivity diagnostic CSV ---
tempname fhp
file open `fhp' using "$out/tables/positivity.csv", write replace
file write `fhp' "exposure,min_pred_prob" _n
file write `fhp' "Never,`minp_0'" _n
file write `fhp' "Infrequent,`minp_1'" _n
file write `fhp' "Frequent,`minp_2'" _n
file close `fhp'
display "Positivity diagnostic written to $out/tables/positivity.csv"

* --- Weight diagnostics CSV ---
summarize cum_weight, detail
tempname fhw
file open `fhw' using "$out/tables/weight_diagnostics.csv", write replace
file write `fhw' "stat,value" _n
file write `fhw' "mean," (string(r(mean), "%5.3f")) _n
file write `fhw' "sd," (string(r(sd), "%5.3f")) _n
file write `fhw' "min," (string(r(min), "%5.3f")) _n
file write `fhw' "max," (string(r(max), "%5.3f")) _n
file write `fhw' "p1," (string(r(p1), "%5.3f")) _n
file write `fhw' "p5," (string(r(p5), "%5.3f")) _n
file write `fhw' "p25," (string(r(p25), "%5.3f")) _n
file write `fhw' "p50," (string(r(p50), "%5.3f")) _n
file write `fhw' "p75," (string(r(p75), "%5.3f")) _n
file write `fhw' "p95," (string(r(p95), "%5.3f")) _n
file write `fhw' "p99," (string(r(p99), "%5.3f")) _n
file write `fhw' "n_outcome," (string(`n_msm', "%9.0f")) _n
file write `fhw' "n_missing_weight," (string(`n_miss_wt', "%9.0f")) _n

* Kish's effective sample size: ESS = (sum(w))^2 / sum(w^2)
quietly summarize cum_weight if in_outcome, meanonly
local sum_w = r(sum)
quietly gen _wsq = cum_weight * cum_weight if in_outcome
quietly summarize _wsq if in_outcome, meanonly
local sum_w2 = r(sum)
local ess = `sum_w' * `sum_w' / `sum_w2'
local ess_ratio = `ess' / `n_msm'
drop _wsq
file write `fhw' "ess," (string(`ess', "%9.0f")) _n
file write `fhw' "ess_ratio," (string(`ess_ratio', "%5.3f")) _n
file write `fhw' "weight_type,IPTW x IPCW (stabilised truncated 1/99)" _n
file close `fhw'
display "Weight diagnostics written to $out/tables/weight_diagnostics.csv"

* --- Covariate balance CSV: standardised mean differences for time-varying
*     confounders, comparing the unweighted vs IPTW-IPCW-weighted samples.
*     SMD is the difference in means (frequent minus never) divided by the
*     pooled SD of the unweighted sample. Conventional thresholds: |SMD| > 0.1
*     suggests imbalance.
display _newline "=== Covariate balance (unweighted vs weighted) ==="
tempname fhb
file open `fhb' using "$out/tables/weight_balance.csv", write replace
file write `fhb' "covariate,smd_unweighted,smd_weighted,n_used" _n

* Levels: 0=never, 1=infrequent, 2=frequent. SMD = frequent vs never.
foreach v of varlist any_mobil_tv any_adl_tv any_iadl_tv cog_tv ///
    cancre lunge cvd_any_tv smoke_now_tv cesd_w ///
    poor_sight_tv poor_hear_tv {

    capture confirm numeric variable `v'
    if _rc continue

    * Unweighted means by exposure (frequent and never)
    quietly summarize `v' if in_outcome & arts3 == 2
    local m_freq_uw = r(mean)
    local sd_freq_uw = r(sd)
    local n_freq_uw = r(N)

    quietly summarize `v' if in_outcome & arts3 == 0
    local m_nev_uw = r(mean)
    local sd_nev_uw = r(sd)
    local n_nev_uw = r(N)

    local pooled_sd = sqrt(((`sd_freq_uw')^2 + (`sd_nev_uw')^2) / 2)
    local smd_uw = .
    if `pooled_sd' > 0 {
        local smd_uw = (`m_freq_uw' - `m_nev_uw') / `pooled_sd'
    }

    * Weighted means (pweight using cumulative MSM weights)
    capture {
        quietly summarize `v' [aweight=cum_weight] if in_outcome & arts3 == 2
        local m_freq_w = r(mean)
        quietly summarize `v' [aweight=cum_weight] if in_outcome & arts3 == 0
        local m_nev_w = r(mean)
        local smd_w = .
        if `pooled_sd' > 0 {
            local smd_w = (`m_freq_w' - `m_nev_w') / `pooled_sd'
        }
    }

    local n_used = `n_freq_uw' + `n_nev_uw'
    file write `fhb' "`v'," (string(`smd_uw', "%6.3f")) "," ///
        (string(`smd_w', "%6.3f")) "," (string(`n_used', "%9.0f")) _n
}
file close `fhb'
display "Weight balance written to $out/tables/weight_balance.csv"

*------------------------------------------------------------------------------
* Covariate balance STRATIFIED BY PRIOR EXPOSURE (A_{t-1}).
*
* A stabilised time-varying weight is designed to remove the association
* between current exposure A_t and concurrent confounders L_t conditional on
* prior exposure A_{t-1} and the age/baseline variables in the numerator.
* Raw SMDs are retained as descriptive audit fields. The primary adjusted SMDs
* come from regressions of each L_t on current exposure, age, age squared, and
* the full baseline covariate set, fitted within strata of A_{t-1}. This follows
* Jackson's regression approach when baseline variables appear in both weight
* models.
*
* Every SMD uses the pooled unweighted SD within the stratum and contrast.
* Weighted regressions use the cumulative combined MSM weight. Two contrasts
* are written: frequent (2) vs never (0) and infrequent (1) vs never (0).
*------------------------------------------------------------------------------
display _newline "=== Stratified covariate balance (by A_{t-1}) ==="
tempname fhbs
file open `fhbs' using "$out/tables/weight_balance_stratified.csv", write replace
file write `fhbs' "stratum,contrast,covariate,smd_raw_unweighted,smd_raw_weighted," ///
    "smd_adjusted_unweighted,smd_adjusted_weighted,n_hi,n_lo,n_adjusted" _n

foreach s in -1 0 1 2 {
    if `s' == -1 {
        local sname "pooled"
        local scond "in_outcome"
    }
    else {
        local lname : word `=`s'+1' of never infrequent frequent
        local sname "lag_`lname'"
        local scond "in_outcome & arts3_lag == `s'"
    }
    foreach con in 2 1 {
        if `con' == 2 local cname "freq_vs_never"
        if `con' == 1 local cname "infreq_vs_never"
        foreach v of varlist any_mobil_tv any_adl_tv any_iadl_tv cog_tv ///
            cancre lunge cvd_any_tv smoke_now_tv cesd_w poor_sight_tv poor_hear_tv {

            quietly summarize `v' if `scond' & arts3 == `con'
            local m_hi  = r(mean)
            local sd_hi = r(sd)
            local n_hi  = r(N)
            quietly summarize `v' if `scond' & arts3 == 0
            local m_lo  = r(mean)
            local sd_lo = r(sd)
            local n_lo  = r(N)

            local psd = sqrt(((`sd_hi')^2 + (`sd_lo')^2) / 2)
            local smd_raw_u = .
            local smd_raw_w = .
            local smd_adj_u = .
            local smd_adj_w = .
            local n_adjusted = .
            if `psd' > 0 & !missing(`psd') {
                local smd_raw_u = (`m_hi' - `m_lo') / `psd'
                quietly summarize `v' if `scond' & arts3 == `con' [aweight=cum_weight]
                local mw_hi = r(mean)
                quietly summarize `v' if `scond' & arts3 == 0 [aweight=cum_weight]
                local mw_lo = r(mean)
                local smd_raw_w = (`mw_hi' - `mw_lo') / `psd'

                quietly regress `v' ib0.arts3 c.agey##c.agey ///
                    i.female i.white i.married i.edu4 i.wealth5 i.working ///
                    i.poor_sight i.poor_hearing cesd i.r2psyche ///
                    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
                    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
                    if `scond' & inlist(arts3, 0, `con')
                local smd_adj_u = _b[`con'.arts3] / `psd'
                local n_adjusted = e(N)

                quietly regress `v' ib0.arts3 c.agey##c.agey ///
                    i.female i.white i.married i.edu4 i.wealth5 i.working ///
                    i.poor_sight i.poor_hearing cesd i.r2psyche ///
                    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
                    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
                    if `scond' & inlist(arts3, 0, `con') [aweight=cum_weight]
                local smd_adj_w = _b[`con'.arts3] / `psd'
                if e(N) != `n_adjusted' {
                    display as error "Adjusted balance samples differ for `sname' `cname' `v'"
                    exit 459
                }
            }
            file write `fhbs' "`sname',`cname',`v'," ///
                (string(`smd_raw_u', "%7.4f")) "," (string(`smd_raw_w', "%7.4f")) "," ///
                (string(`smd_adj_u', "%7.4f")) "," (string(`smd_adj_w', "%7.4f")) "," ///
                (string(`n_hi', "%9.0f")) "," (string(`n_lo', "%9.0f")) "," ///
                (string(`n_adjusted', "%9.0f")) _n
        }
    }
}
file close `fhbs'
display "Stratified balance written to $out/tables/weight_balance_stratified.csv"

display _newline "=============================================="
display "Fancourt 2019 published:"
display "  Frequent vs never: HR 0.69 (0.59-0.80)"
display "  Infrequent vs never: HR 0.86 (0.77-0.96)"
display "=============================================="

log close
