*==============================================================================
* 03_build_panel.do
*
* Builds the long person-wave panel for the time-varying extension under
* MONOTONE CENSORING. Once a participant misses a wave (first wave where
* iwstat != 1), they are permanently censored. No re-entry, no LOCF for
* exposure at unobserved waves. This gives the IPCW model a clean structure.
*
* Each row represents a person-wave interval [wave_t, wave_t+1). The standard
* last interval is wave 9 -> wave 10 (2018.5 -> 2022.0). Wave-10 rows are
* dropped unless they carry a known terminal death after the wave-10 interview.
*
* Output variables:
*   arts3           time-varying 3-category arts engagement (observed only)
*   observed        1 for all rows (monotone censoring drops unobserved)
*   censored_next   1 at the last observed wave if dropout follows
*   died_in_interval 1 if death falls in this interval
*   start_year      wave_year at the start of the interval
*   stop_year       wave_year at the end (next wave, or death midpoint)
*   interval_years  stop_year - start_year
*
* Output: data/fancourt_panel.dta
*==============================================================================

capture log close
log using "$out/logs/03_build_panel.log", replace text

*------------------------------------------------------------------------------
* 1. Pull arts engagement from each wave 2-10
*------------------------------------------------------------------------------
local wavefiles "wave_2_core_data_v4.dta wave_3_elsa_data_v4.dta wave_4_elsa_data_v3.dta wave_5_elsa_data_v4.dta wave_6_elsa_data_v2.dta wave_7_elsa_data.dta wave_8_elsa_data_eul_v2.dta wave_9_elsa_data_eul_v2.dta wave_10_elsa_data_eul_v4.dta"
local w = 1
tempfile artsw
foreach f of local wavefiles {
    local w = `w' + 1
    display _newline "Loading arts engagement from wave `w' ($waves/`f')"
    use idauniq scacta scactc scactd using "$waves/`f'", clear
    foreach v in scacta scactc scactd {
        capture confirm numeric variable `v'
        if !_rc quietly replace `v' = . if `v' < 0
    }
    gen wave = `w'
    * Composite frequency: min() returns the observed value when only one
    * item is non-missing, and missing when both items are missing.
    gen arts_freq_w = min(scactc, scactd)
    gen arts3_w = .
    replace arts3_w = 0 if arts_freq_w == 6
    replace arts3_w = 1 if inlist(arts_freq_w, 4, 5)
    replace arts3_w = 2 if inlist(arts_freq_w, 1, 2, 3)
    keep idauniq wave arts3_w arts_freq_w
    if `w' == 2 {
        save `artsw', replace
    }
    else {
        append using `artsw'
        save `artsw', replace
    }
}

use `artsw', clear
tab wave arts3_w, missing
save "$data/arts_long.dta", replace

*------------------------------------------------------------------------------
* 2. Pull time-varying covariates from harmonised ELSA, reshape long
*------------------------------------------------------------------------------

