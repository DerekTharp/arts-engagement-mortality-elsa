"""Data IO and design-matrix helpers shared across the pipeline."""
import numpy as np
import pandas as pd

from . import config


def read_dta(path, columns=None):
    """Read a Stata .dta without converting value labels (we work with the
    numeric codes, matching the Stata scripts)."""
    return pd.read_stata(path, convert_categoricals=False, columns=columns)


def save_dta(df, path):
    """Persist an intermediate as Stata-13 .dta (no extra dependencies, and
    still openable in Stata). Object columns that are all-NA are dropped to
    keep to_stata happy."""
    df.to_stata(path, write_index=False, version=117)


def clean_sentinels(df, cols):
    """Set harmonised negative missing sentinels (-1/-8/-9, any value < 0) to
    NaN, in place, for the given columns. Mirrors the `replace v = . if v < 0`
    blocks that precede every derived-variable construction in Stata."""
    for c in cols:
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c]):
            df.loc[df[c] < 0, c] = np.nan
    return df


def zstd(s):
    """egen std: standardise using the sample SD (ddof=1) over non-missing."""
    s = pd.Series(s, dtype=float)
    return (s - s.mean()) / s.std(ddof=1)


def rowmean(frame):
    """egen rowmean: mean across columns ignoring missing (NaN if all missing)."""
    return frame.mean(axis=1, skipna=True)


def _stata_pctile(xs, p):
    """p-th percentile using Stata's unweighted definition (methods & formulas).
    xs: sorted ascending numpy array of non-missing values."""
    N = len(xs)
    q = N * p / 100.0
    if abs(q - round(q)) < 1e-9:
        i = int(round(q))                      # 1-indexed x_(q), x_(q+1)
        return (xs[i - 1] + xs[i]) / 2.0
    return xs[int(np.floor(q))]                # 1-indexed x_(floor(q)+1)


def xtile(series, n=5):
    """Stata `xtile x, nq(n)`: cutpoints are the (100/n)-quantiles via Stata's
    pctile definition; an observation joins group 1 + #{cutpoints it exceeds},
    so values tied at a cutpoint fall in the lower group (Stata's convention)."""
    s = pd.Series(series, dtype=float)
    xs = np.sort(s.dropna().values)
    cuts = [_stata_pctile(xs, 100.0 * k / n) for k in range(1, n)]
    x = s.values
    grp = np.ones(len(x))
    for c in cuts:
        grp = grp + (x > c).astype(float)
    grp[np.isnan(x)] = np.nan
    return pd.Series(grp, index=s.index)


def dummies(series, levels):
    """Factor dummies dropping the first (base) level. NaN in -> all-NaN row."""
    s = pd.Series(series)
    cols = {}
    for lev in levels[1:]:
        col = (s == lev).astype(float)
        col[s.isna()] = np.nan
        cols[f"{series.name if hasattr(series, 'name') else 'x'}_{lev}"] = col.values
    return pd.DataFrame(cols, index=s.index)


def build_design(df, factors, conts, extra=None, factor_levels=None):
    """Assemble a model matrix (DataFrame) from factor and continuous columns.

    factors: binary or multi-level categoricals -> dummies (base dropped).
    conts:   continuous columns entered linearly.
    extra:   list of already-built numeric columns/arrays to append (e.g. age,
             age^2, PGS, PCs) as (name, array) tuples.
    Returns a DataFrame; rows with any NaN are the caller's responsibility to
    drop (matching Stata listwise deletion).
    """
    levels = factor_levels or config.FACTOR_LEVELS
    parts = []
    for f in factors:
        lv = levels.get(f)
        if lv is None:  # binary 0/1 factor -> single dummy = the column itself
            col = df[f].astype(float)
            parts.append(col.rename(f).to_frame())
        else:
            d = dummies(df[f].rename(f), lv)
            parts.append(d)
    if conts:
        parts.append(df[conts].astype(float))
    if extra:
        for name, arr in extra:
            parts.append(pd.Series(np.asarray(arr, float), index=df.index,
                                   name=name).to_frame())
    return pd.concat(parts, axis=1)
