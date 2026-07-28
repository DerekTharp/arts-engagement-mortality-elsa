*==============================================================================
* 06_tables.do
*
* Generates machine-readable tables for the manuscript:
*   - Table 1: Baseline characteristics by arts engagement category
*   - Supplementary: Arts engagement transition matrix across waves
*
* Table 2 (model comparison) is written by 05_msm_iptw.do, where the models
* are estimated, per the one-script-one-output standard.
*
* Outputs:
*   output/tables/table1.csv
*   output/tables/transitions.csv
*==============================================================================

capture log close
log using "$out/logs/06_tables.log", replace text

*------------------------------------------------------------------------------
* TABLE 1: Baseline characteristics by arts engagement category
*------------------------------------------------------------------------------
use "$data/fancourt_baseline.dta", clear

* Age categories (matching Fancourt's Table 1 bins)
gen agecat = .
replace agecat = 1 if r2agey >= 50 & r2agey < 60
replace agecat = 2 if r2agey >= 60 & r2agey < 70
replace agecat = 3 if r2agey >= 70 & r2agey < 80
replace agecat = 4 if r2agey >= 80 & !missing(r2agey)
label define agecatlbl 1 "50-59" 2 "60-69" 3 "70-79" 4 "80+"
label values agecat agecatlbl

* Open CSV for Table 1
tempname fh
file open `fh' using "$out/tables/table1.csv", write replace

file write `fh' "Variable,Level,Never (N=),Never %,Infrequent (N=),Infrequent %,Frequent (N=),Frequent %,Total (N=),Total %" _n

* Column Ns
foreach cat in 0 1 2 {
    count if arts3 == `cat'
    local n_`cat' = r(N)
}
count
local n_total = r(N)

file write `fh' "N,," (`n_0') ",," (`n_1') ",," (`n_2') ",," (`n_total') "," _n

* --- Continuous: Age ---
foreach cat in 0 1 2 {
    summarize r2agey if arts3 == `cat'
    local mean_`cat' = string(r(mean), "%4.1f")
    local sd_`cat'   = string(r(sd), "%4.1f")
}
summarize r2agey
local mean_t = string(r(mean), "%4.1f")
local sd_t   = string(r(sd), "%4.1f")
file write `fh' "Age (mean (SD)),," (`n_0') ",`mean_0' (`sd_0')," (`n_1') ",`mean_1' (`sd_1')," (`n_2') ",`mean_2' (`sd_2')," (`n_total') ",`mean_t' (`sd_t')" _n

* --- Age categories ---
foreach cat in 0 1 2 {
    forvalues a = 1/4 {
        count if agecat == `a' & arts3 == `cat'
        local n = r(N)
        local pct = string(100 * `n' / `n_`cat'', "%4.1f")
        local age`a'_n_`cat' = `n'
        local age`a'_p_`cat' = "`pct'"
    }
}
forvalues a = 1/4 {
    count if agecat == `a'
    local n = r(N)
    local pct = string(100 * `n' / `n_total', "%4.1f")
    local age`a'_n_t = `n'
    local age`a'_p_t = "`pct'"
}
local agelabels `" "50-59" "60-69" "70-79" "80+" "'
forvalues a = 1/4 {
    local lab : word `a' of `agelabels'
    file write `fh' "Age group,`lab'," (`age`a'_n_0') ",`age`a'_p_0'," (`age`a'_n_1') ",`age`a'_p_1'," (`age`a'_n_2') ",`age`a'_p_2'," (`age`a'_n_t') ",`age`a'_p_t'" _n
}

* --- Binary variable rows ---
* Write each directly (Stata programs cannot access caller's locals)
foreach varname in female white married working cvd_any r2cancre r2lunge r2psyche any_mobil any_adl any_iadl poor_sight poor_hearing smoke_now {
    local lab = "`varname'"
    if "`varname'" == "female"       local lab "Female"
    if "`varname'" == "white"        local lab "White"
    if "`varname'" == "married"      local lab "Married/cohabiting"
    if "`varname'" == "working"      local lab "Employed"
    if "`varname'" == "cvd_any"      local lab "CVD (any)"
    if "`varname'" == "r2cancre"     local lab "Cancer"
    if "`varname'" == "r2lunge"      local lab "Lung disease"
    if "`varname'" == "r2psyche"     local lab "Psychiatric condition"
    if "`varname'" == "any_mobil"    local lab "Any mobility limitation"
    if "`varname'" == "any_adl"      local lab "Any ADL limitation"
    if "`varname'" == "any_iadl"     local lab "Any IADL limitation"
    if "`varname'" == "poor_sight"   local lab "Poor eyesight"
    if "`varname'" == "poor_hearing" local lab "Poor hearing"
    if "`varname'" == "smoke_now"    local lab "Current smoker"

    foreach cat in 0 1 2 {
        count if `varname' == 1 & arts3 == `cat'
        local bn_`cat' = r(N)
        local bp_`cat' = string(100 * r(N) / `n_`cat'', "%4.1f")
    }
    count if `varname' == 1
    local bn_t = r(N)
    local bp_t = string(100 * r(N) / `n_total', "%4.1f")
    file write `fh' "`lab',," (`bn_0') ",`bp_0'," (`bn_1') ",`bp_1'," (`bn_2') ",`bp_2'," (`bn_t') ",`bp_t'" _n
}

* Education categories
foreach cat in 0 1 2 {
    forvalues e = 1/4 {
        count if edu4 == `e' & arts3 == `cat'
        local n = r(N)
        local pct = string(100 * `n' / `n_`cat'', "%4.1f")
        local edu`e'_n_`cat' = `n'
        local edu`e'_p_`cat' = "`pct'"
    }
}
forvalues e = 1/4 {
    count if edu4 == `e'
    local n = r(N)
    local pct = string(100 * `n' / `n_total', "%4.1f")
    local edu`e'_n_t = `n'
    local edu`e'_p_t = "`pct'"
}
local edulabels `" "No qualification" "Age-16 qualification" "Age-18 qualification" "Degree" "'
forvalues e = 1/4 {
    local lab : word `e' of `edulabels'
    file write `fh' "Education,`lab'," (`edu`e'_n_0') ",`edu`e'_p_0'," (`edu`e'_n_1') ",`edu`e'_p_1'," (`edu`e'_n_2') ",`edu`e'_p_2'," (`edu`e'_n_t') ",`edu`e'_p_t'" _n
}

