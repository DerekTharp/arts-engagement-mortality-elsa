*==============================================================================
* 01_build_sample.do
*
* Builds the wave 2 baseline analytic sample for Fancourt & Steptoe 2019
* replication.
*
* Output:
*   data/fancourt_baseline.dta   wave 2 cross-section with follow-up time and
*                                death indicator, for the baseline Cox model
*
* The person-wave panel for the time-varying extension is built separately
* in 03_build_panel.do.
*
* Target sample size for baseline: approximately 6,710 (Fancourt's flowchart).
* Follow-up construction should be validated against raw status labels and
* external death files rather than inferred from project notes.
*==============================================================================

capture log close
log using "$out/logs/01_build_sample.log", replace text

*------------------------------------------------------------------------------
* 1. Arts engagement at wave 2 baseline
*------------------------------------------------------------------------------
use idauniq scacta scactc scactd using "$waves/wave_2_core_data_v4.dta", clear

* Fancourt's "receptive arts engagement" composite = max frequency across
* art galleries/museums (scactc) and theatre/concerts/opera (scactd).
* Cinema (scacta) is excluded.
* Coding: 1=twice monthly+, 2=once monthly, 3=every few months,
*         4=once or twice a year, 5=less than once a year, 6=never
* Missing codes (-1, -9) set to .

foreach v of varlist scactc scactd {
    replace `v' = . if `v' < 0
}

* Composite = minimum of scactc and scactd (lower code = more frequent).
* Stata's min() ignores missing values, so when only one item is observed the
* composite takes that item's value; when both are missing the composite is
* missing.
gen arts_freq = min(scactc, scactd)

* Fancourt's 3-category: never / infrequent / frequent
gen arts3 = .
replace arts3 = 0 if arts_freq == 6                                // never
replace arts3 = 1 if inlist(arts_freq, 4, 5)                       // infrequent
replace arts3 = 2 if inlist(arts_freq, 1, 2, 3)                    // frequent
label define arts3lbl 0 "Never" 1 "Infrequent" 2 "Frequent"
label values arts3 arts3lbl

tab arts3, missing
save "$data/w2_arts.dta", replace

*------------------------------------------------------------------------------
* 2. Wave 2 baseline covariates (from harmonised ELSA)
*------------------------------------------------------------------------------
use idauniq ragender raracem raeduc_e r2agey r2mstat r2lbrf_e ///
    h2atotb r2proxy r2wtresp ///
    r2iwstat r2sight r2hearing r2cesd r2psyche ///
    r2cancre r2lunge r2hearte r2stroke r2hibpe r2diabe r2arthre r2osteoe ///
    r2smoken r2drinkd_e r2mobilba r2adlwaa r2iadlaa ///
    r2imrc r2dlrc r2orient ///
    r3iwstat r4iwstat r5iwstat r6iwstat r7iwstat r8iwstat r9iwstat r10iwstat ///
    using "$harm", clear

* Restrict to respondents with a wave 2 interview (iwstat==1)
keep if r2iwstat == 1
count
display "Wave 2 respondents (r2iwstat==1): " r(N)

* Age 50+
drop if r2agey < 50 | missing(r2agey)
count
display "Wave 2 age 50+: " r(N)

merge 1:1 idauniq using "$data/w2_arts.dta", keep(match) nogen
count
display "With arts engagement data: " r(N)

*------------------------------------------------------------------------------
* 3. Covariate construction — match Fancourt's operationalisations
*------------------------------------------------------------------------------

* Clean negative sentinel codes across all covariates before constructing
* derived variables. Harmonised ELSA uses -1 (not applicable), -9 (refused),
* -8 (don't know) as missing sentinels. Setting these to . prevents them
* from leaking into binary indicators as valid zeros.
foreach v of varlist ragender raracem r2mstat raeduc_e r2lbrf_e ///
    r2sight r2hearing r2cesd ///
    r2cancre r2lunge r2hearte r2stroke r2hibpe r2diabe r2arthre r2osteoe r2psyche ///
    r2smoken r2drinkd_e r2mobilba r2adlwaa r2iadlaa ///
    r2imrc r2dlrc r2orient {
    capture confirm numeric variable `v'
    if !_rc quietly replace `v' = . if `v' < 0
}

* Sex (1=male, 2=female in harmonised → 0/1)
gen female = (ragender == 2) if !missing(ragender)

* White British vs other
gen white = (raracem == 1) if !missing(raracem)

* Marital: married/cohabiting (1) vs single/widowed/divorced (0)
gen married = inlist(r2mstat, 1, 3) if !missing(r2mstat)

* Education (raeduc_e: harmonised ELSA categorical)
* Collapse to Fancourt's 4 categories
tab raeduc_e, missing
gen edu4 = .
replace edu4 = 1 if raeduc_e <= 2 & !missing(raeduc_e)             // no qual / low
replace edu4 = 2 if raeduc_e == 3                                  // age 16 qual
replace edu4 = 3 if raeduc_e == 4                                  // age 18 qual
replace edu4 = 4 if raeduc_e >= 5 & !missing(raeduc_e)             // degree
label define edu4lbl 1 "No qual" 2 "Age-16 qual" 3 "Age-18 qual" 4 "Degree"
label values edu4 edu4lbl

* Wealth fifths (from total non-housing+housing wealth)
xtile wealth5 = h2atotb, nq(5)

* Employment: working FT or PT vs not working / retired
gen working = inlist(r2lbrf_e, 1, 2) if !missing(r2lbrf_e)

* Self-rated sensory (1=excellent...5=poor in harmonised; 6=blind/deaf)
gen poor_sight   = inrange(r2sight, 4, 6)   if !missing(r2sight)
gen poor_hearing = inrange(r2hearing, 4, 6) if !missing(r2hearing)

* Fancourt groups cardiovascular disease (high BP, heart problems, stroke, diabetes)
gen cvd_any = (r2hibpe==1 | r2hearte==1 | r2stroke==1 | r2diabe==1)
replace cvd_any = . if missing(r2hibpe) & missing(r2hearte) & missing(r2stroke) & missing(r2diabe)

* Other long-term conditions (arthritis, osteoporosis, other)
gen other_ltc = (r2arthre==1 | r2osteoe==1)
replace other_ltc = . if missing(r2arthre) & missing(r2osteoe)

* Smoking now
gen smoke_now = (r2smoken == 1) if !missing(r2smoken)

* Alcohol frequency (0-7 days per week typically)
gen alcfreq = r2drinkd_e if r2drinkd_e >= 0

* Mobility / ADL / IADL any difficulty (0/1 indicators from harmonised derived vars)
gen any_mobil = (r2mobilba == 1) if !missing(r2mobilba)
gen any_adl   = (r2adlwaa  == 1) if !missing(r2adlwaa)
gen any_iadl  = (r2iadlaa  == 1) if !missing(r2iadlaa)

* Depressive symptoms (CESD 0-8)
gen cesd = r2cesd

* Cognition — composite of harmonised items available at wave 2
* r2imrc (immediate recall), r2dlrc (delayed recall), r2orient (orientation)
* Negative sentinels already cleaned above.
egen zimrc   = std(r2imrc)
egen zdlrc   = std(r2dlrc)
egen zorient = std(r2orient)
egen cog_mean = rowmean(zimrc zdlrc zorient)

*------------------------------------------------------------------------------
* 4. Mortality construction — validated `iwstat` plus EOL supplements
*------------------------------------------------------------------------------
* Gateway Harmonized ELSA interview status codes (verified against
* value labels in gh_elsa_h.dta):
*   0 = inap. (not in sample at this wave)
*   1 = resp, alive (interviewed)
*   4 = nr, alive (non-response, alive — NOT dead)
*   5 = nr, died this wv (died between previous wave and this wave)
*   6 = nr, died prev wv (death carried forward from earlier coding)
*   7 = nr, dropped from samp
*   9 = nr, dk if alive or died
*
* Construction rule:
*   1. Use observed death year/season from later EOL sources when available.
*   2. Otherwise use harmonised EOL year/season.
*   3. Otherwise fall back to the iwstat interval midpoint.

gen died_wave = .
forvalues w = 3/10 {
    capture confirm variable r`w'iwstat
    if !_rc {
        replace died_wave = `w' if missing(died_wave) & inlist(r`w'iwstat, 5, 6)
    }
}

