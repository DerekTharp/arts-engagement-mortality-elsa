# STROBE Statement — Checklist of items for cohort studies

Tharp D. Checking that the weights worked: a tutorial on balance diagnostics for marginal structural models, using arts engagement and mortality in the English Longitudinal Study of Ageing.

This is a Theory and Methods paper: it develops and demonstrates balance diagnostics for marginal structural models, using an observational cohort analysis (arts engagement and mortality in ELSA) as the worked example. The STROBE items below are completed for that underlying cohort analysis. Locators are given by manuscript section (and supplement section/figure), which are robust to typeset pagination.

| Item No | Recommendation | Location | Comment |
|---------|---------------|---------|---------|
| **Title and abstract** | | | |
| 1 | (a) Indicate study design in title or abstract | Title; Abstract | Title names the data source (ELSA) and the design (marginal structural models); Abstract Methods states the worked example is a public-data reconstruction analysed with a ladder of models from baseline-fixed to a stabilised IPTW-IPCW MSM |
| | (b) Informative and balanced summary | Abstract | Structured, standalone abstract (Background, Methods, Results, Conclusion); {abstract_word_count} words; assumes no prior knowledge of the cited papers |
| **Introduction** | | | |
| 2 | Scientific background and rationale | Introduction | The general problem (time-varying confounding affected by prior exposure when an exposure tracks health), the limitations of baseline-fixed and concurrent-adjusted time-varying models under the stated causal structure, and the studies motivating the worked example |
| 3 | Specific objectives | Introduction, final paragraph | To demonstrate how to fit and diagnose an MSM for a health-tracking exposure, and to show why balance must condition on all variables retained by a stabilised-weight numerator |
| **Methods** | | | |
| 4 | Study design | Methods: example/data; model ladder | Biennial cohort (ELSA waves 2–10) analysed with baseline-fixed Cox, time-varying discrete-time proportional-hazards models, a concurrent-adjusted model, and a stabilised IPTW-IPCW marginal structural model |
| 5 | Setting, locations, relevant dates | Methods: example/data | ELSA, adults aged {baseline_min_age}+ in England, biennial since 2002; wave-2 baseline 2004–05; data from UK Data Service studies 5050 (Gateway Harmonized ELSA, Version H) and 8773 (genetic polygenic scores) |
| 6 | (a) Eligibility; selection; follow-up | Methods: example/data; Suppl §S6, Fig S1 | Wave-2 respondents aged {baseline_min_age}+ with complete arts engagement and covariates (N={n_baseline}); monotone-censored person-wave panel ({n_panel_intervals} outcome-model intervals). Flow and missingness in Supplement §S6 and Figure S1 |
| | (b) Matched studies | n/a | Not a matched cohort |
| 7 | Outcomes, exposures, confounders defined | Methods: example/data; causal structure | All-cause mortality (iwstat transitions + wave-10 end-of-life proxy interviews); three-category receptive arts engagement (never/infrequent/frequent); time-varying confounders L_t and the baseline covariate set defined in “The causal structure” and Supplement §S3 |
| 8 | Data sources / measurement | Methods: example/data; Suppl §S3, §S5 | Survey variables from Gateway Harmonized ELSA; arts items from self-completion modules at each wave; mortality from iwstat codes 5/6 plus wave-10 end-of-life interviews; PGS variables from UK Data Service study 8773 (Suppl §S5) |
| 9 | Efforts to address bias | Methods: causal structure; weight diagnosis; Suppl §S1–S2, §S5, §S7 | DAG and MSM rationale; IPTW for time-varying confounding affected by prior exposure; IPCW for informative attrition; numerator-conditioned balance diagnostics for both exposure contrasts; PGS and negative-control-outcome probes; terminal-censoring, weight-truncation/positivity, and death-undercount sensitivity checks |
| 10 | Study size | Methods: example/data; Suppl §S6 | N={n_baseline} baseline; {n_panel_intervals} person-wave intervals and {n_panel_deaths} deaths in the outcome-model panel; N={n_pgs_sample} genotyped participants for the PGS probe |
| 11 | Quantitative variables — handling | Methods: example/data; model ladder; Suppl §S2, §S5 | Three-category exposure with stated bands; age modelled quadratically with interval length as an offset; weight diagnostics/positivity in Suppl §S2; standardised PGS and {n_pgs_pcs} genetic PCs in Suppl §S5 |
| 12 | (a) Statistical methods / confounder control | Methods: model ladder; weight diagnosis | Baseline-fixed Cox; time-varying and concurrent-adjusted discrete-time proportional-hazards models; stabilised IPTW-IPCW MSM (multinomial treatment model, logistic censoring model); cluster-robust SEs |
| | (b) Subgroups/interactions | Results: weight diagnosis | Balance assessed within strata of prior-wave exposure and regression-adjusted for the other numerator covariates (the paper's central diagnostic), not an effect-modification analysis |
| | (c) Missing data | Methods: example/data; Suppl §S6 | Complete-case for baseline covariates; informative attrition handled by the IPCW component; per-variable missingness in Suppl §S6 |
| | (d) Loss to follow-up | Methods: example/data; Suppl §S1 | Monotone censoring from the first wave of non-interview or incomplete self-completion; terminal-censoring sensitivity in Suppl §S1 |
| | (e) Sensitivity analyses | Suppl §S1–S2, §S5, §S7 | Terminal-censoring, weight-truncation, positivity, PGS, and two-sided death-undercount analyses |
| **Results** | | | |
| 13 | (a) Numbers at each stage | Suppl §S6, Fig S1 | Wave-2 eligible → analytic sample N={n_baseline} → panel {n_panel_pre_weight} intervals → {n_panel_intervals} in outcome model ({n_missing_weight} excluded for missing weight-model inputs) |
| | (b) Non-participation | Suppl §S6 | Complete-case exclusion dominated by missing self-completion arts items; panel excludes waves after first non-interview/incomplete self-completion |
| | (c) Flow diagram | Suppl Fig S1 | Provided as supplementary Figure S1 |
| 14 | (a) Characteristics of participants | Suppl §S3, Table S3 | Baseline characteristics by arts-engagement category (Supplementary Table S3) |
| | (b) Missing data per variable | Suppl §S6 | Per-variable baseline missingness tabulated |
| | (c) Follow-up time | Suppl §S3, Table S3 | Follow-up years by baseline exposure category in Table S3 |
| 15 | Outcome events | Results: model ladder; Table 1; Suppl Table S3 | Table 1 reports deaths in each panel; the full baseline-fixed sample has {n_deaths_baseline} deaths, the outcome-model panel {n_panel_deaths}, the genotyped subsample {n_pgs_deaths} |
| 16 | (a) Adjusted estimates with precision | Results: model ladder; Table 1 | Table 1 gives adjusted HRs with 95% CIs for the four common-panel specifications; two auxiliary Cox models are in Suppl §S3 |
| | (b) Category boundaries | Methods: example/data | never / infrequent (once or twice a year, or less) / frequent (every few months or more) |
| | (c) Absolute risk | Suppl Table S3 | Crude mortality by baseline exposure category (Table S3); model estimates retained on the HR scale for comparability |
| 17 | Other analyses | Results: weight diagnosis; Table 2; Fig 2; Suppl §S1–S2, §S5, §S7 | Numerator-conditioned balance diagnostics for frequent-versus-never and infrequent-versus-never exposure (Table 2, Figure 2); PGS and negative-control-outcome probe; terminal-censoring, weight-truncation, positivity, and death-undercount analyses |
| **Discussion** | | | |
| 18 | Key results | Discussion, opening paragraph | Estimate ladder {hr_bfcl_frequent} → {or_uwt_frequent} → MSM {or_msm_frequent}; the balance diagnostic, not the point estimate, carries the inference |
| 19 | Limitations | Discussion | Mortality-endpoint gap ({n_deaths_baseline} vs {published_deaths} deaths); biennial measurement missing terminal decline; monotone-censoring selection; MSM no-unmeasured-confounding assumption; survey weights not applied |
| 20 | Interpretation | Discussion | Weighting improved adjusted balance in common transitions but left residual imbalance in sparse boundary comparisons; measured balance does not rule out unmeasured baseline social patterning or interim health decline |
| 21 | Generalisability | Discussion | Estimates describe the analytic cohort rather than the English population aged {baseline_min_age}+ (survey weights not applied) |
| **Other information** | | | |
| 22 | Funding | Declarations | None |

Items marked "n/a" are not applicable to this study design. Completed for the Theory and Methods resubmission to *Journal of Epidemiology and Community Health*.