use idauniq ragender raracem raeduc_e ///
    r2agey r3agey r4agey r5agey r6agey r7agey r8agey r9agey r10agey ///
    r2iwstat r3iwstat r4iwstat r5iwstat r6iwstat r7iwstat r8iwstat r9iwstat r10iwstat ///
    r2mstat r3mstat r4mstat r5mstat r6mstat r7mstat r8mstat r9mstat r10mstat ///
    r2lbrf_e r3lbrf_e r4lbrf_e r5lbrf_e r6lbrf_e r7lbrf_e r8lbrf_e r9lbrf_e r10lbrf_e ///
    h2atotb h3atotb h4atotb h5atotb h6atotb h7atotb h8atotb h9atotb h10atotb ///
    r2cesd r3cesd r4cesd r5cesd r6cesd r7cesd r8cesd r9cesd r10cesd ///
    r2cancre r3cancre r4cancre r5cancre r6cancre r7cancre r8cancre r9cancre r10cancre ///
    r2lunge r3lunge r4lunge r5lunge r6lunge r7lunge r8lunge r9lunge r10lunge ///
    r2hearte r3hearte r4hearte r5hearte r6hearte r7hearte r8hearte r9hearte r10hearte ///
    r2stroke r3stroke r4stroke r5stroke r6stroke r7stroke r8stroke r9stroke r10stroke ///
    r2hibpe r3hibpe r4hibpe r5hibpe r6hibpe r7hibpe r8hibpe r9hibpe r10hibpe ///
    r2diabe r3diabe r4diabe r5diabe r6diabe r7diabe r8diabe r9diabe r10diabe ///
    r2smoken r3smoken r4smoken r5smoken r6smoken r7smoken r8smoken r9smoken r10smoken ///
    r2mobilba r3mobilba r4mobilba r5mobilba r6mobilba r7mobilba r8mobilba r9mobilba r10mobilba ///
    r2adlwaa r3adlwaa r4adlwaa r5adlwaa r6adlwaa r7adlwaa r8adlwaa r9adlwaa r10adlwaa ///
    r2iadlaa r3iadlaa r4iadlaa r5iadlaa r6iadlaa r7iadlaa r8iadlaa r9iadlaa r10iadlaa ///
    r2imrc r3imrc r4imrc r5imrc r6imrc r7imrc r8imrc r9imrc r10imrc ///
    r2dlrc r3dlrc r4dlrc r5dlrc r6dlrc r7dlrc r8dlrc r9dlrc r10dlrc ///
    r2orient r3orient r4orient r5orient r6orient r7orient r8orient r9orient r10orient ///
    r2sight r3sight r4sight r5sight r6sight r7sight r8sight r9sight r10sight ///
    r2hearing r3hearing r4hearing r5hearing r6hearing r7hearing r8hearing r9hearing r10hearing ///
    r2proxy r3proxy r4proxy r5proxy r6proxy r7proxy r8proxy r9proxy r10proxy ///
    r2wtresp ///
    using "$harm", clear

* Keep only persons in the baseline sample
merge 1:1 idauniq using "$data/fancourt_baseline.dta", keepusing(idauniq) keep(match) nogen

reshape long r@iwstat r@agey r@mstat r@lbrf_e h@atotb r@cesd ///
    r@cancre r@lunge r@hearte r@stroke r@hibpe r@diabe r@smoken ///
    r@mobilba r@adlwaa r@iadlaa ///
    r@imrc r@dlrc r@orient r@sight r@hearing r@proxy, ///
    i(idauniq) j(wave)

rename riwstat   iwstat
rename ragey     agey
rename rmstat    mstat
rename rlbrf_e   lbrf_e
rename hatotb    atotb
rename rcesd     cesd_w
rename rcancre   cancre
rename rlunge    lunge
rename rhearte   hearte
rename rstroke   stroke
rename rhibpe    hibpe
rename rdiabe    diabe
rename rsmoken   smoken
rename rmobilba  mobilba
rename radlwaa   adlwaa
rename riadlaa   iadlaa
rename rimrc     imrc
rename rdlrc     dlrc
rename rorient   orient
rename rsight    sight
rename rhearing  hearing
rename rproxy    proxy

* Clean harmonised negative sentinels before any panel recodes so they do not
* leak into 0/1 indicators as healthy values.
foreach v in mstat lbrf_e atotb cesd_w cancre lunge hearte stroke hibpe diabe ///
    smoken mobilba adlwaa iadlaa imrc dlrc orient sight hearing proxy {
    capture confirm numeric variable `v'
    if !_rc quietly replace `v' = . if `v' < 0
}

*------------------------------------------------------------------------------
* 2b. Apply monotone censoring: keep only waves where the person was
*     interviewed AND has observed arts engagement. Once either condition
*     fails, all subsequent waves are permanently censored.
*
*     "Observed" = iwstat==1 AND non-missing arts engagement. A person
*     interviewed but missing the self-completion arts items is treated
*     as censored, because exposure is unobserved. This ensures the
*     treatment model never uses imputed or missing exposure values.
*------------------------------------------------------------------------------

* Keep only waves where the person was interviewed
keep if iwstat == 1

* Merge arts engagement
merge 1:1 idauniq wave using "$data/arts_long.dta", keep(master match) nogen
gen arts3 = arts3_w

* Drop waves where arts engagement is missing (self-completion non-response).
* This must happen BEFORE monotone enforcement so that a missing-arts wave
* triggers censoring of all subsequent waves, even if they have complete data.
count if missing(arts3)
display "Interviewed waves with missing arts (treated as censored): " r(N)
drop if missing(arts3)

display _newline "Before monotone censoring enforcement (interviewed + arts observed):"
tab wave, missing

