*==============================================================================
* 08_pgs_sensitivity.do
*
* Polygenic score sensitivity analyses for the arts-mortality association.
*
* Uses ELSA PGS dataset (UK Data Service study 8773) to:
*   1. Test whether PGS for educational attainment (EA_3) predicts arts
*      engagement after measured-covariate adjustment — confirms genetic
*      social patterning operates through but beyond measured covariates.
*   2. Add PGS-education to the baseline-fixed Cox and check whether the
*      arts engagement HR attenuates — direct test of genetic/social
*      confounding as the mechanism Wright (2020) flagged.
*   3. PGS-height as negative control — genetic analogue of Wright's
*      measured-height negative control outcome test.
*
* All PGS models include the first 10 genetic principal components to
* control for population stratification, and restrict to participants
* with European ancestry (the reference population for the GWAS).
*
* Output: output/tables/table_pgs.csv
*==============================================================================

capture log close
log using "$out/logs/08_pgs_sensitivity.log", replace text

*------------------------------------------------------------------------------
* 1. Merge PGS and principal components with baseline sample
*------------------------------------------------------------------------------
use "$data/fancourt_baseline.dta", clear

* PGS path: configured via $pgs_root in 00_master.do, with a fallback to a
* relative path so this script remains runnable from a clean project root.
local pgs_path "$pgs_root"
capture confirm file "`pgs_path'/list_pgs_scores_elsa_2022.dta"
if _rc {
    local pgs_path "ELSA (English Longitudinal Study of Aging)/UKDA-8773-stata/UKDA-8773-stata/stata/stata13"
    capture confirm file "`pgs_path'/list_pgs_scores_elsa_2022.dta"
    if _rc {
        display as error "Cannot locate ELSA PGS file. Set \$pgs_root in 00_master.do."
        exit 601
    }
}

merge 1:1 idauniq using "`pgs_path'/list_pgs_scores_elsa_2022.dta", ///
    keepusing(EA_3 Height GC_2018 SEC_DEP) ///
    keep(master match) nogen

merge 1:1 idauniq using "`pgs_path'/principal_components_elsa_2022.dta", ///
    keepusing(pc1-pc10) keep(master match) nogen

* Count how many baseline participants have PGS data
gen has_pgs = !missing(EA_3)
tab has_pgs
count if has_pgs == 1
display "Baseline sample with PGS: " r(N)
display "Baseline sample without PGS: " _N - r(N)

* Restrict to genotyped sample
keep if has_pgs == 1

* Restrict to white British / European ancestry (reference population for
* the GWAS summary statistics used to construct these PGS). ELSA is ~95%
* white; this drops the small non-white subsample for whom PGS are not
* well calibrated.
count if white == 0
display "Non-white participants dropped from PGS sample: " r(N)
keep if white == 1

* Standardise PGS for interpretability (1-SD units)
foreach v in EA_3 Height GC_2018 SEC_DEP {
    egen z_`v' = std(`v')
}

*------------------------------------------------------------------------------
* 2. Reference: baseline-fixed Cox WITHOUT PGS (genotyped subsample)
*------------------------------------------------------------------------------
gen entry_age = r2agey
gen exit_age  = r2agey + fu_years
stset exit_age, failure(died==1) enter(time entry_age) origin(time 0)

display _newline "=== Model 0: Baseline-fixed Cox, genotyped subsample (no PGS) ==="
stcox ib0.arts3 i.female i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean, nolog

local n_ref = e(N)
local d_ref = e(N_fail)

* Store reference HRs
foreach lev in 1 2 {
    local hr0_`lev'    = exp(_b[`lev'.arts3])
    local ci0_lo_`lev' = exp(_b[`lev'.arts3] - 1.96 * _se[`lev'.arts3])
    local ci0_hi_`lev' = exp(_b[`lev'.arts3] + 1.96 * _se[`lev'.arts3])
}

*------------------------------------------------------------------------------
* 3. Add PGS-education (EA_3) to baseline Cox
*------------------------------------------------------------------------------
display _newline "=== Model 1: Baseline-fixed Cox + PGS-education + 10 PCs ==="
stcox ib0.arts3 i.female i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    z_EA_3 pc1-pc10, nolog

local n_ea = e(N)
local d_ea = e(N_fail)

foreach lev in 1 2 {
    local hr1_`lev'    = exp(_b[`lev'.arts3])
    local ci1_lo_`lev' = exp(_b[`lev'.arts3] - 1.96 * _se[`lev'.arts3])
    local ci1_hi_`lev' = exp(_b[`lev'.arts3] + 1.96 * _se[`lev'.arts3])
}

