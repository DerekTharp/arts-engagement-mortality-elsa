# Arts engagement and mortality in ELSA — public-data reconstruction (replication code)

Replication code for:

> Tharp D. Checking that the weights worked: a tutorial on balance diagnostics for marginal structural models, using arts engagement and mortality in the English Longitudinal Study of Ageing. Theory and Methods paper submitted to *Journal of Epidemiology and Community Health*, 2026.

The applied example is a public-data reconstruction of:

> Fancourt D, Steptoe A. The art of life and death: 14 year follow-up analyses of associations between arts engagement and mortality in the English Longitudinal Study of Ageing. *BMJ* 2019;367:l6377. doi:10.1136/bmj.l6377

It walks through a ladder of models (baseline-fixed, time-varying, concurrent-confounder-adjusted, and a stabilised IPTW-IPCW marginal structural model) and focuses on diagnosing the weights. For both non-reference exposure contrasts, standardised mean differences are evaluated before and after weighting within prior-wave exposure strata and regression-adjusted for the other covariates retained by the stabilised numerator. A polygenic-score sensitivity analysis with a genetic negative-control-outcome test and a quantitative bias analysis of the public-data death undercount are reported in the supplement.

The repository contains the analysis pipeline, regenerable outputs, reporting
templates, and the reviewed numeric contracts used to prevent stale manuscript
values. Licensed source data and submission DOCX files are not tracked.

## Requirements

- **Python 3.12+** with `numpy`, `scipy`, `pandas`, and `matplotlib` (see `requirements.txt`). No Stata, `statsmodels`, or `lifelines` are needed — the survival, discrete-time, marginal-structural-model, and ordered-logit estimators are implemented directly on numpy/scipy.
- **ELSA Gateway Harmonised data** — UK Data Service study 5050
- **ELSA genetic / polygenic-score data** — UK Data Service study 8773 (required for `08_pgs_sensitivity.py`)

Both ELSA datasets are publicly available to researchers under standard UK Data Service academic licence. NHS-linked mortality data are not required for this analysis and are not used.

## Reproduction

1. Obtain the ELSA Gateway Harmonised dataset (study 5050) and the ELSA genetic dataset (study 8773) from the UK Data Service.
2. Place the UK Data Service downloads under the repository root — study 5050 as `ELSA (English Longitudinal Study of Aging)/UKDA-5050-stata/` and study 8773 as the matching `UKDA-8773-stata/` folder. Paths are configured in one place, `code/pyelsa/config.py` (`PROJ` defaults to the repository root, so running from the repo root works as-is).
3. Install dependencies and run the pipeline from the project root:
   ```
   pip install -r requirements.txt
   python3 code/run_all.py
   ```
   This runs the numbered pipeline (`01`–`09`), regenerates the figures (DAG,
   the numerator-conditioned balance plot, the STROBE participant-flow
   diagram, the undercount heatmap, and the model-ladder forest plot), rebuilds
   all reporting Markdown, and writes `output/ANALYSIS_MANIFEST.json` only after
   the reporting gate passes.
4. All results are written to `output/tables/` (CSV) and
   `output/figures/` (PNG). Project-estimated manuscript values are populated
   from these files. External, administrative, design, and structural literals
   remaining in the templates are reviewed in
   `manuscript/numeric_literals.tsv`.
5. To verify an existing working tree without regenerating it, run
   `python3 code/check_reported_numbers.py`. To rebuild and verify the complete
   JECH upload bundle, including DOCX text/media and staged figures, run
   `python3 code/run_all.py --submission`.
6. To check outputs against a pinned reference set (for example, the original
   Stata run), run `python3 code/validate.py <reference_dir>`. Missing reference
   CSVs fail by default; `--allow-missing-reference` is only for an intentional
   partial exploratory comparison.

## Pipeline

The Python engine is canonical. The numbered `.do` files are retained as the Stata reference implementation. Historical deterministic outputs were used to validate the overlapping Python pipeline; the updated numerator-conditioned balance diagnostic is mirrored in the reference script but the Python success manifest is authoritative. The death-undercount simulation is validated through declared scenario and reproducibility checks rather than identical draws from different random-number generators.

```
code/
  run_all.py                            Orchestrator — runs the full pipeline
  validate.py                           Compares output/tables against a reference set
  check_reported_numbers.py             Fail-closed result/report/submission gate
  build_manuscript.py                   Renders all reporting Markdown from templates
  build_submission_docx.py              Builds the four JECH Word files
  pyelsa/
    config.py                           Single source of truth: paths, variable
                                        lists, covariate sets, recode rules
    io.py                               .dta IO, sentinel cleaning, xtile, design matrices
    models.py                           Cox (Breslow, left-trunc, model/cluster SEs),
                                        cloglog GLM (offset, pweight, cluster),
                                        multinomial/ordered logit, OLS
  01_build_sample.py                    Wave-2 baseline sample + mortality endpoint
                                        + per-variable missingness CSV
  02_cox_replication.py                 Baseline-fixed Cox replication (log)
  03_build_panel.py                     Monotone-censored person-wave panel
  04_time_varying_cox.py                Time-varying Cox (log)
  05_msm_iptw.py                        IPTW + IPCW MSM + concurrent-confounder-
                                        adjusted contrast + raw and numerator-
                                        conditioned balance diagnostics for both
                                        exposure contrasts (writes table2 + all
                                        weight diagnostics)
  06_tables.py                          Baseline characteristics table + transition matrix
  07_figures.py                         Model-ladder forest plot (Supplementary Figure S3)
  08_pgs_sensitivity.py                 Polygenic-score sensitivity + genetic NCO test
  09_death_undercount_sensitivity.py    Quantitative bias analysis grid (simulation)

  make_dag.py                           Directed acyclic graph (Figure 1)
  make_balance_figure.py                Numerator-conditioned balance plot (Figure 2)
  make_flow_diagram.py                  STROBE participant-flow diagram
  make_undercount_figure.py             Death-undercount sensitivity heatmap
  stata_reference/*.do                  Original Stata pipeline (reference implementation)

output/
  ANALYSIS_MANIFEST.json                Hash manifest written only after a fresh,
                                        complete passing run
  tables/                               table1.csv, table2.csv, transitions.csv,
                                        weight_diagnostics.csv, weight_balance.csv,
                                        weight_balance_stratified.csv, table_pgs.csv,
                                        baseline_missingness.csv,
                                        death_undercount_sensitivity.csv
  figures/                              figure1_dag.png,
                                        figure2_balance_smd.png,
                                        figure_s1_flow.png,
                                        figure_s2_undercount_grid.png,
                                        figure_s3_model_ladder.png
```

Every output file is written by exactly one generating script, and each figure
parses its analysis values from the CSV outputs above or the shared external
benchmark configuration. The reporting gate checks exact sample/count
contracts, common-sample identities, finite result grids, current template
renders, every registered numeric literal, and cryptographic hashes for the
complete analysis/reporting bundle. A run begins by invalidating prior success
manifests, so an interrupted or failed run cannot appear current.

## Data

The `data/` subdirectory is not included in this repository — the ELSA raw files are covered by UK Data Service licence terms. Intermediate analytic datasets (`data/fancourt_baseline.dta`, `data/fancourt_panel.dta`) are produced by the pipeline and placed there during execution.

## Citation

If you use or build on this code, please cite the manuscript above (journal citation forthcoming on acceptance).

## Contact

Derek Tharp, PhD
Department of Accounting & Finance, University of Southern Maine, Portland, ME, USA
ORCID: 0000-0002-5973-2586
derek.tharp@maine.edu