* Confirmed alive requires an explicit alive code, not unknown status.
gen last_alive_wave = 2
forvalues w = 3/10 {
    capture confirm variable r`w'iwstat
    if !_rc {
        replace last_alive_wave = `w' if inlist(r`w'iwstat, 1, 4)
    }
}

* Last wave actually interviewed (iwstat==1 only). Used by 03_build_panel.do
* to determine the censoring point under monotone censoring.
gen last_interviewed_wave = 2
forvalues w = 3/10 {
    capture confirm variable r`w'iwstat
    if !_rc {
        replace last_interviewed_wave = `w' if r`w'iwstat == 1
    }
}

* Last wave with any non-inapp status. Keep this for diagnostics only.
* Unknown-status codes (for example iwstat==9) should not extend censoring
* beyond the last confirmed-alive wave.
gen last_contact_wave = 2
forvalues w = 3/10 {
    capture confirm variable r`w'iwstat
    if !_rc {
        replace last_contact_wave = `w' if inlist(r`w'iwstat, 1, 4, 5, 6, 7, 9)
    }
}

merge 1:1 idauniq using "$eol", ///
    keepusing(idauniq raxyear raxseason) keep(master match) gen(harm_eol_merge)
gen in_eol_harm = (harm_eol_merge == 3)
drop harm_eol_merge

