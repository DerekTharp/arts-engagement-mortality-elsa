*==============================================================================
* 09_death_undercount_sensitivity.do
*
* Quantitative bias analysis for the public-data death undercount.
*
* The public reconstruction observes 1,022 deaths in the wave-2 baseline
* analytic sample (N=6,055). Fancourt & Steptoe's NHS-linked endpoint
* captured ~2,001 deaths in the same sample. We do not treat 2,001 - 1,022
* = 979 as the true count of unobserved deaths for this complete-case sample:
* the harmonised file's death capture is structurally censored after ~2013,
* and the offset is best read as an order-of-magnitude calibration of the
* potential undercount, not as a fact about this analytic sample.
*
* This script bounds the baseline-fixed Cox HR for frequent-vs-never arts
* engagement under a deterministic two-dimensional grid:
*
*   n_extra     in {0, 200, 400, 600, 800, 979, 1000}
*               number of unobserved deaths to add back
*
*   rr_alloc    in {0.5, 0.67, 1.0, 1.5, 2.0, 3.0, 5.0}
*               relative risk of being assigned an unobserved death given
*               never-engagement vs frequent-engagement; infrequent gets
*               the geometric mean of the two endpoints. Values below 1
*               place the unobserved deaths preferentially among frequent
*               engagers (the direction that would attenuate the inverse
*               association), so the grid is two-sided rather than testing
*               only the conventionally raised never-engager concentration.
*
* For each of the 49 grid cells the script:
*   1. Samples n_extra person-IDs from the currently never-observed-dead
*      cohort, with selection probability proportional to allocation weights
*      that respect rr_alloc by arts3 stratum;
*   2. For each sampled person, assigns a death year drawn uniformly from
*      that person's unobserved at-risk interval (last_alive_year+1 through
*      administrative horizon; persons with no such window are excluded
*      from sampling);
*   3. Refits the baseline-fixed Cox (age timescale, full covariate set);
*   4. Repeats steps 1-3 200 times with a fixed seed and reports the
*      simulation median and 2.5/97.5 percentiles of the HR for frequent
*      vs never.
*
* Outputs are simulation intervals over the scenario, NOT confidence
* intervals; the CSV column names are HR_median, HR_p2_5, HR_p97_5
* accordingly.
*
* Output:
*   output/tables/death_undercount_sensitivity.csv
*   output/logs/09_death_undercount_sensitivity.log
*==============================================================================

capture log close
log using "$out/logs/09_death_undercount_sensitivity.log", replace text

clear all
set more off
set seed 26461022

* Administrative horizon: end of available follow-up window. We use the
* maximum observed exit_year in the baseline file as a conservative bound
* (any death after that is by construction not observable in this dataset).
use "$data/fancourt_baseline.dta", clear

* Cache wave-2 baseline year per person for the at-risk interval definition.
* exit_year is the year of death (if died==1) or administrative censoring
* (if died==0). baseline_year is wave-2 calendar year.
quietly summarize exit_year, meanonly
local admin_horizon = r(max)
display "Administrative horizon (max exit_year): " `admin_horizon'

* Confirm key variables exist
foreach v in idauniq arts3 r2agey baseline_year exit_year fu_years died ///
             female white married edu4 wealth5 working ///
             poor_sight poor_hearing cesd r2psyche ///
             r2cancre r2lunge cvd_any other_ltc ///
             smoke_now alcfreq any_mobil any_adl any_iadl cog_mean {
    capture confirm variable `v'
    if _rc {
        display as error "Required variable `v' missing from baseline file"
        exit 111
    }
}

* Define each person's unobserved at-risk window.
* For died==1 persons, no extra death can be assigned (already observed dead).
* For died==0 persons, the unobserved window runs from (exit_year + 1) up
* to admin_horizon. exit_year for survivors is the last-observed year,
* so the +1 anchors the death some time after their last known-alive
* moment. Persons whose exit_year already equals admin_horizon have no
* unobserved window and are excluded from extra-death sampling.
gen unobs_lo  = exit_year + 1 if died == 0
gen unobs_hi  = `admin_horizon' if died == 0
gen unobs_win = unobs_hi - unobs_lo + 1 if died == 0
gen eligible_for_extra = (died == 0 & unobs_win >= 1)

quietly count if eligible_for_extra
display "Survivors eligible for extra-death assignment: " r(N)

* Persist the baseline file with these new columns into a temporary copy
* that the simulation re-reads cleanly each iteration.
tempfile baseline
save "`baseline'", replace

*------------------------------------------------------------------------------
* Grid definition
*------------------------------------------------------------------------------
local n_extra_grid  "0 200 400 600 800 979 1000"
local rr_alloc_grid "0.5 0.67 1.0 1.5 2.0 3.0 5.0"
local nreps 200

* Output CSV
tempname fh
file open `fh' using "$out/tables/death_undercount_sensitivity.csv", write replace
file write `fh' "n_extra,rr_alloc,exposure,HR_median,HR_p2_5,HR_p97_5,n_reps,note" _n

