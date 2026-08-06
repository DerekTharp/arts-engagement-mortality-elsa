"""run_all — reproduce every table and figure from the raw ELSA data.

Set the data location by editing pyelsa/config.py (PROJ defaults to the
repository root, so running from the repository root works as-is). Then:

    python3 code/run_all.py

Runs the numbered pipeline (01-09) and regenerates the figures. Results are
written to output/tables (CSV) and output/figures (PNG).
"""
import subprocess
import sys
from pathlib import Path

from pyelsa import config as C

CODE = Path(__file__).resolve().parent

PIPELINE = [
    "01_build_sample.py",
    "02_cox_replication.py",
    "03_build_panel.py",
    "04_time_varying_cox.py",
    "05_msm_iptw.py",
    "06_tables.py",
    "08_pgs_sensitivity.py",
    "09_death_undercount_sensitivity.py",
]
FIGURE_SCRIPTS = [
    "make_dag.py",
    "make_balance_figure.py",
    "make_flow_diagram.py",
    "make_undercount_figure.py",
    "07_figures.py",
]


def run(script):
    print(f"\n=== {script} ===", flush=True)
    r = subprocess.run([sys.executable, str(CODE / script)])
    if r.returncode != 0:
        sys.exit(f"FAILED: {script}")


def main():
    for d in (C.DATA, C.TABLES, C.FIGURES):
        d.mkdir(parents=True, exist_ok=True)
    for s in PIPELINE + FIGURE_SCRIPTS:
        run(s)
    print("\nPipeline complete. Outputs in output/tables and output/figures.")


if __name__ == "__main__":
    main()