* Enforce monotone structure: for each person, keep waves 2 through their
* first contiguous run. A gap means _n > 1 and wave != wave[_n-1] + 1.
sort idauniq wave
by idauniq: gen gap = (wave != wave[_n-1] + 1) if _n > 1
by idauniq: gen first_gap = sum(gap)
drop if first_gap > 0
drop gap first_gap

display _newline "After monotone censoring enforcement:"
tab wave, missing

* All remaining rows are interviewed with observed exposure
gen observed = 1
label variable observed "1=interviewed and arts observed (all rows under monotone censoring)"

tab wave arts3, missing

*------------------------------------------------------------------------------
* 3. Bring in death info and construct censored_next and died_in_interval
*
*    IMPORTANT: censored_next and died_in_interval are computed BEFORE
*    dropping wave-10 rows, using the full monotone panel to determine
*    each person's last_panel_wave. This avoids misclassifying wave-10
*    completers as censored.
*------------------------------------------------------------------------------

merge m:1 idauniq using "$data/fancourt_baseline.dta", ///
    keepusing(died died_wave death_year death_source ///
        r2agey last_alive_wave last_interviewed_wave baseline_year ///
        hcap_last_productive_wave hcap_last_ivw_year hcap_last_ivw_month) ///
    keep(match) nogen
sort idauniq wave

* last_panel_wave: the last wave in each person's monotone run (including wave 10)
by idauniq: gen last_panel_wave = wave[_N]

*------------------------------------------------------------------------------
* 3a. Bring in the next-wave harmonised iwstat for each panel row.
*
*     ELSA fieldwork is a window (e.g. wave 3 ran 2006-07), so a death the
*     harmonised file codes at wave (w+1) can have a death_year that falls
*     slightly past the midpoint between wave w and wave w+1. A terminal death
*     is therefore attributed to the wave-w interval whenever the next wave
*     codes the respondent as died (iwstat 5/6), not only when the midpoint
*     window happens to contain death_year. Because every panel row is an
*     observed (interviewed) wave, the respondent is alive at their last panel
*     wave, so a terminal death is coded 5 ("died this wave") at w+1; code 6
*     ("died previous wave") cannot arise at this boundary and contributes no
*     deaths (it is retained in the condition only for completeness).
*------------------------------------------------------------------------------
preserve
use idauniq r2iwstat r3iwstat r4iwstat r5iwstat r6iwstat ///
    r7iwstat r8iwstat r9iwstat r10iwstat using "$harm", clear
tempfile harm_iwstat_all
save "`harm_iwstat_all'"
restore
merge m:1 idauniq using "`harm_iwstat_all'", keep(master match) nogen

gen next_iwstat = .
forvalues w = 2/9 {
    local w1 = `w' + 1
    replace next_iwstat = r`w1'iwstat if wave == `w'
}
drop r2iwstat r3iwstat r4iwstat r5iwstat r6iwstat ///
     r7iwstat r8iwstat r9iwstat r10iwstat

*------------------------------------------------------------------------------
* 4. Construct wave-year variables and assign terminal death intervals
*------------------------------------------------------------------------------

gen wave_year = .
replace wave_year = 2004.5 if wave == 2
replace wave_year = 2006.5 if wave == 3
replace wave_year = 2008.5 if wave == 4
replace wave_year = 2010.5 if wave == 5
replace wave_year = 2012.5 if wave == 6
replace wave_year = 2014.5 if wave == 7
replace wave_year = 2016.5 if wave == 8
replace wave_year = 2018.5 if wave == 9
replace wave_year = 2022.0 if wave == 10

gen scheduled_next_year = .
replace scheduled_next_year = 2006.5 if wave == 2
replace scheduled_next_year = 2008.5 if wave == 3
replace scheduled_next_year = 2010.5 if wave == 4
replace scheduled_next_year = 2012.5 if wave == 5
replace scheduled_next_year = 2014.5 if wave == 6
replace scheduled_next_year = 2016.5 if wave == 7
replace scheduled_next_year = 2018.5 if wave == 8
replace scheduled_next_year = 2022.0 if wave == 9

* --- died_in_interval ---
* A death is observed in the panel if it is attributable to the interval
* following the last observed row. We accept three pieces of evidence:
*   (i)  next_iwstat in {5, 6} -- harmonised file authoritatively codes the
*        death at the next wave, regardless of fine-grained death_year timing
*   (ii) death_year falls within the standard wave-midpoint window
*   (iii) for wave 10 (no scheduled wave 11), any death_year strictly after
*        the wave-10 interview is attributed to the wave-10 terminal interval
gen died_in_interval = 0
replace died_in_interval = 1 if died == 1 ///
    & wave == last_panel_wave ///
    & ( ///
        inlist(next_iwstat, 5, 6) ///
        | (!missing(scheduled_next_year) & death_year <= scheduled_next_year) ///
        | (wave == 10 & death_year > wave_year) ///
    ) ///
    & (missing(hcap_last_productive_wave) | hcap_last_productive_wave == last_panel_wave)

