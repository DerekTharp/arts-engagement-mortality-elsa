*==============================================================================
* 02_cox_replication.do
*
* Reproduces Fancourt & Steptoe 2019 (BMJ 367:l6377) headline Cox model:
*   HR 0.69 (95% CI 0.59-0.80) for frequent arts engagement vs never
*   HR 0.86 (0.77-0.96) for infrequent vs never
*   HR 0.80 (0.75-0.87) per-category continuous
*
* Fancourt used age as the time scale (survival time in months from birth date
* to death/censoring/end of follow-up). We use the same specification with
* interval-censored death times from ELSA interview status transitions.
*==============================================================================

capture log close
log using "$out/logs/02_cox_replication.log", replace text

use "$data/fancourt_baseline.dta", clear

* Sample size assertion (baseline sample should be ~6,000-7,500)
count
assert r(N) > 5500 & r(N) < 8000
display "Baseline sample N = " _N

*------------------------------------------------------------------------------
* 1. Set up survival data with AGE as the time scale
*------------------------------------------------------------------------------
gen entry_age = r2agey
gen exit_age  = r2agey + fu_years

stset exit_age, failure(died==1) enter(time entry_age) origin(time 0)

*------------------------------------------------------------------------------
* 2. Model 1 — age-adjusted only (continuous exposure)
*------------------------------------------------------------------------------
display _newline "=== Model 1: age only (continuous arts exposure) ==="
stcox c.arts3, nolog

*------------------------------------------------------------------------------
* 3. Model 2 — fully adjusted (continuous exposure)
*------------------------------------------------------------------------------
display _newline "=== Model 2: fully adjusted (continuous arts exposure) ==="
stcox c.arts3 i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean, nolog

*------------------------------------------------------------------------------
* 4. Model 3 — fully adjusted (categorical exposure: never / infrequent / frequent)
*------------------------------------------------------------------------------
display _newline "=== Model 3: fully adjusted (3-category arts exposure) ==="
stcox ib0.arts3 i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean, nolog

*------------------------------------------------------------------------------
* 5. Store hazard ratios for comparison with Fancourt's published values
*------------------------------------------------------------------------------
display _newline "=============================================="
display "Fancourt 2019 published values:"
display "  Frequent vs never: HR 0.69 (0.59-0.80)"
display "  Infrequent vs never: HR 0.86 (0.77-0.96)"
display "  Continuous per category: HR 0.80 (0.75-0.87)"
display "=============================================="

log close