foreach v in raxyear raxseason {
    capture confirm numeric variable `v'
    if !_rc quietly replace `v' = . if `v' < 0
}

capture confirm file "$eol_w10"
if !_rc {
    merge 1:1 idauniq using "$eol_w10", ///
        keepusing(idauniq wave eidatey dveidates eidatlayy eidatlamm) ///
        keep(master match) gen(hcap_eol_merge)
    gen in_eol_hcap = (hcap_eol_merge == 3)
    drop hcap_eol_merge
    rename wave      hcap_last_productive_wave
    rename eidatey   hcap_death_year
    rename dveidates hcap_death_season
    rename eidatlayy hcap_last_ivw_year
    rename eidatlamm hcap_last_ivw_month

    foreach v in hcap_last_productive_wave hcap_death_year hcap_death_season ///
        hcap_last_ivw_year hcap_last_ivw_month {
        capture confirm numeric variable `v'
        if !_rc quietly replace `v' = . if `v' < 0
    }
}
else {
    gen in_eol_hcap = 0
    gen hcap_last_productive_wave = .
    gen hcap_death_year = .
    gen hcap_death_season = .
    gen hcap_last_ivw_year = .
    gen hcap_last_ivw_month = .
}

gen death_year_harm = .
replace death_year_harm = raxyear + 0.125 if raxseason == 1
replace death_year_harm = raxyear + 0.375 if raxseason == 2
replace death_year_harm = raxyear + 0.625 if raxseason == 3
replace death_year_harm = raxyear + 0.875 if raxseason == 4

gen death_year_hcap = .
replace death_year_hcap = hcap_death_year + 0.125 if hcap_death_season == 1
replace death_year_hcap = hcap_death_year + 0.375 if hcap_death_season == 2
replace death_year_hcap = hcap_death_year + 0.625 if hcap_death_season == 3
replace death_year_hcap = hcap_death_year + 0.875 if hcap_death_season == 4

count if !missing(death_year_hcap) & !missing(death_year_harm)
display "Deaths observed in both HCAP2 and harmonised EOL: " r(N)

* ELSA interview wave midpoint years (approximate — wave collection midpoints)
* Wave 2 = 2004-05 → 2004.5
* Wave 3 = 2006-07 → 2006.5
* Wave 4 = 2008-09 → 2008.5
* Wave 5 = 2010-11 → 2010.5
* Wave 6 = 2012-13 → 2012.5
* Wave 7 = 2014-15 → 2014.5
* Wave 8 = 2016-17 → 2016.5
* Wave 9 = 2018-19 → 2018.5
* Wave 10 = 2021-23 → 2022.0

gen died_wave_year = .
replace died_wave_year = 2004.5 if died_wave == 2
replace died_wave_year = 2006.5 if died_wave == 3
replace died_wave_year = 2008.5 if died_wave == 4
replace died_wave_year = 2010.5 if died_wave == 5
replace died_wave_year = 2012.5 if died_wave == 6
replace died_wave_year = 2014.5 if died_wave == 7
replace died_wave_year = 2016.5 if died_wave == 8
replace died_wave_year = 2018.5 if died_wave == 9
replace died_wave_year = 2022.0 if died_wave == 10

gen last_alive_year = .
replace last_alive_year = 2004.5 if last_alive_wave == 2
replace last_alive_year = 2006.5 if last_alive_wave == 3
replace last_alive_year = 2008.5 if last_alive_wave == 4
replace last_alive_year = 2010.5 if last_alive_wave == 5
replace last_alive_year = 2012.5 if last_alive_wave == 6
replace last_alive_year = 2014.5 if last_alive_wave == 7
replace last_alive_year = 2016.5 if last_alive_wave == 8
replace last_alive_year = 2018.5 if last_alive_wave == 9
replace last_alive_year = 2022.0 if last_alive_wave == 10