display _newline "Deaths in panel:"
tab died_in_interval
tab wave died_in_interval, missing

* --- censored_next ---
* Last observed row before administrative end, provided the death was not
* observed in the immediately following interval.
gen censored_next = 0
replace censored_next = 1 if wave == last_panel_wave ///
    & !missing(scheduled_next_year) ///
    & died_in_interval == 0

display _newline "Censored_next distribution:"
tab censored_next
tab wave censored_next, missing

*------------------------------------------------------------------------------
* 5. Drop wave-10 rows without a terminal death interval
*------------------------------------------------------------------------------
display _newline "Rows at wave 10 before drop:"
count if wave == 10

drop if wave == 10 & died_in_interval == 0

display _newline "After dropping wave 10:"
tab wave, missing

sort idauniq wave
by idauniq: gen next_wave = wave[_n+1]

*------------------------------------------------------------------------------
* 6. Compute start_year, stop_year, interval_years
*------------------------------------------------------------------------------

gen start_year = wave_year

* Next wave's year for standard interval endpoint
sort idauniq wave
by idauniq: gen next_wave_year = wave_year[_n+1]

gen stop_year = .

* (a) Non-terminal rows: interval ends at next wave in the panel
replace stop_year = next_wave_year if !missing(next_wave_year)

* (b) Death intervals: stop at the observed/approximated death year.
*     If the recorded death year falls before the generic wave midpoint,
*     clamp to a short positive terminal interval rather than dropping the case.
replace stop_year = death_year if died_in_interval == 1
replace stop_year = wave_year + 0.25 if died_in_interval == 1 & stop_year <= wave_year

* (c) Right-censored at the last panel wave (alive, no death in this interval,
*     no subsequent wave in the panel). The person either dropped out or
*     reached the end of follow-up. Interval ends at the next scheduled wave.
* For waves 2-8: next scheduled wave is 2 years later
replace stop_year = wave_year + 2.0 if missing(stop_year) & died_in_interval == 0 & wave <= 8
* For wave 9: next scheduled wave is wave 10 at 2022.0 (3.5 years later)
replace stop_year = wave_year + 3.5 if missing(stop_year) & died_in_interval == 0 & wave == 9

gen interval_years = stop_year - start_year
label variable interval_years "Length of this person-wave interval in years"

*------------------------------------------------------------------------------
* 7. Sanity checks and cleanup
*------------------------------------------------------------------------------

* Verify all intervals are positive
count if interval_years <= 0 & !missing(interval_years)
if r(N) > 0 {
    display as error "WARNING: " r(N) " rows with interval_years <= 0"
    list idauniq wave wave_year stop_year interval_years died_in_interval ///
        if interval_years <= 0 & !missing(interval_years) in 1/20
}
assert interval_years > 0 & !missing(interval_years)

* Verify no missing stop_year
assert !missing(stop_year)

display _newline "Interval length by wave:"
summarize interval_years, detail
tabstat interval_years, by(wave) statistics(mean sd min max n)

* Verify no missing exposure (should be impossible under monotone censoring)
assert !missing(arts3)

* Drop temporary variables
drop next_wave_year last_panel_wave next_wave scheduled_next_year

tab wave, missing
tab wave arts3, missing
tab wave died_in_interval, missing
tab wave censored_next, missing
summarize interval_years, detail

save "$data/fancourt_panel.dta", replace

*------------------------------------------------------------------------------
* 8. Summary diagnostics
*------------------------------------------------------------------------------

display _newline "=============================================="
display "Person-wave panel built (monotone censoring)."
count
display "Total person-waves: " r(N)
tempvar tag
egen `tag' = tag(idauniq)
quietly count if `tag' == 1
display "Unique persons: " r(N)
count if died_in_interval == 1
display "Death intervals: " r(N)
count if censored_next == 1
display "Censored-next events: " r(N)
count if observed == 0
display "Unobserved rows (should be 0): " r(N)
display "=============================================="

log close
