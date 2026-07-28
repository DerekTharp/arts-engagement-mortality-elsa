*==============================================================================
* 04_time_varying_cox.do
*
* Supplementary time-varying Cox regression with arts engagement updated at
* each wave. Uses age as the timescale and a subset of baseline covariates
* plus time-varying health confounders. Estimated on the monotone-censored
* panel (observed rows only). Reported as supplementary context in the
* manuscript; the primary comparison uses discrete-time cloglog models
* in 05_msm_iptw.do.
*==============================================================================

capture log close
log using "$out/logs/04_time_varying_cox.log", replace text

use "$data/fancourt_panel.dta", clear

* All panel rows are observed under monotone censoring
keep if observed == 1

* Sample size assertion (panel should be ~25,000-35,000 person-waves)
count
assert r(N) > 20000 & r(N) < 40000
display "Panel person-waves: " _N

*------------------------------------------------------------------------------
* 1. Bring in time-invariant baseline covariates
*------------------------------------------------------------------------------
merge m:1 idauniq using "$data/fancourt_baseline.dta", ///
    keepusing(female white married edu4 wealth5 working poor_sight poor_hearing ///
              r2psyche) ///
    keep(master match) nogen

sort idauniq wave

*------------------------------------------------------------------------------
* 2. Build time-varying covariates from the panel
*------------------------------------------------------------------------------
* Belt-and-suspenders sentinel cleaning (primary cleaning is in 03_build_panel.do)
foreach v of varlist hibpe hearte stroke diabe smoken mobilba adlwaa iadlaa ///
    sight hearing imrc dlrc orient cesd_w cancre lunge {
    capture confirm numeric variable `v'
    if !_rc quietly replace `v' = . if `v' < 0
}

gen cvd_any   = (hibpe == 1 | hearte == 1 | stroke == 1 | diabe == 1)
replace cvd_any = . if missing(hibpe) & missing(hearte) & missing(stroke) & missing(diabe)

gen smoke_now = (smoken == 1) if !missing(smoken)
gen any_mobil = (mobilba == 1) if !missing(mobilba)
gen any_adl   = (adlwaa  == 1) if !missing(adlwaa)
gen any_iadl  = (iadlaa  == 1) if !missing(iadlaa)

gen poor_sight_w   = inrange(sight, 4, 6)    if !missing(sight)
gen poor_hear_w    = inrange(hearing, 4, 6) if !missing(hearing)

foreach v in imrc dlrc orient {
    capture confirm numeric variable `v'
    if !_rc quietly replace `v' = . if `v' < 0
}
egen zimrc_w   = std(imrc)
egen zdlrc_w   = std(dlrc)
egen zorient_w = std(orient)
egen cog_mean_w = rowmean(zimrc_w zdlrc_w zorient_w)

*------------------------------------------------------------------------------
* 3. Set up time-varying survival data with AGE as the time scale
*------------------------------------------------------------------------------
* Each row is a [wave interval] for one person. Use baseline age plus the
* elapsed follow-up time so the start/stop ages are coherent across rows.

gen entry_age = r2agey + (start_year - baseline_year)
gen exit_age  = r2agey + (stop_year  - baseline_year)

* Drop any rows with missing age or implausible intervals
drop if missing(entry_age) | missing(exit_age) | exit_age <= entry_age

stset exit_age, id(idauniq) failure(died_in_interval==1) enter(time entry_age) origin(time 0)

*------------------------------------------------------------------------------
* 4. Model A — time-varying arts engagement, age only
*------------------------------------------------------------------------------
display _newline "=== Time-varying Model A: arts engagement, age only ==="
stcox c.arts3, nolog vce(cluster idauniq)

*------------------------------------------------------------------------------
* 5. Model B — time-varying exposure, baseline-only (time-invariant) covariates
*------------------------------------------------------------------------------
display _newline "=== Time-varying Model B: arts engagement, baseline covariates ==="
stcox c.arts3 i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing i.r2psyche, ///
    nolog vce(cluster idauniq)

*------------------------------------------------------------------------------
* 6. Model C — time-varying exposure AND time-varying health covariates
*------------------------------------------------------------------------------
display _newline "=== Time-varying Model C: arts engagement + time-varying health ==="
stcox c.arts3 i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight_w i.poor_hear_w cesd_w i.r2psyche ///
    i.cancre i.lunge i.cvd_any ///
    i.smoke_now i.any_mobil i.any_adl i.any_iadl cog_mean_w, ///
    nolog vce(cluster idauniq)

*------------------------------------------------------------------------------
* 7. Categorical version of Model C (for interpretation alongside Fancourt)
*------------------------------------------------------------------------------
display _newline "=== Time-varying Model C-cat: 3-category arts exposure ==="
stcox ib0.arts3 i.female i.white i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight_w i.poor_hear_w cesd_w i.r2psyche ///
    i.cancre i.lunge i.cvd_any ///
    i.smoke_now i.any_mobil i.any_adl i.any_iadl cog_mean_w, ///
    nolog vce(cluster idauniq)

display _newline "=============================================="
display "Fancourt 2019 published:"
display "  Frequent vs never: HR 0.69 (0.59-0.80)"
display "  Infrequent vs never: HR 0.86 (0.77-0.96)"
display "=============================================="

log close