* PGS-education effect on mortality
local hr_ea    = exp(_b[z_EA_3])
local ci_ea_lo = exp(_b[z_EA_3] - 1.96 * _se[z_EA_3])
local ci_ea_hi = exp(_b[z_EA_3] + 1.96 * _se[z_EA_3])
display "PGS-education HR per SD: " string(`hr_ea', "%5.3f") ///
    " (" string(`ci_ea_lo', "%5.3f") "-" string(`ci_ea_hi', "%5.3f") ")"

*------------------------------------------------------------------------------
* 4. Add PGS-education + PGS-cognition + PGS-social deprivation
*------------------------------------------------------------------------------
display _newline "=== Model 2: Baseline-fixed Cox + PGS-education + PGS-cognition + PGS-deprivation + 10 PCs ==="
stcox ib0.arts3 i.female i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    z_EA_3 z_GC_2018 z_SEC_DEP pc1-pc10, nolog

local n_multi = e(N)
local d_multi = e(N_fail)

foreach lev in 1 2 {
    local hr2_`lev'    = exp(_b[`lev'.arts3])
    local ci2_lo_`lev' = exp(_b[`lev'.arts3] - 1.96 * _se[`lev'.arts3])
    local ci2_hi_`lev' = exp(_b[`lev'.arts3] + 1.96 * _se[`lev'.arts3])
}

*------------------------------------------------------------------------------
* 5. PGS-education predicting arts engagement (multinomial logit)
*    Does genetic social advantage predict cultural engagement after
*    adjusting for measured education, wealth, cognition?
*------------------------------------------------------------------------------
display _newline "=== PGS-education predicting arts engagement (ordered logit) ==="
ologit arts3 z_EA_3 c.r2agey##c.r2agey i.female i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    pc1-pc10, nolog

display _newline "PGS-education coefficient in ordered logit for arts engagement:"
display "  Coeff: " string(_b[z_EA_3], "%6.4f") " (SE " string(_se[z_EA_3], "%6.4f") ")"
display "  OR per SD: " string(exp(_b[z_EA_3]), "%5.3f")