* Continuous: CESD, cognition
foreach cat in 0 1 2 {
    summarize cesd if arts3 == `cat'
    local cesd_mean_`cat' = string(r(mean), "%4.1f")
    local cesd_sd_`cat'   = string(r(sd), "%4.1f")
    summarize cog_mean if arts3 == `cat'
    local cog_mean_`cat' = string(r(mean), "%5.2f")
    local cog_sd_`cat'   = string(r(sd), "%5.2f")
}
summarize cesd
local cesd_mean_t = string(r(mean), "%4.1f")
local cesd_sd_t   = string(r(sd), "%4.1f")
summarize cog_mean
local cog_mean_t = string(r(mean), "%5.2f")
local cog_sd_t   = string(r(sd), "%5.2f")

file write `fh' "CES-D (mean (SD)),," (`n_0') ",`cesd_mean_0' (`cesd_sd_0')," (`n_1') ",`cesd_mean_1' (`cesd_sd_1')," (`n_2') ",`cesd_mean_2' (`cesd_sd_2')," (`n_total') ",`cesd_mean_t' (`cesd_sd_t')" _n
file write `fh' "Cognition z-score (mean (SD)),," (`n_0') ",`cog_mean_0' (`cog_sd_0')," (`n_1') ",`cog_mean_1' (`cog_sd_1')," (`n_2') ",`cog_mean_2' (`cog_sd_2')," (`n_total') ",`cog_mean_t' (`cog_sd_t')" _n

* Mortality outcome
foreach cat in 0 1 2 {
    count if died == 1 & arts3 == `cat'
    local n = r(N)
    local pct = string(100 * `n' / `n_`cat'', "%4.1f")
    local died_n_`cat' = `n'
    local died_p_`cat' = "`pct'"
}
count if died == 1
local n = r(N)
local pct = string(100 * `n' / `n_total', "%4.1f")
file write `fh' "Died during follow-up,," (`died_n_0') ",`died_p_0'," (`died_n_1') ",`died_p_1'," (`died_n_2') ",`died_p_2'," (`n') ",`pct'" _n

* Follow-up years
foreach cat in 0 1 2 {
    summarize fu_years if arts3 == `cat'
    local fu_mean_`cat' = string(r(mean), "%4.1f")
    local fu_sd_`cat'   = string(r(sd), "%4.1f")
}
summarize fu_years
local fu_mean_t = string(r(mean), "%4.1f")
local fu_sd_t   = string(r(sd), "%4.1f")
file write `fh' "Follow-up years (mean (SD)),," (`n_0') ",`fu_mean_0' (`fu_sd_0')," (`n_1') ",`fu_mean_1' (`fu_sd_1')," (`n_2') ",`fu_mean_2' (`fu_sd_2')," (`n_total') ",`fu_mean_t' (`fu_sd_t')" _n

file close `fh'
display "Table 1 written to $out/tables/table1.csv"

* Table 2 and weight diagnostics are written by 05_msm_iptw.do
* (single source of truth for all model estimates)

*------------------------------------------------------------------------------
* SUPPLEMENTARY: Arts engagement transition matrix across waves
*------------------------------------------------------------------------------
use "$data/fancourt_panel.dta", clear

* Lagged exposure
sort idauniq wave
by idauniq: gen arts3_prev = arts3[_n-1]

* Keep only rows where both current and previous are genuinely observed
* (under monotone censoring, all panel rows are observed, but this guard
* makes the requirement explicit and protects against future panel changes)
keep if !missing(arts3) & !missing(arts3_prev) & observed == 1

tempname fh3
file open `fh3' using "$out/tables/transitions.csv", write replace
file write `fh3' "From,To,N,Pct_of_from" _n

* Transition counts
forvalues from = 0/2 {
    count if arts3_prev == `from'
    local n_from = r(N)
    forvalues to = 0/2 {
        count if arts3_prev == `from' & arts3 == `to'
        local n = r(N)
        local pct = string(100 * `n' / `n_from', "%4.1f")
        local fromlbl = cond(`from' == 0, "Never", cond(`from' == 1, "Infrequent", "Frequent"))
        local tolbl   = cond(`to'   == 0, "Never", cond(`to'   == 1, "Infrequent", "Frequent"))
        file write `fh3' "`fromlbl',`tolbl',`n',`pct'" _n
    }
}

file close `fh3'
display "Transition matrix written to $out/tables/transitions.csv"

log close
