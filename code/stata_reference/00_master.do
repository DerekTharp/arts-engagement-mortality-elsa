*==============================================================================
* 00_master.do — 26.46 Arts Engagement Replication (JECH)
*
* Reproduces Fancourt & Steptoe 2019 (BMJ 367:l6377) baseline Cox model and
* extends it with time-varying exposure and marginal structural models.
*
* To reproduce from scratch, set ONE path: edit `global proj` below to the
* directory holding this project (the parent of code/, data/, output/, and the
* ELSA data folder), then run:
*     stata-mp -b do code/stata_reference/00_master.do
*
* This is the validated historical reference. The production pipeline is
* Python (`python3 code/run_all.py`).
*==============================================================================

clear all
set more off
set maxvar 32000

*---- paths --------------------------------------------------------------------
* Single editable root; everything else is derived from it. Defaults to the
* current directory, so running this from the repository root works as-is.
* Set an absolute path here if you run from elsewhere.
global proj      "."

global elsa_root "$proj/ELSA (English Longitudinal Study of Aging)/UKDA-5050-stata"
global pgs_root  "$proj/ELSA (English Longitudinal Study of Aging)/UKDA-8773-stata/UKDA-8773-stata/stata/stata13"
global waves     "$elsa_root/stata/stata13_se"
global harm      "$elsa_root/stata/stata13_se/gh_elsa_h.dta"
global eol       "$elsa_root/stata/stata13_se/h_elsa_eol_a2.dta"
global eol_w6    "$elsa_root/stata/stata13_se/elsa_endoflife_w6archive.dta"
global eol_w10   "$elsa_root/stata/stata13_se/elsa_endoflife_hcap2_w10.dta"
global data      "$proj/data"
global out       "$proj/output"

capture mkdir "$data"
capture mkdir "$out"
capture mkdir "$out/logs"
capture mkdir "$out/tables"
capture mkdir "$out/figures"

*---- verify data present ------------------------------------------------------
capture confirm file "$harm"
if _rc {
    display as error "Harmonised ELSA file not found at $harm"
    display as error "Edit global proj at the top of 00_master.do"
    exit 601
}

*---- pipeline -----------------------------------------------------------------
do "code/stata_reference/01_build_sample.do"
do "code/stata_reference/02_cox_replication.do"
do "code/stata_reference/03_build_panel.do"
do "code/stata_reference/04_time_varying_cox.do"
do "code/stata_reference/05_msm_iptw.do"
do "code/stata_reference/06_tables.do"
do "code/stata_reference/07_figures.do"
do "code/stata_reference/08_pgs_sensitivity.do"
do "code/stata_reference/09_death_undercount_sensitivity.do"

*---- regenerate DAG, balance love plot, STROBE flow, and undercount figures ---
shell python3 "code/make_dag.py"
shell python3 "code/make_balance_figure.py"
shell python3 "code/make_flow_diagram.py"
shell python3 "code/make_undercount_figure.py"

display "=============================================="
display "Master pipeline complete."
display "All results are in output/tables/ (CSV) and output/figures/ (PNG)."
display "=============================================="