gen last_contact_year = .
replace last_contact_year = 2004.5 if last_contact_wave == 2
replace last_contact_year = 2006.5 if last_contact_wave == 3
replace last_contact_year = 2008.5 if last_contact_wave == 4
replace last_contact_year = 2010.5 if last_contact_wave == 5
replace last_contact_year = 2012.5 if last_contact_wave == 6
replace last_contact_year = 2014.5 if last_contact_wave == 7
replace last_contact_year = 2016.5 if last_contact_wave == 8
replace last_contact_year = 2018.5 if last_contact_wave == 9
replace last_contact_year = 2022.0 if last_contact_wave == 10

gen death_year_iwstat = (last_alive_year + died_wave_year) / 2 if !missing(died_wave_year)

gen death_year = death_year_hcap
replace death_year = death_year_harm if missing(death_year)
replace death_year = death_year_iwstat if missing(death_year)

gen death_source = .
replace death_source = 1 if !missing(death_year_hcap)
replace death_source = 2 if missing(death_year_hcap) & !missing(death_year_harm)
replace death_source = 3 if missing(death_year_hcap) & missing(death_year_harm) & !missing(death_year_iwstat)
label define deathsrc 1 "HCAP2 EOL" 2 "Harmonised EOL" 3 "iwstat midpoint"
label values death_source deathsrc

gen died = !missing(death_year)
tab death_source if died == 1, missing

count if died == 0 & last_contact_wave > last_alive_wave
display "Censored survivors with unknown/non-confirmed status after last alive wave: " r(N)

* For censored observations, stop at the last confirmed-alive wave.
gen exit_year = cond(died == 1, death_year, last_alive_year)
gen baseline_year = 2004.5
gen fu_years = exit_year - baseline_year

* Drop if no follow-up (died before / during baseline wave)
drop if fu_years <= 0 | missing(fu_years)

tab died
summarize fu_years, detail

*------------------------------------------------------------------------------
* 5. Apply Fancourt-style inclusion criteria
*------------------------------------------------------------------------------
* Complete data on exposure and core covariates
local covars "female white married edu4 wealth5 working poor_sight poor_hearing cesd r2psyche r2cancre r2lunge cvd_any other_ltc smoke_now alcfreq any_mobil any_adl any_iadl cog_mean"

gen complete = 1
replace complete = 0 if missing(arts3)
foreach v of local covars {
    replace complete = 0 if missing(`v')
}

*------------------------------------------------------------------------------
* 5a. Tabulate per-variable missingness in the wave-2 eligible pool
*     (post age-restriction, pre complete-case exclusion). Written to
*     output/tables/baseline_missingness.csv for the supplement template
*     to consume; respects the project rule that every manuscript claim
*     traces to a machine-readable output.
*------------------------------------------------------------------------------
local missvars "arts3 `covars'"
local n_eligible = _N

tempname mfh
file open `mfh' using "$out/tables/baseline_missingness.csv", write replace
file write `mfh' "variable,n_eligible,n_missing,pct_missing" _n
foreach v of local missvars {
    quietly count if missing(`v')
    local nmiss = r(N)
    local pct = string(100 * `nmiss' / `n_eligible', "%5.2f")
    file write `mfh' "`v',`n_eligible',`nmiss',`pct'" _n
}
file close `mfh'
display "Per-variable missingness written to $out/tables/baseline_missingness.csv"

keep if complete == 1
count
display "Final baseline sample: " r(N)

*------------------------------------------------------------------------------
* 6. Save baseline analytic file
*------------------------------------------------------------------------------
keep idauniq arts3 arts_freq scactc scactd scacta r2agey female white ///
     married edu4 wealth5 working poor_sight poor_hearing cesd r2psyche ///
     r2cancre r2lunge r2hearte r2stroke r2hibpe r2diabe r2arthre r2osteoe ///
     cvd_any other_ltc smoke_now alcfreq any_mobil any_adl any_iadl ///
     cog_mean r2proxy r2wtresp ///
     died death_year death_source fu_years baseline_year exit_year ///
     last_alive_wave last_interviewed_wave last_contact_wave died_wave ///
     in_eol_harm in_eol_hcap hcap_last_productive_wave ///
     hcap_last_ivw_year hcap_last_ivw_month

label data "Fancourt 2019 BMJ replication — wave 2 baseline analytic sample"
save "$data/fancourt_baseline.dta", replace

display "=============================================="
display "Baseline sample built and saved."
display "N = " _N
tab arts3, missing
display "Deaths: "
count if died == 1
display "=============================================="

log close
