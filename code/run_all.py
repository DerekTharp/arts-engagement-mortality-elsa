"""run_all — reproduce every table and figure from the raw ELSA data.

The Python engine for the ELSA arts-engagement analysis. Set the data location
by editing pyelsa/config.py (PROJ defaults to the repository root). Then:

    python3 code/run_all.py

Runs the numbered pipeline (01-09), regenerates the figures, and rebuilds the
manuscript. A successful run writes ANALYSIS_MANIFEST.json only after the
reporting gate passes. Add ``--submission`` to rebuild and verify the complete
JECH upload bundle.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from check_reported_numbers import REQUIRED_FIGURES

ROOT = Path(__file__).resolve().parent.parent
CODE = Path(__file__).resolve().parent
FIGURE_DIR = ROOT / "output" / "figures"
SUBMISSION_FIGURES = ROOT / "JECH submission" / "figures"

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


def run(script, *args):
    label = " ".join((script, *map(str, args)))
    print(f"\n=== {label} ===", flush=True)
    r = subprocess.run([sys.executable, str(CODE / script), *map(str, args)])
    if r.returncode != 0:
        sys.exit(f"FAILED: {label}")


def stage_submission_figures():
    SUBMISSION_FIGURES.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_FIGURES:
        source = FIGURE_DIR / name
        if not source.is_file():
            sys.exit(f"FAILED: required submission figure is missing: {source}")
        shutil.copy2(source, SUBMISSION_FIGURES / name)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rebuild and verify every analysis and reporting artifact."
    )
    parser.add_argument(
        "--submission",
        action="store_true",
        help="Also rebuild and verify the complete JECH submission bundle.",
    )
    args = parser.parse_args(argv)

    # This invalidates every prior success marker before any analytical work.
    # A failed or interrupted run therefore cannot leave a valid manifest.
    run("check_reported_numbers.py", "--begin-run")
    for s in PIPELINE:
        run(s)
    for s in FIGURE_SCRIPTS:
        run(s)
    run("build_manuscript.py")
    run("check_reported_numbers.py", "--refresh-manifest")

    if args.submission:
        run("build_submission_docx.py")
        stage_submission_figures()
        run(
            "check_reported_numbers.py",
            "--submission",
            "--refresh-submission-manifest",
        )
        print("\nSubmission bundle complete and verified.")
    else:
        print("\nPipeline complete and verified. Outputs in output/tables and output/figures.")


if __name__ == "__main__":
    main()
