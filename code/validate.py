"""Validate the Python pipeline's outputs against a reference set of CSVs
(e.g. the Stata pipeline's committed outputs).

Usage:
    python3 code/validate.py <reference_dir>

Compares every CSV the Python pipeline writes to output/tables/ against the
same-named file in <reference_dir>. Cells are compared as strings after
normalising line endings; numeric cells that differ are re-checked with a small
tolerance and reported with the magnitude of the difference so immaterial
rounding is distinguishable from real divergence. Missing reference files fail
validation by default; ``--allow-missing-reference`` is an explicit escape for
partial exploratory comparisons.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "output" / "tables"


def _rows(path):
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip("\n")
    return [line.split(",") for line in text.split("\n")]


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def compare(py_path, ref_path, tol=5e-3):
    a, b = _rows(py_path), _rows(ref_path)
    diffs = []
    if len(a) != len(b):
        diffs.append(f"row count {len(a)} vs {len(b)}")
    for i, (ra, rb) in enumerate(zip(a, b)):
        if len(ra) != len(rb):
            diffs.append(f"row {i}: field count {len(ra)} vs {len(rb)}")
            continue
        for j, (ca, cb) in enumerate(zip(ra, rb)):
            if ca == cb:
                continue
            na, nb = _num(ca), _num(cb)
            if na is not None and nb is not None:
                if abs(na - nb) <= tol:
                    diffs.append(f"row {i} col {j}: {ca} vs {cb} (diff={abs(na-nb):.4g}, within tol)")
                else:
                    diffs.append(f"row {i} col {j}: {ca} vs {cb} (diff={abs(na-nb):.4g})")
            else:
                diffs.append(f"row {i} col {j}: '{ca}' vs '{cb}'")
    return diffs


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare pipeline CSVs with a pinned reference set."
    )
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument(
        "--allow-missing-reference",
        action="store_true",
        help="Permit output CSVs with no same-named reference file.",
    )
    args = parser.parse_args(argv)
    ref = args.reference_dir
    if not ref.is_dir():
        parser.error(f"reference directory does not exist: {ref}")

    py_files = sorted(TABLES.glob("*.csv"))
    n_exact = n_tol = n_diff = n_skip = 0
    for pf in py_files:
        rf = ref / pf.name
        if not rf.exists():
            print(f"  --  {pf.name}: no reference")
            n_skip += 1
            continue
        diffs = compare(pf, rf)
        hard = [d for d in diffs if "within tol" not in d]
        if not diffs:
            print(f"  OK  {pf.name}: identical")
            n_exact += 1
        elif not hard:
            print(f"  ~=  {pf.name}: {len(diffs)} cell(s) within tolerance")
            for d in diffs:
                print(f"        {d}")
            n_tol += 1
        else:
            print(f"  XX  {pf.name}: {len(hard)} cell(s) differ")
            for d in hard[:20]:
                print(f"        {d}")
            n_diff += 1
    print(f"\n{n_exact} identical, {n_tol} within-tolerance, {n_diff} differ, {n_skip} no-reference")
    if n_skip and not args.allow_missing_reference:
        print(
            "Missing reference files are validation failures. "
            "Use --allow-missing-reference only for an intentional partial comparison."
        )
    return 1 if n_diff or (n_skip and not args.allow_missing_reference) else 0


if __name__ == "__main__":
    raise SystemExit(main())