*------------------------------------------------------------------------------
* Helper: run one scenario, return median + 2.5/97.5 percentiles of HR
*------------------------------------------------------------------------------
foreach n_extra of local n_extra_grid {
    foreach rr_alloc of local rr_alloc_grid {

        * Allocation weights by arts3 category. Reference (frequent) = 1.
        * rr_alloc = RR of unobserved death for never vs frequent.
        * Infrequent = geometric mean of the two endpoints.
        local w_never     = `rr_alloc'
        local w_freq      = 1
        local w_infreq    = sqrt(`rr_alloc')

        * Store per-rep HRs in three Stata locals (built as space-separated)
        local hr_inf_list ""
        local hr_freq_list ""

        forvalues rep = 1/`nreps' {

            use "`baseline'", clear

            if `n_extra' > 0 {
                * Build per-person sampling weight respecting allocation RR
                gen samp_w = 0
                replace samp_w = `w_never'  if eligible_for_extra & arts3 == 0
                replace samp_w = `w_infreq' if eligible_for_extra & arts3 == 1
                replace samp_w = `w_freq'   if eligible_for_extra & arts3 == 2

                * Draw n_extra persons without replacement, probability prop
                * to samp_w. Use a random sort with weight-adjusted noise:
                * generate u ~ U(0,1), set rank_key = -ln(u)/samp_w, sort
                * ascending and take the first n_extra (efficient Poisson
                * sampling without replacement; smaller key = higher
                * probability of being selected when sampling without
                * replacement proportional to samp_w).
                quietly count if eligible_for_extra
                if r(N) < `n_extra' {
                    display as error "Cell (n_extra=`n_extra', rr=`rr_alloc') rep `rep': " ///
                        "eligible pool (r(N)) smaller than n_extra (`n_extra')"
                    continue, break
                }
                gen u = runiform() if eligible_for_extra
                gen rank_key = -ln(u) / samp_w if eligible_for_extra
                * Mark the n_extra persons with the smallest rank_key as
                * receiving an unobserved death
                gen rank_pos = .
                gsort - eligible_for_extra rank_key
                quietly replace rank_pos = _n if eligible_for_extra
                gen sampled_extra = (rank_pos <= `n_extra') & eligible_for_extra

                * For sampled persons, assign death year uniformly across
                * their unobserved at-risk interval [unobs_lo, unobs_hi].
                * (Integer year for simplicity; the Cox uses age at exit so
                * sub-year precision is unnecessary at this scale.)
                gen extra_offset = floor(runiform() * unobs_win) if sampled_extra
                gen new_exit_year = exit_year if !sampled_extra
                replace new_exit_year = unobs_lo + extra_offset if sampled_extra
                gen new_died = died
                replace new_died = 1 if sampled_extra
                gen new_fu_years = new_exit_year - baseline_year

                * Persons whose new_fu_years is non-positive should not enter
                * the survival model (shouldn't happen given unobs_lo > exit_year)
                drop if new_fu_years <= 0
            }
            else {
                * No extras to add; use observed data as is
                gen new_died = died
                gen new_fu_years = fu_years
            }

            * Refit baseline-fixed Cox with age as timescale
            capture {
                gen entry_age = r2agey
                gen exit_age  = r2agey + new_fu_years
                stset exit_age, failure(new_died==1) enter(time entry_age) ///
                    origin(time 0)
                quietly stcox ib0.arts3 ///
                    i.female i.white i.married i.edu4 i.wealth5 i.working ///
                    i.poor_sight i.poor_hearing cesd i.r2psyche ///
                    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
                    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean, nolog
                local hr_inf  = exp(_b[1.arts3])
                local hr_freq = exp(_b[2.arts3])
                local hr_inf_list  "`hr_inf_list' `hr_inf'"
                local hr_freq_list "`hr_freq_list' `hr_freq'"
            }
            if _rc {
                display as error "Cox fit failed at cell n_extra=`n_extra' rr=`rr_alloc' rep=`rep'"
            }
        }

        * Summarise across the `nreps' simulation HRs for this cell.
        * Push the lists into a temp dataset to use Stata's pctile.
        foreach lab in inf freq {
            clear
            tempname mat
            local list `hr_`lab'_list'
            local n : word count `list'
            if `n' == 0 continue
            quietly set obs `n'
            gen hr = .
            forvalues i = 1/`n' {
                local val : word `i' of `list'
                quietly replace hr = `val' in `i'
            }
            quietly _pctile hr, percentiles(2.5 50 97.5)
            local p25_  = r(r1)
            local p50_  = r(r2)
            local p975_ = r(r3)
            local exposure = cond("`lab'" == "inf", "Infrequent", "Frequent")
            local note "deterministic grid; sim intervals over `nreps' reps with extras allocated by RR"
            file write `fh' "`n_extra',`rr_alloc',`exposure'," ///
                (string(`p50_', "%5.3f")) "," ///
                (string(`p25_', "%5.3f")) "," ///
                (string(`p975_', "%5.3f")) "," ///
                "`nreps',`note'" _n
            display "Cell n_extra=`n_extra' rr=`rr_alloc' `exposure': " ///
                "median " %5.3f `p50_' " (2.5p " %5.3f `p25_' " 97.5p " %5.3f `p975_' ")"
        }
    }
}

file close `fh'

display _newline "Bias-analysis grid written to $out/tables/death_undercount_sensitivity.csv"

log close
