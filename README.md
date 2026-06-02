# Arts engagement and mortality in ELSA — public-data reconstruction (replication code)

Replication code for:

> Tharp D. Time-varying arts engagement and mortality in older adults: a marginal structural model reconstruction using the English Longitudinal Study of Ageing. Submitted to *Journal of Epidemiology and Community Health*, 2026.

The analysis is a public-data reconstruction of:

> Fancourt D, Steptoe A. The art of life and death: 14 year follow-up analyses of associations between arts engagement and mortality in the English Longitudinal Study of Ageing. *BMJ* 2019;367:l6377. doi:10.1136/bmj.l6377

and extends it with time-varying exposure, a stabilised IPTW-IPCW marginal structural model, a naive concurrent-confounder-adjusted contrast, a polygenic-score sensitivity analysis with a genetic negative-control-outcome test, and a quantitative bias analysis bounding the headline HR under varying assumptions about the public-data death undercount.

This is a code-only repository. The manuscript, supplement, STROBE checklist, and cover letter are not tracked here. The repository contains only the latest revision of the pipeline; no development history is retained.

## Requirements

- **Stata 18 or later** (tested on Stata/MP 19)
- **Python 3.10+** with `matplotlib` and `pandas` for the DAG, STROBE participant-flow diagram, and undercount sensitivity heatmap
- **ELSA Gateway Harmonised data** — UK Data Service study 5050
- **ELSA genetic / polygenic-score data** — UK Data Service study 8773 (required for `08_pgs_sensitivity.do`)

Both ELSA datasets are publicly available to researchers under standard UK Data Service academic licence. NHS-linked mortality data are not required for this analysis and are not used.

## Reproduction

1. Obtain the ELSA Gateway Harmonised dataset (study 5050) and the ELSA genetic dataset (study 8773) from the UK Data Service.
2. Set `global proj` at the top of `code/00_master.do` to the repository root (it defaults to `.`, the current directory, so running from the repo root works as-is). Place the UK Data Service downloads beneath it — study 5050 as `ELSA (English Longitudinal Study of Aging)/UKDA-5050-stata/` and study 8773 as the matching `UKDA-8773-stata/` folder.
3. From the project root, run:
   ```
   stata-mp -b do code/00_master.do
   ```
   This executes the full pipeline (`01_build_sample.do` through `09_death_undercount_sensitivity.do`), then generates the DAG, STROBE participant-flow diagram, and undercount sensitivity heatmap via Python.
4. All results are written to `output/tables/` (CSV) and `output/figures/` (PNG). Every number reported in the paper can be read directly from these files.

## Pipeline

```
code/
  00_master.do                          Orchestrator — runs the full pipeline
  01_build_sample.do                    Wave-2 baseline sample + mortality endpoint
                                        + per-variable missingness CSV
  02_cox_replication.do                 Baseline-fixed Cox replication
  03_build_panel.do                     Monotone-censored person-wave panel
  04_time_varying_cox.do                Time-varying Cox + discrete-time PH models
  05_msm_iptw.do                        IPTW + IPCW MSM + naive confounder-adjusted
                                        contrast
  06_tables.do                          Table 1 (baseline characteristics)
                                        + transition matrix
  07_figures.do                         Forest plot (model comparison)
  08_pgs_sensitivity.do                 Polygenic-score sensitivity analysis +
                                        genetic NCO test
  09_death_undercount_sensitivity.do    Quantitative bias analysis grid

  make_dag.py                           Directed acyclic graph
  make_flow_diagram.py                  STROBE participant-flow diagram
  make_undercount_figure.py             Death-undercount sensitivity heatmap

output/
  tables/                               table1.csv, table2.csv, transitions.csv,
                                        weight_diagnostics.csv, table_pgs.csv,
                                        baseline_missingness.csv,
                                        death_undercount_sensitivity.csv
  figures/                              figure1_dag.png,
                                        figure2_model_comparison.png,
                                        figure_s1_flow.png,
                                        figure_s2_undercount_grid.png
```

Every output file is written by exactly one generating script, and each figure parses its analysis values from the CSV outputs above. The only hardcoded constant is the published Fancourt & Steptoe reference estimate (HR 0.69), shown on the forest plot for comparison.

## Data

The `data/` subdirectory is not included in this repository — the ELSA raw files are covered by UK Data Service licence terms. Intermediate analytic datasets (`data/fancourt_baseline.dta`, `data/fancourt_panel.dta`) are produced by the pipeline and placed there during execution.

## Citation

If you use or build on this code, please cite the manuscript above (journal citation forthcoming on acceptance).

## Contact

Derek Tharp, PhD
Department of Accounting & Finance, University of Southern Maine, Portland, ME, USA
ORCID: 0000-0002-5973-2586
derek.tharp@maine.edu
