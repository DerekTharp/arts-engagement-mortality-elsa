# Arts engagement and mortality in ELSA — public-data reconstruction (replication code)

Replication code for:

> Tharp D. Checking that the weights worked: a tutorial on balance diagnostics for marginal structural models, using arts engagement and mortality in the English Longitudinal Study of Ageing. Theory and Methods paper submitted to *Journal of Epidemiology and Community Health*, 2026.

The applied example is a public-data reconstruction of:

> Fancourt D, Steptoe A. The art of life and death: 14 year follow-up analyses of associations between arts engagement and mortality in the English Longitudinal Study of Ageing. *BMJ* 2019;367:l6377. doi:10.1136/bmj.l6377

The pipeline walks through a ladder of models (baseline-fixed, time-varying, concurrent-confounder-adjusted, and a stabilised IPTW-IPCW marginal structural model) and focuses on diagnosing the weights. For both non-reference exposure contrasts, standardised mean differences are evaluated before and after weighting within prior-wave exposure strata and regression-adjusted for the other covariates retained by the stabilised numerator. A polygenic-score sensitivity analysis with a genetic negative-control-outcome test and a quantitative bias analysis of the public-data death undercount are also produced.

## Requirements

- **Python 3.12+** with `numpy`, `scipy`, `pandas`, and `matplotlib` (see `requirements.txt`). No Stata, `statsmodels`, or `lifelines` are needed — the survival, discrete-time, marginal-structural-model, and ordered-logit estimators are implemented directly on numpy/scipy.
- **ELSA Gateway Harmonised data** — UK Data Service study 5050
- **ELSA genetic / polygenic-score data** — UK Data Service study 8773 (required for `08_pgs_sensitivity.py`)

Both ELSA datasets are available to researchers under standard UK Data Service academic licence. NHS-linked mortality data are not required for this analysis and are not used.

## Reproduction

1. Obtain the ELSA Gateway Harmonised dataset (study 5050) and the ELSA genetic dataset (study 8773) from the UK Data Service.
2. Place the UK Data Service downloads under the repository root — study 5050 as `ELSA (English Longitudinal Study of Aging)/UKDA-5050-stata/` and study 8773 as the matching `UKDA-8773-stata/` folder. Paths are configured in one place, `code/pyelsa/config.py` (`PROJ` defaults to the repository root, so running from the repository root works as-is).
3. Install dependencies and run the pipeline from the repository root:
   ```
   pip install -r requirements.txt
   python3 code/run_all.py
   ```
4. Results are written to `output/tables/` (CSV) and `output/figures/` (PNG). Both directories are created on the first run.

## Repository contents

```
code/
  run_all.py                            Runs the full pipeline end to end

  01_build_sample.py                    Wave-2 baseline sample and mortality endpoint
  02_cox_replication.py                 Baseline-exposure Cox replication
  03_build_panel.py                     Wave 2-10 person-wave panel
  04_time_varying_cox.py                Time-varying exposure models
  05_msm_iptw.py                        Stabilised IPTW-IPCW marginal structural model
  06_tables.py                          Result tables
  07_figures.py                         Model-ladder forest plot
  08_pgs_sensitivity.py                 Polygenic-score sensitivity and negative-control test
  09_death_undercount_sensitivity.py    Quantitative bias analysis grid (simulation)

  make_dag.py                           Directed acyclic graph
  make_balance_figure.py                Numerator-conditioned balance plot
  make_flow_diagram.py                  STROBE participant-flow diagram
  make_undercount_figure.py             Death-undercount sensitivity heatmap

  pyelsa/                               Shared configuration, I/O, and estimators
    config.py                           Paths, variable names, covariate sets, recodes
    io.py                               Data reading, sentinel cleaning, design matrices
    models.py                           Cox, discrete-time, MSM, and ordered-logit estimators
```

Every output file is written by exactly one generating script, and each figure parses its values from the CSV outputs rather than from hardcoded numbers.

## Data

The `data/` subdirectory is not included in this repository — the ELSA raw files are covered by UK Data Service licence terms. Intermediate analytic datasets (`data/fancourt_baseline.dta`, `data/fancourt_panel.dta`) are produced by the pipeline and placed there during execution.

## Citation

If you use or build on this code, please cite the manuscript above (journal citation forthcoming on acceptance).

## Contact

Derek Tharp, PhD
Department of Accounting & Finance, University of Southern Maine, Portland, ME, USA
ORCID: 0000-0002-5973-2586
derek.tharp@maine.edu