* Capture the ordered-logit OR + 95% CI + p-value for table_pgs.csv so the
* manuscript build no longer needs to parse the log file.
local pgs_arts_or    = string(exp(_b[z_EA_3]), "%5.3f")
local pgs_arts_or_lo = string(exp(_b[z_EA_3] - 1.96 * _se[z_EA_3]), "%5.3f")
local pgs_arts_or_hi = string(exp(_b[z_EA_3] + 1.96 * _se[z_EA_3]), "%5.3f")
local pgs_arts_z     = _b[z_EA_3] / _se[z_EA_3]
local pgs_arts_p     = string(2 * (1 - normal(abs(`pgs_arts_z'))), "%6.4f")

*------------------------------------------------------------------------------
* 6. PGS-height as negative control outcome (genetic Wright test)
*    Wright showed measured height is associated with arts engagement
*    after covariate adjustment — a result that should not occur if the
*    adjustment set is sufficient, since arts cannot cause height.
*    We replicate this genetically: does arts engagement predict PGS-height
*    after full covariate adjustment? If yes, genetic social patterning
*    linked to height is not absorbed by the measured covariates.
*------------------------------------------------------------------------------
display _newline "=== Negative control outcome: arts engagement predicting PGS-height ==="
regress z_Height ib0.arts3 c.r2agey##c.r2agey i.female i.married i.edu4 i.wealth5 i.working ///
    i.poor_sight i.poor_hearing cesd i.r2psyche ///
    i.r2cancre i.r2lunge i.cvd_any i.other_ltc ///
    i.smoke_now alcfreq i.any_mobil i.any_adl i.any_iadl cog_mean ///
    pc1-pc10

local ht_coeff_1 = string(_b[1.arts3], "%6.4f")
local ht_coeff_2 = string(_b[2.arts3], "%6.4f")
local ht_se_1    = _se[1.arts3]
local ht_se_2    = _se[2.arts3]
local ht_p_1     = string(2 * ttail(e(df_r), abs(_b[1.arts3] / _se[1.arts3])), "%5.3f")
local ht_p_2     = string(2 * ttail(e(df_r), abs(_b[2.arts3] / _se[2.arts3])), "%5.3f")
display "Arts engagement coefficients on PGS-height (SD units):"
display "  Infrequent vs never: " `ht_coeff_1' " (p=" `ht_p_1' ")"
display "  Frequent vs never:   " `ht_coeff_2' " (p=" `ht_p_2' ")"

*------------------------------------------------------------------------------
* 7. Write results to CSV
*------------------------------------------------------------------------------
tempname fh
file open `fh' using "$out/tables/table_pgs.csv", write replace
file write `fh' "Model,Exposure,HR,CI_low,CI_high,N,Deaths,Note" _n

* Reference (no PGS)
foreach lev in 1 2 {
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "Cox (no PGS; genotyped),`explab'," ///
        (string(`hr0_`lev'', "%5.2f")) "," ///
        (string(`ci0_lo_`lev'', "%5.2f")) "," ///
        (string(`ci0_hi_`lev'', "%5.2f")) "," ///
        (`n_ref') "," (`d_ref') ",Reference" _n
}

* + PGS-education
foreach lev in 1 2 {
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "Cox + PGS-education,`explab'," ///
        (string(`hr1_`lev'', "%5.2f")) "," ///
        (string(`ci1_lo_`lev'', "%5.2f")) "," ///
        (string(`ci1_hi_`lev'', "%5.2f")) "," ///
        (`n_ea') "," (`d_ea') ",+ EA_3 + 10 PCs" _n
}

* + PGS-education + cognition + deprivation
foreach lev in 1 2 {
    local explab = cond(`lev' == 1, "Infrequent", "Frequent")
    file write `fh' "Cox + PGS-education/cognition/deprivation,`explab'," ///
        (string(`hr2_`lev'', "%5.2f")) "," ///
        (string(`ci2_lo_`lev'', "%5.2f")) "," ///
        (string(`ci2_hi_`lev'', "%5.2f")) "," ///
        (`n_multi') "," (`d_multi') ",+ EA_3 + GC_2018 + SEC_DEP + 10 PCs" _n
}

* PGS own effects (formatted consistently with other rows)
file write `fh' "PGS-education own effect,," ///
    (string(`hr_ea', "%5.2f")) "," ///
    (string(`ci_ea_lo', "%5.2f")) "," ///
    (string(`ci_ea_hi', "%5.2f")) "," ///
    (`n_ea') "," (`d_ea') ",HR per SD" _n

* PGS-education effect on arts engagement (ordered-logit OR per SD).
* Reported here so the manuscript builder can pick it up without parsing logs.
file write `fh' "PGS-education predicting arts engagement,,`pgs_arts_or',`pgs_arts_or_lo',`pgs_arts_or_hi',`n_ea',,OR per SD (ordered logit; p=`pgs_arts_p')" _n

* PGS-height negative control (separate columns: Coeff, SE, P-value)
file write `fh' "" _n
file write `fh' "PGS-height negative control (arts predicting genetic height)" _n
file write `fh' "Exposure,Coeff_SD,SE,P_value,Note" _n
file write `fh' "Infrequent vs never,`ht_coeff_1'," (string(`ht_se_1', "%6.4f")) ",`ht_p_1',OLS regression of z_Height on arts3" _n
file write `fh' "Frequent vs never,`ht_coeff_2'," (string(`ht_se_2', "%6.4f")) ",`ht_p_2',OLS regression of z_Height on arts3" _n

file close `fh'
display _newline "PGS results written to $out/tables/table_pgs.csv"

*------------------------------------------------------------------------------
* Summary display
*------------------------------------------------------------------------------
display _newline "=============================================="
display "PGS Sensitivity Analysis Summary"
display "=============================================="
display "Genotyped subsample: N=" (`n_ref') ", deaths=" (`d_ref')
display ""
display "Frequent vs never:"
display "  No PGS:                HR " string(`hr0_2', "%5.2f") " (" string(`ci0_lo_2', "%5.2f") "-" string(`ci0_hi_2', "%5.2f") ")"
display "  + PGS-education:      HR " string(`hr1_2', "%5.2f") " (" string(`ci1_lo_2', "%5.2f") "-" string(`ci1_hi_2', "%5.2f") ")"
display "  + PGS-edu/cog/dep:    HR " string(`hr2_2', "%5.2f") " (" string(`ci2_lo_2', "%5.2f") "-" string(`ci2_hi_2', "%5.2f") ")"
display ""
display "PGS-education own effect: HR " string(`hr_ea', "%5.3f") " per SD"
display "PGS-height negative control (arts -> PGS-height):"
display "  Infrequent vs never: coeff " `ht_coeff_1' " (p=" `ht_p_1' ")"
display "  Frequent vs never:   coeff " `ht_coeff_2' " (p=" `ht_p_2' ")"
display "=============================================="

log close
