#!/usr/bin/env python3
"""Fail-closed reporting and stale-number gate for the JECH resubmission.

The project already renders analysis values from CSVs into Markdown.  This gate
adds the safeguards used in the stronger neighbouring projects:

* exact structural-count and cross-output identities;
* a reviewed ledger for every numeric literal left in a reporting template;
* a pure rebuild comparison for manuscript, supplement, STROBE and cover letter;
* success manifests that hash the complete analysis/reporting bundle;
* optional fresh-DOCX and submission-figure comparisons.

Normal workflow:

    python3 code/run_all.py
    python3 code/check_reported_numbers.py

Final upload workflow:

    python3 code/run_all.py --submission

The analysis success manifest is invalidated before ``run_all.py`` starts and is
written atomically only after every declared output and report passes.  A failed
or partial run therefore cannot leave a valid success marker behind.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
DATA = ROOT / "data"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
MANUSCRIPT = ROOT / "manuscript"
SUBMISSION = ROOT / "JECH submission"

EXPECTATIONS = MANUSCRIPT / "reporting_expectations.json"
LITERAL_LEDGER = MANUSCRIPT / "numeric_literals.tsv"
ANALYSIS_MANIFEST = ROOT / "output" / "ANALYSIS_MANIFEST.json"
SUBMISSION_MANIFEST = SUBMISSION / "SUBMISSION_MANIFEST.json"
RUN_MARKER = ROOT / "output" / ".analysis_run_started"

REQUIRED_TABLES = (
    "baseline_missingness.csv",
    "death_undercount_sensitivity.csv",
    "positivity.csv",
    "sensitivity_censoring.csv",
    "sensitivity_weights.csv",
    "table1.csv",
    "table2.csv",
    "table_pgs.csv",
    "transitions.csv",
    "weight_balance.csv",
    "weight_balance_stratified.csv",
    "weight_diagnostics.csv",
)

REQUIRED_FIGURES = (
    "figure1_dag.png",
    "figure2_balance_smd.png",
    "figure_s1_flow.png",
    "figure_s2_undercount_grid.png",
    "figure_s3_model_ladder.png",
)

REPORT_TEMPLATES = (
    "manuscript_template.md",
    "supplement_template.md",
    "strobe_checklist_template.md",
    "cover_letter_template.md",
)

REPORT_OUTPUTS = (
    "manuscript.md",
    "supplement.md",
    "strobe_checklist.md",
    "cover_letter.md",
)

GENERATED_DATA = (
    "fancourt_baseline.dta",
    "arts_long.dta",
    "fancourt_panel.dta",
)

DOCX_NAMES = (
    "manuscript.docx",
    "supplement.docx",
    "strobe_checklist.docx",
    "cover_letter.docx",
)

COMMON_PANEL_MODELS = (
    "Baseline-fixed cloglog (panel)",
    "Unweighted discrete-time PH",
    "Concurrent-confounder-adjusted PH",
    "MSM IPTW+IPCW cloglog",
)

MODEL_EXPOSURES = ("Infrequent", "Frequent")
STRATA = ("pooled", "lag_never", "lag_infrequent", "lag_frequent")
CONTRASTS = ("freq_vs_never", "infreq_vs_never")

LITERAL_CLASSES = {"ADMIN", "DESIGN", "EXTERNAL", "STRUCTURAL"}
NUMBER_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
    "thousand",
    "half",
    "quarter",
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
)
NUMBER_WORD_RE = re.compile(
    r"\b(?:" + "|".join(NUMBER_WORDS) + r")\b", flags=re.IGNORECASE
)
NUMERIC_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"([+−-]?(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?|\.\d+)"
    r"(?:st|nd|rd|th)?%?)"
    r"(?![A-Za-z0-9_])"
)

MANIFEST_SCHEMA_VERSION = 2


class GateError(RuntimeError):
    """A reporting contract or provenance check failed."""


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise GateError(f"missing artifact: {path.relative_to(ROOT)}")
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    after = path.stat()
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise GateError(f"artifact changed while hashing: {path}")
    return digest.hexdigest()


def _artifact_record(path: Path) -> dict[str, str | int]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _read_csv(name: str) -> list[dict[str, str]]:
    path = TABLES / name
    if not path.is_file():
        raise GateError(f"missing required table: output/tables/{name}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _read_first_csv_block(name: str) -> list[dict[str, str]]:
    """Read the first rectangular block of a multi-block CSV."""
    path = TABLES / name
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    block = []
    for line in lines:
        if not line.strip():
            break
        block.append(line)
    return list(csv.DictReader(block))


def _as_int(value: str, label: str) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise GateError(f"{label} is not numeric: {value!r}") from exc
    if not math.isfinite(number) or not number.is_integer():
        raise GateError(f"{label} is not a finite integer: {value!r}")
    return int(number)


def _as_float(value: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise GateError(f"{label} is not numeric: {value!r}") from exc
    if not math.isfinite(number):
        raise GateError(f"{label} is not finite: {value!r}")
    return number


def _expect_equal(label: str, actual, expected) -> None:
    if actual != expected:
        raise GateError(f"{label}: got {actual!r}, expected {expected!r}")


def _expect_close(label: str, actual: float, expected: float, tol=5e-10) -> None:
    if abs(actual - expected) > tol:
        raise GateError(
            f"{label}: got {actual!r}, expected {expected!r} (tol={tol})"
        )


def load_expectations() -> dict:
    try:
        payload = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read reporting expectations: {exc}") from exc
    if payload.get("schema_version") != 1:
        raise GateError("reporting_expectations.json schema_version must be 1")
    return payload


def check_output_contract() -> dict[str, int]:
    """Enforce exact counts, schemas, finite values and cross-output identities."""
    expected = load_expectations()

    missing = [name for name in REQUIRED_TABLES if not (TABLES / name).is_file()]
    if missing:
        raise GateError(f"missing required output tables: {missing}")
    empty = [name for name in REQUIRED_TABLES if (TABLES / name).stat().st_size == 0]
    if empty:
        raise GateError(f"empty required output tables: {empty}")

    # Baseline anchors from Table 1.
    table1 = _read_csv("table1.csv")
    by_t1 = {(r.get("Variable", ""), r.get("Level", "")): r for r in table1}
    n_row = by_t1.get(("N", ""))
    d_row = by_t1.get(("Died during follow-up", ""))
    if n_row is None or d_row is None:
        raise GateError("table1.csv is missing the N or death anchor row")
    baseline_n = _as_int(n_row["Total (N=)"], "table1 baseline N")
    baseline_deaths = _as_int(
        d_row["Total (N=)"], "table1 baseline deaths"
    )
    _expect_equal("baseline N", baseline_n, expected["baseline"]["n"])
    _expect_equal(
        "baseline deaths", baseline_deaths, expected["baseline"]["deaths"]
    )

    # Model table: exact row/key set, finite estimates, and common samples.
    table2 = _read_csv("table2.csv")
    _expect_equal("table2 row count", len(table2), expected["table2_rows"])
    by_model = {}
    for index, row in enumerate(table2, start=2):
        key = (row.get("Model", ""), row.get("Exposure", ""))
        if key in by_model:
            raise GateError(f"table2 duplicate key at row {index}: {key}")
        by_model[key] = row
        estimates = {
            column: _as_float(row.get(column, ""), f"table2 {key} {column}")
            for column in ("HR", "CI_low", "CI_high")
        }
        if not (
            estimates["CI_low"] <= estimates["HR"] <= estimates["CI_high"]
        ):
            raise GateError(f"table2 {key} estimate lies outside its CI")
        for column in ("N", "Deaths"):
            _as_int(row.get(column, ""), f"table2 {key} {column}")

    required_model_keys = {
        (model, exposure)
        for model in (
            "Baseline-fixed Cox",
            "Time-varying Cox",
            *COMMON_PANEL_MODELS,
        )
        for exposure in MODEL_EXPOSURES
    }
    _expect_equal("table2 model/exposure keys", set(by_model), required_model_keys)

    for exposure in MODEL_EXPOSURES:
        row = by_model[("Baseline-fixed Cox", exposure)]
        _expect_equal(
            f"baseline Cox N ({exposure})",
            _as_int(row["N"], "baseline Cox N"),
            baseline_n,
        )
        _expect_equal(
            f"baseline Cox deaths ({exposure})",
            _as_int(row["Deaths"], "baseline Cox deaths"),
            baseline_deaths,
        )

    tv_rows = [by_model[("Time-varying Cox", exposure)] for exposure in MODEL_EXPOSURES]
    for row in tv_rows:
        _expect_equal(
            "time-varying Cox intervals",
            _as_int(row["N"], "time-varying Cox N"),
            expected["time_varying_cox"]["intervals"],
        )
        _expect_equal(
            "time-varying Cox deaths",
            _as_int(row["Deaths"], "time-varying Cox deaths"),
            expected["time_varying_cox"]["deaths"],
        )

    common_rows = [
        by_model[(model, exposure)]
        for model in COMMON_PANEL_MODELS
        for exposure in MODEL_EXPOSURES
    ]
    common_ns = {_as_int(row["N"], "common-panel N") for row in common_rows}
    common_ds = {
        _as_int(row["Deaths"], "common-panel deaths") for row in common_rows
    }
    _expect_equal("common-panel N identity", common_ns, {expected["panel"]["outcome_intervals"]})
    _expect_equal("common-panel death identity", common_ds, {expected["panel"]["deaths"]})
    panel_n = next(iter(common_ns))
    panel_deaths = next(iter(common_ds))

    # Weight diagnostics must identify the same analytic panel.
    weights = {
        row["stat"]: row["value"] for row in _read_csv("weight_diagnostics.csv")
    }
    for stat in (
        "mean",
        "sd",
        "min",
        "max",
        "p1",
        "p5",
        "p25",
        "p50",
        "p75",
        "p95",
        "p99",
        "n_outcome",
        "n_missing_weight",
        "ess",
        "ess_ratio",
    ):
        if stat not in weights:
            raise GateError(f"weight_diagnostics.csv missing stat={stat}")
    weight_n = _as_int(weights["n_outcome"], "weight n_outcome")
    missing_weight = _as_int(
        weights["n_missing_weight"], "weight n_missing_weight"
    )
    _expect_equal("weight outcome N", weight_n, panel_n)
    _expect_equal(
        "missing weights", missing_weight, expected["panel"]["missing_weights"]
    )
    _expect_equal(
        "pre-weight interval count",
        weight_n + missing_weight,
        expected["panel"]["pre_weight_intervals"],
    )

    # Primary sensitivity row must repeat the primary MSM result exactly.
    sens = _read_csv("sensitivity_censoring.csv")
    primary = [r for r in sens if r.get("spec", "").startswith("MSM primary")]
    if len(primary) != 1:
        raise GateError(
            f"sensitivity_censoring primary selector matched {len(primary)} rows"
        )
    msm = by_model[("MSM IPTW+IPCW cloglog", "Frequent")]
    primary = primary[0]
    for column in ("HR", "CI_low", "CI_high"):
        _expect_close(
            f"primary sensitivity {column}",
            _as_float(primary[column], f"sensitivity {column}"),
            _as_float(msm[column], f"MSM {column}"),
        )
    _expect_equal(
        "primary sensitivity N",
        _as_int(primary["N"], "primary sensitivity N"),
        panel_n,
    )
    sensitivity_columns = (
        "terminal_total",
        "known_alive_next",
        "unknown_next",
        "known_alive_pct",
        "unknown_pct",
    )
    for column in sensitivity_columns:
        if column not in primary:
            raise GateError(
                f"sensitivity_censoring.csv missing required column {column}"
            )
    terminal_total = _as_int(
        primary["terminal_total"], "terminal sensitivity total"
    )
    known_alive = _as_int(
        primary["known_alive_next"], "terminal known-alive count"
    )
    unknown_next = _as_int(
        primary["unknown_next"], "terminal unknown-status count"
    )
    _expect_equal(
        "terminal-status count identity",
        known_alive + unknown_next,
        terminal_total,
    )
    known_pct = _as_float(
        primary["known_alive_pct"], "terminal known-alive percentage"
    )
    unknown_pct = _as_float(
        primary["unknown_pct"], "terminal unknown percentage"
    )
    if terminal_total <= 0:
        raise GateError("terminal sensitivity total must be positive")
    _expect_close(
        "terminal known-alive percentage",
        known_pct,
        100 * known_alive / terminal_total,
        tol=0.051,
    )
    _expect_close(
        "terminal unknown percentage",
        unknown_pct,
        100 * unknown_next / terminal_total,
        tol=0.051,
    )
    _expect_close(
        "terminal percentages sum",
        known_pct + unknown_pct,
        100.0,
        tol=0.11,
    )
    alternative = [
        r for r in sens if r.get("spec", "").startswith("MSM unknown")
    ]
    if len(alternative) != 1:
        raise GateError(
            "sensitivity_censoring unknown-status selector matched "
            f"{len(alternative)} rows"
        )
    alternative = alternative[0]
    for column in sensitivity_columns:
        _expect_equal(
            f"terminal diagnostic repeated in alternative ({column})",
            alternative[column],
            primary[column],
        )
    _expect_equal(
        "terminal sensitivity sample identity",
        _as_int(alternative["N"], "terminal alternative N")
        + _as_int(alternative["n_removed"], "terminal intervals removed"),
        panel_n,
    )

    # Stratified balance: complete Cartesian product with stable cell sizes.
    balance = _read_csv("weight_balance_stratified.csv")
    b_exp = expected["stratified_balance"]
    _expect_equal("stratified-balance row count", len(balance), b_exp["rows"])
    keys = Counter()
    covariates = set()
    strata = set()
    contrasts = set()
    cell_sizes = {}
    adjusted_sizes = {}
    for row in balance:
        key = (row["stratum"], row["contrast"], row["covariate"])
        keys[key] += 1
        covariates.add(row["covariate"])
        strata.add(row["stratum"])
        contrasts.add(row["contrast"])
        for field in (
            "smd_raw_unweighted",
            "smd_raw_weighted",
            "smd_adjusted_unweighted",
            "smd_adjusted_weighted",
        ):
            _as_float(row[field], f"balance {key} {field}")
        pair = (
            _as_int(row["n_hi"], f"balance {key} n_hi"),
            _as_int(row["n_lo"], f"balance {key} n_lo"),
        )
        n_adjusted = _as_int(
            row["n_adjusted"], f"balance {key} n_adjusted"
        )
        if n_adjusted <= 0 or n_adjusted > sum(pair):
            raise GateError(
                f"balance adjusted sample invalid for {key}: "
                f"{n_adjusted} of {sum(pair)}"
            )
        sc = (row["stratum"], row["contrast"])
        if sc in cell_sizes and cell_sizes[sc] != pair:
            raise GateError(f"balance cell sizes vary within {sc}")
        cell_sizes[sc] = pair
        if sc in adjusted_sizes and adjusted_sizes[sc] != n_adjusted:
            raise GateError(f"balance adjusted sample sizes vary within {sc}")
        adjusted_sizes[sc] = n_adjusted
    duplicates = [key for key, count in keys.items() if count != 1]
    if duplicates:
        raise GateError(f"stratified-balance duplicate keys: {duplicates[:5]}")
    _expect_equal("balance strata", strata, set(STRATA))
    _expect_equal("balance contrasts", contrasts, set(CONTRASTS))
    _expect_equal("balance covariate count", len(covariates), b_exp["covariates"])
    _expect_equal("balance stratum count", len(strata), b_exp["strata"])
    _expect_equal("balance contrast count", len(contrasts), b_exp["contrasts"])
    expected_balance_keys = {
        (stratum, contrast, covariate)
        for stratum in STRATA
        for contrast in CONTRASTS
        for covariate in covariates
    }
    _expect_equal("stratified-balance key grid", set(keys), expected_balance_keys)
    expected_cell_sizes = {
        tuple(key.split("|")): tuple(values)
        for key, values in b_exp["cell_sizes"].items()
    }
    observed_cell_sizes = {
        key: (*cell_sizes[key], adjusted_sizes[key]) for key in cell_sizes
    }
    _expect_equal(
        "stratified-balance cell sizes",
        observed_cell_sizes,
        expected_cell_sizes,
    )

    # PGS sample/event anchors.
    pgs = _read_first_csv_block("table_pgs.csv")
    pgs_ref = [
        row
        for row in pgs
        if row.get("Model") == "Cox (no PGS; genotyped)"
    ]
    if len(pgs_ref) != 2:
        raise GateError(f"PGS reference selector matched {len(pgs_ref)} rows")
    for row in pgs_ref:
        _expect_equal(
            "PGS N", _as_int(row["N"], "PGS N"), expected["pgs"]["n"]
        )
        _expect_equal(
            "PGS deaths",
            _as_int(row["Deaths"], "PGS deaths"),
            expected["pgs"]["deaths"],
        )
    pgs_arts = [
        row
        for row in pgs
        if row.get("Model") == "PGS-education predicting arts engagement"
    ]
    if len(pgs_arts) != 1:
        raise GateError(
            "PGS arts-prediction selector matched "
            f"{len(pgs_arts)} rows"
        )
    pgs_arts_p = _as_float(
        pgs_arts[0].get("P_value", ""), "PGS arts-prediction P value"
    )
    if not 0 <= pgs_arts_p <= 1:
        raise GateError("PGS arts-prediction P value lies outside [0, 1]")

    # Death-undercount grid identity and finite result cells.
    undercount = _read_csv("death_undercount_sensitivity.csv")
    u_exp = expected["death_undercount"]
    _expect_equal("undercount row count", len(undercount), u_exp["rows"])
    grid_keys = Counter()
    reps = set()
    by_exposure_count = Counter()
    n_extra_levels = set()
    rr_alloc_levels = set()
    exposure_levels = set()
    for row in undercount:
        n_extra = _as_int(row["n_extra"], "undercount n_extra")
        rr_alloc = _as_float(row["rr_alloc"], "undercount rr_alloc")
        exposure = row["exposure"]
        if n_extra < 0 or rr_alloc <= 0:
            raise GateError(
                f"invalid undercount design cell: n_extra={n_extra}, "
                f"rr_alloc={rr_alloc}"
            )
        key = (n_extra, rr_alloc, exposure)
        grid_keys[key] += 1
        by_exposure_count[exposure] += 1
        n_extra_levels.add(n_extra)
        rr_alloc_levels.add(rr_alloc)
        exposure_levels.add(exposure)
        reps.add(_as_int(row["n_reps"], f"undercount {key} n_reps"))
        estimates = {
            column: _as_float(row[column], f"undercount {key} {column}")
            for column in ("HR_median", "HR_p2_5", "HR_p97_5")
        }
        if not (
            estimates["HR_p2_5"]
            <= estimates["HR_median"]
            <= estimates["HR_p97_5"]
        ):
            raise GateError(
                f"undercount median lies outside simulation interval: {key}"
            )
    duplicate_grid = [key for key, count in grid_keys.items() if count != 1]
    if duplicate_grid:
        raise GateError(f"undercount duplicate keys: {duplicate_grid[:5]}")
    _expect_equal(
        "undercount repetitions", reps, {u_exp["repetitions_per_cell"]}
    )
    _expect_equal(
        "undercount cells per exposure",
        set(by_exposure_count.values()),
        {u_exp["cells_per_exposure"]},
    )
    _expect_equal(
        "undercount exposure count",
        len(exposure_levels),
        u_exp["exposures"],
    )
    _expect_equal(
        "undercount exposure labels",
        exposure_levels,
        set(MODEL_EXPOSURES),
    )
    _expect_equal(
        "undercount n_extra level count",
        len(n_extra_levels),
        u_exp["n_extra_levels"],
    )
    _expect_equal(
        "undercount rr_alloc level count",
        len(rr_alloc_levels),
        u_exp["rr_alloc_levels"],
    )
    expected_grid = {
        (n_extra, rr_alloc, exposure)
        for n_extra in n_extra_levels
        for rr_alloc in rr_alloc_levels
        for exposure in exposure_levels
    }
    _expect_equal("undercount Cartesian grid", set(grid_keys), expected_grid)
    if not set(u_exp["reported_allocation_levels"]).issubset(rr_alloc_levels):
        raise GateError(
            "undercount grid omits an allocation level reported in the supplement"
        )
    sys.path.insert(0, str(CODE))
    from pyelsa import config as C  # pylint: disable=import-outside-toplevel

    calibration_extra = C.PUBLISHED_DEATHS - baseline_deaths
    if calibration_extra not in n_extra_levels:
        raise GateError(
            "undercount grid omits the published-data death-count calibration "
            f"level ({calibration_extra})"
        )

    print(
        "OUTPUT CONTRACT: PASS "
        f"(baseline {baseline_n}/{baseline_deaths} deaths; "
        f"panel {panel_n}/{panel_deaths} deaths; "
        f"{len(balance)} balance rows)"
    )
    return {
        "baseline_n": baseline_n,
        "baseline_deaths": baseline_deaths,
        "panel_n": panel_n,
        "panel_deaths": panel_deaths,
        "panel_pre_weight": weight_n + missing_weight,
        "pgs_n": expected["pgs"]["n"],
        "pgs_deaths": expected["pgs"]["deaths"],
    }


def _template_scan_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # References contain bibliographic numbers governed by the citation audit,
    # not the empirical-number ledger. Keep the later figure legends.
    if path.name == "manuscript_template.md":
        start = text.find("## References")
        end = text.find("## Figure legends", start)
        if start >= 0 and end >= 0:
            text = text[:start] + text[end:]
    text = re.sub(r"\{[a-z_][a-z0-9_]*\}", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b10\.\d{4,9}/\S+", " ", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+", " ", text)
    text = re.sub(r"\^[0-9,\-]+\^", " ", text)
    return text


def discover_template_literals() -> Counter[tuple[str, str]]:
    found: Counter[tuple[str, str]] = Counter()
    for name in REPORT_TEMPLATES:
        path = MANUSCRIPT / name
        if not path.is_file():
            raise GateError(f"missing reporting template: manuscript/{name}")
        text = _template_scan_text(path)
        rel = path.relative_to(ROOT).as_posix()
        for match in NUMERIC_RE.finditer(text):
            found[(rel, match.group(1))] += 1
        for match in NUMBER_WORD_RE.finditer(text):
            found[(rel, match.group(0).lower())] += 1
    return found


def load_literal_ledger() -> tuple[Counter[tuple[str, str]], list[dict[str, str]]]:
    if not LITERAL_LEDGER.is_file():
        raise GateError("missing manuscript/numeric_literals.tsv")
    with LITERAL_LEDGER.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    expected_header = {"path", "token", "count", "class", "source", "note"}
    if not rows:
        raise GateError("numeric_literals.tsv has no reviewed rows")
    if set(rows[0]) != expected_header:
        raise GateError(
            "numeric_literals.tsv columns must be "
            "path, token, count, class, source, note"
        )
    declared: Counter[tuple[str, str]] = Counter()
    seen = set()
    for line_no, row in enumerate(rows, start=2):
        key = (row["path"].strip(), row["token"].strip())
        if key in seen:
            raise GateError(f"numeric_literals.tsv duplicate row {line_no}: {key}")
        seen.add(key)
        if row["class"].strip() not in LITERAL_CLASSES:
            raise GateError(
                f"numeric_literals.tsv row {line_no} has invalid class "
                f"{row['class']!r}"
            )
        if not row["source"].strip() or not row["note"].strip():
            raise GateError(
                f"numeric_literals.tsv row {line_no} needs source and note"
            )
        count = _as_int(row["count"], f"numeric literal row {line_no} count")
        if count <= 0:
            raise GateError(
                f"numeric_literals.tsv row {line_no} count must be positive"
            )
        declared[key] = count
    return declared, rows


def check_template_literals() -> None:
    actual = discover_template_literals()
    declared, _ = load_literal_ledger()
    uncovered = actual - declared
    orphaned = declared - actual
    if uncovered or orphaned:
        parts = []
        if uncovered:
            preview = [
                f"{path}:{token} x{count}"
                for (path, token), count in sorted(uncovered.items())[:20]
            ]
            parts.append("unregistered numeric literals: " + "; ".join(preview))
        if orphaned:
            preview = [
                f"{path}:{token} x{count}"
                for (path, token), count in sorted(orphaned.items())[:20]
            ]
            parts.append("orphaned/over-counted ledger entries: " + "; ".join(preview))
        raise GateError(" | ".join(parts))
    print(
        "NUMERIC LITERAL LEDGER: PASS "
        f"({sum(actual.values())} occurrences; {len(actual)} path/token entries)"
    )


def check_rendered_reports() -> dict[str, str]:
    """Verify every report is exactly what current CSVs/templates render."""
    sys.path.insert(0, str(CODE))
    import build_manuscript as builder  # pylint: disable=import-outside-toplevel

    try:
        rendered, values = builder.render_outputs()
        builder.check_outputs(rendered)
    except Exception as exc:  # the builder turns source/output errors into context
        raise GateError(f"fresh report render failed: {exc}") from exc

    for output_path in rendered:
        text = output_path.read_text(encoding="utf-8")
        if re.search(r"\{[a-z_][a-z0-9_]*\}", text):
            raise GateError(f"unresolved placeholder in {output_path.name}")
        if re.search(r"(?<!\w)(?:TBD|nan|[+-]?inf)(?!\w)", text, re.I):
            raise GateError(f"sentinel/non-finite token in {output_path.name}")

    # Operational checklist counts are cross-checked even though the checklist
    # itself remains editable rather than template-generated.
    checklist_path = SUBMISSION / "SUBMISSION_CHECKLIST.md"
    checklist = checklist_path.read_text(encoding="utf-8")
    main_wc = values["main_word_count"]
    abstract_wc = values["abstract_word_count"]
    references = values["reference_count"]
    displays = values["display_count"]
    if (
        f"**Word count:** {main_wc} " not in checklist
        or f"/ {abstract_wc} (structured abstract)" not in checklist
    ):
        raise GateError(
            "submission checklist word counts do not match the generated manuscript"
        )
    display_match = re.search(
        r"\*\*Display items:\*\*\s*(\d+) tables \+ (\d+) figures", checklist
    )
    if not display_match:
        raise GateError("cannot parse display counts from submission checklist")
    checklist_displays = int(display_match.group(1)) + int(display_match.group(2))
    _expect_equal("checklist display count", checklist_displays, int(displays))
    if f"{references} references" not in checklist:
        raise GateError(
            "submission checklist reference count does not match manuscript"
        )

    print(
        "REPORT BUILD: PASS "
        f"({main_wc} main words; {abstract_wc} abstract; "
        f"{displays} displays; {references} references)"
    )
    return {
        "main_word_count": main_wc,
        "abstract_word_count": abstract_wc,
        "display_count": displays,
        "reference_count": references,
    }


def _repository_state() -> dict[str, str | bool | None]:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return {"revision": None, "dirty": None}
    return {
        "revision": revision.stdout.strip() if revision.returncode == 0 else None,
        "dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def _analysis_input_paths() -> list[Path]:
    paths = sorted(
        path
        for path in CODE.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    paths.extend(MANUSCRIPT / name for name in REPORT_TEMPLATES)
    paths.extend(
        [
            MANUSCRIPT / "reporting_expectations.json",
            MANUSCRIPT / "numeric_literals.tsv",
            ROOT / "requirements.txt",
            ROOT / "README.md",
            ROOT / ".gitignore",
            SUBMISSION / "SUBMISSION_CHECKLIST.md",
        ]
    )
    postformat = MANUSCRIPT / "postformat_docx.py"
    if postformat.exists():
        paths.append(postformat)
    return sorted(set(path.resolve() for path in paths))


def _analysis_output_paths() -> list[Path]:
    paths = [TABLES / name for name in REQUIRED_TABLES]
    paths.extend(FIGURES / name for name in REQUIRED_FIGURES)
    paths.extend(MANUSCRIPT / name for name in REPORT_OUTPUTS)
    # Only the three intermediates below are regenerated by the active Python
    # pipeline.  Including every historical .dta in data/ would make a clean
    # run impossible whenever an intentionally retained legacy file is older
    # than the run marker.
    paths.extend(DATA / name for name in GENERATED_DATA)
    return sorted(set(path.resolve() for path in paths))


def _raw_input_paths() -> list[Path]:
    sys.path.insert(0, str(CODE))
    from pyelsa import config as C  # pylint: disable=import-outside-toplevel

    paths = [
        C.HARM,
        C.EOL,
        C.EOL_W10,
        *(C.WAVES / filename for filename in C.WAVE_FILES.values()),
        C.PGS_ROOT / "list_pgs_scores_elsa_2022.dta",
        C.PGS_ROOT / "principal_components_elsa_2022.dta",
    ]
    return sorted(set(path.resolve() for path in paths), key=str)


def _raw_input_records() -> list[dict[str, str | int]]:
    """Record cryptographic fingerprints for every licensed raw input."""
    records = []
    for path in _raw_input_paths():
        if not path.is_file():
            raise GateError(f"missing licensed raw input: {path}")
        stat = path.stat()
        try:
            recorded_path = path.relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            # The configurable raw-data root may intentionally live outside
            # the repository. In that case the full path is required to
            # distinguish inputs; the default project layout remains relative.
            recorded_path = str(path)
        records.append(
            {
                "path": recorded_path,
                "sha256": _sha256(path),
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    return records


def begin_analysis_run() -> None:
    ANALYSIS_MANIFEST.unlink(missing_ok=True)
    SUBMISSION_MANIFEST.unlink(missing_ok=True)
    RUN_MARKER.unlink(missing_ok=True)
    RUN_MARKER.parent.mkdir(parents=True, exist_ok=True)
    # Snapshot every declared input before execution.  Output mtimes alone are
    # not enough: code or raw data changed during a run could otherwise be
    # recorded as the provenance for results produced by the earlier version.
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "marker_type": "analysis_run_input_snapshot",
        "inputs": [_artifact_record(path) for path in _analysis_input_paths()],
        "raw_inputs": _raw_input_records(),
    }
    _atomic_json(RUN_MARKER, payload)
    print("REPORTING MANIFESTS INVALIDATED")


def _load_run_marker() -> dict:
    if not RUN_MARKER.is_file():
        raise GateError(
            "cannot refresh analysis manifest without a run marker; "
            "start with code/check_reported_numbers.py --begin-run"
        )
    try:
        payload = json.loads(RUN_MARKER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read analysis run marker: {exc}") from exc
    if not isinstance(payload, dict):
        raise GateError("analysis run marker must be a JSON object")
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise GateError("analysis run marker has the wrong schema_version")
    if payload.get("marker_type") != "analysis_run_input_snapshot":
        raise GateError("analysis run marker has the wrong marker_type")
    return payload


def _require_fresh_run_outputs(
    paths: list[Path],
    input_records: list[dict[str, str | int]],
    raw_input_records: list[dict[str, str | int]],
) -> None:
    marker = _load_run_marker()
    if marker.get("inputs") != input_records:
        raise GateError(
            "declared code/reporting inputs changed after this run began; "
            "restart the full pipeline"
        )
    if marker.get("raw_inputs") != raw_input_records:
        raise GateError(
            "licensed raw inputs changed after this run began; "
            "restart the full pipeline"
        )
    started = RUN_MARKER.stat().st_mtime_ns
    stale = [
        path.relative_to(ROOT).as_posix()
        for path in paths
        if not path.is_file() or path.stat().st_mtime_ns < started
    ]
    if stale:
        raise GateError(
            "declared outputs were not regenerated during this run: "
            + ", ".join(stale[:20])
        )


def write_analysis_manifest(summary: dict) -> None:
    inputs = _analysis_input_paths()
    outputs = _analysis_output_paths()
    input_records = [_artifact_record(path) for path in inputs]
    raw_input_records = _raw_input_records()
    _require_fresh_run_outputs(outputs, input_records, raw_input_records)
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_type": "analysis_reporting_bundle",
        "producer": "code/run_all.py",
        "repository": _repository_state(),
        "raw_inputs": raw_input_records,
        "inputs": input_records,
        "outputs": [_artifact_record(path) for path in outputs],
        "checks": summary,
    }
    _atomic_json(ANALYSIS_MANIFEST, payload)
    RUN_MARKER.unlink(missing_ok=True)
    print(f"ANALYSIS MANIFEST: wrote {ANALYSIS_MANIFEST.relative_to(ROOT)}")


def _relative_paths(paths: list[Path]) -> set[str]:
    root = ROOT.resolve()
    return {path.resolve().relative_to(root).as_posix() for path in paths}


def _validate_records(
    records,
    label: str,
    expected_paths: set[str] | None = None,
) -> list[str]:
    errors = []
    if not isinstance(records, list):
        return [f"{label} must be a list"]
    seen = set()
    root = ROOT.resolve()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"{label}[{index}] is not an object")
            continue
        rel = record.get("path")
        if not isinstance(rel, str) or not rel:
            errors.append(f"{label}[{index}].path is invalid")
            continue
        if rel in seen:
            errors.append(f"{label} contains duplicate path {rel}")
            continue
        seen.add(rel)
        try:
            path = (ROOT / rel).resolve()
            canonical = path.relative_to(root).as_posix()
        except (OSError, ValueError):
            errors.append(f"{label}[{index}].path escapes the project root")
            continue
        if rel != canonical:
            errors.append(
                f"{label}[{index}].path is not canonical: {rel!r}"
            )
            continue
        size = record.get("size_bytes")
        digest = record.get("sha256")
        if (
            not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
        ):
            errors.append(f"{label}[{index}].size_bytes is invalid")
            continue
        if not isinstance(digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}", digest
        ):
            errors.append(f"{label}[{index}].sha256 is invalid")
            continue
        if not path.is_file():
            errors.append(f"{rel} is missing")
            continue
        if path.stat().st_size != size:
            errors.append(f"{rel} size is stale")
            continue
        if _sha256(path) != digest:
            errors.append(f"{rel} hash is stale")
    if expected_paths is not None:
        missing = sorted(expected_paths - seen)
        unexpected = sorted(seen - expected_paths)
        if missing:
            errors.append(
                f"{label} omits declared paths: {', '.join(missing[:10])}"
            )
        if unexpected:
            errors.append(
                f"{label} contains undeclared paths: "
                + ", ".join(unexpected[:10])
            )
    return errors


def validate_analysis_manifest(expected_summary: dict | None = None) -> None:
    if not ANALYSIS_MANIFEST.is_file():
        raise GateError(
            "analysis success manifest is absent; run python3 code/run_all.py"
        )
    try:
        payload = json.loads(ANALYSIS_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read analysis manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise GateError("analysis manifest must be a JSON object")
    errors = []
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("wrong analysis manifest schema_version")
    if payload.get("manifest_type") != "analysis_reporting_bundle":
        errors.append("wrong analysis manifest type")
    errors.extend(
        _validate_records(
            payload.get("inputs"),
            "inputs",
            _relative_paths(_analysis_input_paths()),
        )
    )
    errors.extend(
        _validate_records(
            payload.get("outputs"),
            "outputs",
            _relative_paths(_analysis_output_paths()),
        )
    )

    recorded_raw = payload.get("raw_inputs")
    current_raw = _raw_input_records()
    if recorded_raw != current_raw:
        errors.append("licensed raw-input signatures changed")
    if expected_summary is not None and payload.get("checks") != expected_summary:
        errors.append("recorded check summary does not match current checks")
    if errors:
        raise GateError("stale/invalid analysis manifest: " + "; ".join(errors[:20]))
    print("ANALYSIS MANIFEST: PASS")


def _docx_parts(path: Path) -> dict[str, str]:
    """Hash every substantive DOCX part, normalising volatile timestamps.

    Two consecutive builds are byte-identical part-by-part except for the
    created/modified timestamps in ``docProps/core.xml``.  Normalising those
    two fields lets the gate detect stale text, tables, styles, relationships,
    embedded media and metadata without depending on ZIP entry timestamps.
    """
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise GateError(f"DOCX contains duplicate ZIP members: {path.name}")
        records = {}
        for name in sorted(names):
            content = archive.read(name)
            if name == "docProps/core.xml":
                root = ElementTree.fromstring(content)
                for node in root.iter():
                    local = node.tag.rsplit("}", 1)[-1]
                    if local in {"created", "modified"}:
                        node.text = ""
                content = ElementTree.tostring(root, encoding="utf-8")
            records[name] = hashlib.sha256(content).hexdigest()
        return records


def _docx_differences(current: Path, fresh: Path) -> list[str]:
    current_parts = _docx_parts(current)
    fresh_parts = _docx_parts(fresh)
    return [
        name
        for name in sorted(set(current_parts) | set(fresh_parts))
        if current_parts.get(name) != fresh_parts.get(name)
    ]


def check_submission_package() -> None:
    for name in DOCX_NAMES:
        if not (SUBMISSION / name).is_file():
            raise GateError(f"submission package missing {name}")
    staged_pngs = {
        path.name for path in (SUBMISSION / "figures").glob("*.png")
    }
    if staged_pngs != set(REQUIRED_FIGURES):
        missing = sorted(set(REQUIRED_FIGURES) - staged_pngs)
        extra = sorted(staged_pngs - set(REQUIRED_FIGURES))
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise GateError(
            "submission figures directory does not match the declared set: "
            + "; ".join(details)
        )
    for name in REQUIRED_FIGURES:
        source = FIGURES / name
        staged = SUBMISSION / "figures" / name
        if not staged.is_file():
            raise GateError(f"submission package missing figures/{name}")
        if _sha256(source) != _sha256(staged):
            raise GateError(f"submission figure is stale: figures/{name}")

    with tempfile.TemporaryDirectory(prefix="jech_submission_check_") as temp:
        fresh_dir = Path(temp)
        command = [
            sys.executable,
            str(CODE / "build_submission_docx.py"),
            "--out-dir",
            str(fresh_dir),
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode:
            raise GateError(
                "fresh DOCX build failed: "
                + (result.stderr.strip() or result.stdout.strip())
            )
        for name in DOCX_NAMES:
            current = SUBMISSION / name
            fresh = fresh_dir / name
            differences = _docx_differences(current, fresh)
            if differences:
                raise GateError(
                    f"submission DOCX is stale: {name} "
                    f"(changed parts: {', '.join(differences[:10])})"
                )
    print("SUBMISSION PACKAGE: PASS (fresh DOCX parts and figure hashes)")


def _submission_artifact_paths() -> list[Path]:
    artifacts = [SUBMISSION / name for name in DOCX_NAMES]
    artifacts.extend(SUBMISSION / "figures" / name for name in REQUIRED_FIGURES)
    return sorted(artifacts)


def write_submission_manifest(summary: dict) -> None:
    validate_analysis_manifest(summary)
    artifacts = _submission_artifact_paths()
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_type": "jech_submission_bundle",
        "analysis_manifest_sha256": _sha256(ANALYSIS_MANIFEST),
        "artifacts": [_artifact_record(path) for path in artifacts],
        "checks": summary,
    }
    _atomic_json(SUBMISSION_MANIFEST, payload)
    print(f"SUBMISSION MANIFEST: wrote {SUBMISSION_MANIFEST.relative_to(ROOT)}")


def validate_submission_manifest(expected_summary: dict | None = None) -> None:
    if not SUBMISSION_MANIFEST.is_file():
        raise GateError(
            "submission success manifest is absent; "
            "run python3 code/run_all.py --submission"
        )
    try:
        payload = json.loads(SUBMISSION_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read submission manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise GateError("submission manifest must be a JSON object")
    errors = []
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("wrong submission manifest schema_version")
    if payload.get("manifest_type") != "jech_submission_bundle":
        errors.append("wrong submission manifest type")
    if payload.get("analysis_manifest_sha256") != _sha256(ANALYSIS_MANIFEST):
        errors.append("submission manifest points to a stale analysis manifest")
    errors.extend(
        _validate_records(
            payload.get("artifacts"),
            "artifacts",
            _relative_paths(_submission_artifact_paths()),
        )
    )
    if expected_summary is not None and payload.get("checks") != expected_summary:
        errors.append("recorded check summary does not match current checks")
    if errors:
        raise GateError("stale/invalid submission manifest: " + "; ".join(errors))
    print("SUBMISSION MANIFEST: PASS")


def run_checks() -> dict:
    counts = check_output_contract()
    check_template_literals()
    document = check_rendered_reports()
    return {"counts": counts, "document": document}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed stale-number and reporting provenance gate."
    )
    parser.add_argument(
        "--begin-run",
        action="store_true",
        help="Invalidate old success manifests and create a run marker.",
    )
    parser.add_argument(
        "--refresh-manifest",
        action="store_true",
        help="After a fresh full run, atomically write ANALYSIS_MANIFEST.json.",
    )
    parser.add_argument(
        "--submission",
        action="store_true",
        help="Also verify fresh DOCX/figures and the submission manifest.",
    )
    parser.add_argument(
        "--refresh-submission-manifest",
        action="store_true",
        help="Write the submission success manifest after package verification.",
    )
    parser.add_argument(
        "--discover-literals",
        action="store_true",
        help="Print the currently discovered template literal counts as TSV.",
    )
    args = parser.parse_args(argv)

    other_actions = (
        args.refresh_manifest
        or args.submission
        or args.refresh_submission_manifest
    )
    if args.begin_run and (args.discover_literals or other_actions):
        parser.error("--begin-run cannot be combined with another action")
    if args.discover_literals and other_actions:
        parser.error("--discover-literals cannot be combined with another action")
    if args.refresh_submission_manifest and not args.submission:
        parser.error("--refresh-submission-manifest requires --submission")

    try:
        if args.begin_run:
            begin_analysis_run()
            return 0

        if args.discover_literals:
            print("path\ttoken\tcount")
            for (path, token), count in sorted(discover_template_literals().items()):
                print(f"{path}\t{token}\t{count}")
            return 0

        # A refresh request is itself an attempt to replace the success marker.
        # Invalidate the old marker before any checks so a failed refresh cannot
        # leave an apparently current success file behind.
        if args.refresh_manifest:
            ANALYSIS_MANIFEST.unlink(missing_ok=True)
            SUBMISSION_MANIFEST.unlink(missing_ok=True)
        if args.refresh_submission_manifest:
            SUBMISSION_MANIFEST.unlink(missing_ok=True)

        summary = run_checks()
        if args.refresh_manifest:
            try:
                write_analysis_manifest(summary)
                validate_analysis_manifest(summary)
            except Exception:
                ANALYSIS_MANIFEST.unlink(missing_ok=True)
                SUBMISSION_MANIFEST.unlink(missing_ok=True)
                raise
        else:
            validate_analysis_manifest(summary)

        if args.submission:
            check_submission_package()
            if args.refresh_submission_manifest:
                try:
                    write_submission_manifest(summary)
                    validate_submission_manifest(summary)
                except Exception:
                    SUBMISSION_MANIFEST.unlink(missing_ok=True)
                    raise
            else:
                validate_submission_manifest(summary)
    except (
        GateError,
        OSError,
        ValueError,
        KeyError,
        ElementTree.ParseError,
        subprocess.SubprocessError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"REPORTING GATE FAILED: {exc}", file=sys.stderr)
        return 1

    print("REPORTING GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
