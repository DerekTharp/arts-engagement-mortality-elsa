*==============================================================================
* 07_figures.do
*
* Forest plot comparing HR estimates for frequent arts engagement vs never
* across all model specifications. Visual companion to main-text Table 1 (the
* model ladder), included as Supplementary Figure S3. The main-text figures are
* the DAG (Figure 1) and the balance love plot (Figure 2, make_balance_figure.py).
*
* Output: output/figures/figure_s3_model_ladder.png
*==============================================================================

capture log close
log using "$out/logs/07_figures.log", replace text

*------------------------------------------------------------------------------
* Read Table 2 CSV and build the plot dataset
*------------------------------------------------------------------------------
import delimited "$out/tables/table2.csv", clear varnames(1)

keep if exposure == "Frequent"

gen order = .
replace order = 7 if model == "Baseline-fixed Cox"
replace order = 6 if model == "Time-varying Cox"
replace order = 5 if model == "Baseline-fixed cloglog (panel)"
replace order = 4 if model == "Unweighted discrete-time PH"
replace order = 3 if model == "Concurrent-confounder-adjusted PH"
replace order = 2 if model == "MSM IPTW+IPCW cloglog"

destring hr ci_low ci_high, replace

* Add Fancourt's published estimate as reference
local newobs = _N + 1
set obs `newobs'
replace model    = "Fancourt 2019 (published)" in `newobs'
replace exposure = "Frequent"                   in `newobs'
replace hr    = 0.69                         in `newobs'
replace ci_low   = 0.59                         in `newobs'
replace ci_high  = 0.80                         in `newobs'
replace metric   = "HR"                         in `newobs'
replace order    = 8                            in `newobs'

* Estimate label (HR value with CI)
gen est_label = string(hr, "%4.2f") + " (" + string(ci_low, "%4.2f") + "-" + string(ci_high, "%4.2f") + ")"

* Forest plot with labels
twoway (rcap ci_low ci_high order, horizontal lcolor(gs4) lwidth(medium)) ///
       (scatter order hr, msymbol(diamond) msize(medlarge) mcolor(navy) ///
            mlabel(est_label) mlabposition(12) mlabsize(vsmall) mlabcolor(maroon) mlabgap(1.5)) ///
       , xline(1, lcolor(gs10) lpattern(dash)) ///
         xlabel(0.4(0.1)1.1, format(%3.1f) labsize(small)) ///
         yscale(range(0.5 9.2)) ///
         ylabel(1 " " ///
                2 `" "MSM" "(IPTW+IPCW)" "' ///
                3 `" "Naive confounder-" "adjusted PH" "' ///
                4 `" "Unweighted" "discrete-time PH" "' ///
                5 `" "Baseline-fixed" "cloglog (panel)" "' ///
                6 `" "Time-varying" "Cox" "' ///
                7 `" "Baseline-fixed" "Cox (full sample)" "' ///
                8 `" "Fancourt 2019" "(published)" "', ///
                angle(0) labsize(small) nogrid) ///
         xtitle("Hazard ratio (frequent vs never)", size(small)) ///
         ytitle("") ///
         title("Arts engagement and mortality: model comparison", size(medium)) ///
         subtitle("Frequent engagement vs never, all models adjusted", size(small)) ///
         note("Adjusted hazard ratios; error bars are 95% confidence intervals." ///
              "The four discrete-time panel models share one monotone-censored sample.", size(vsmall)) ///
         legend(off) ///
         graphregion(color(white)) plotregion(margin(l=2 r=2)) ///
         scheme(s2color) ///
         name(forest_labeled, replace)

graph export "$out/figures/figure_s3_model_ladder.png", name(forest_labeled) replace width(1600)

display "Supplementary Figure S3 written to $out/figures/figure_s3_model_ladder.png"

log close
