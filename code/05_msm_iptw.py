"""05_msm_iptw — stabilised IPTW+IPCW marginal structural model, the
concurrent-confounder-adjusted contrast, and the balance diagnostics.

Port of 05_msm_iptw.do. Single source of truth for all model estimates.
Produces: table2.csv, weight_diagnostics.csv, positivity.csv,
sensitivity_censoring.csv, sensitivity_weights.csv, weight_balance.csv,
weight_balance_stratified.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C
from pyelsa import io
from pyelsa import models as M

BASE_FACTORS = C.BASELINE_FACTORS
BASE_CONT = C.BASELINE_CONT


# ---------------------------------------------------------------------------
# TV confounder construction (mirrors 05 section 2), on the panel.
# ---------------------------------------------------------------------------
def build_tv(p):
    cvd = p[["hibpe", "hearte", "stroke", "diabe"]]
    p["cvd_any_tv"] = (cvd == 1).any(axis=1).astype(float)
    p.loc[cvd.isna().all(axis=1), "cvd_any_tv"] = np.nan
    p["smoke_now_tv"] = np.where(p["smoken"].notna(), (p["smoken"] == 1).astype(float), np.nan)
    p["any_mobil_tv"] = np.where(p["mobilba"].notna(), (p["mobilba"] == 1).astype(float), np.nan)
    p["any_adl_tv"] = np.where(p["adlwaa"].notna(), (p["adlwaa"] == 1).astype(float), np.nan)
    p["any_iadl_tv"] = np.where(p["iadlaa"].notna(), (p["iadlaa"] == 1).astype(float), np.nan)
    p["poor_sight_tv"] = np.where(p["sight"].notna(), p["sight"].between(4, 6).astype(float), np.nan)
    p["poor_hear_tv"] = np.where(p["hearing"].notna(), p["hearing"].between(4, 6).astype(float), np.nan)
    for v in ["imrc", "dlrc", "orient"]:
        p.loc[p[v] < 0, v] = np.nan
    p["cog_tv"] = io.rowmean(pd.concat(
        [io.zstd(p["imrc"]), io.zstd(p["dlrc"]), io.zstd(p["orient"])], axis=1))
    return p


def design(df, factors, conts, extra):
    return io.build_design(df, factors, conts, extra=extra)


def fit_weights(p):
    """Reproduce the stabilised IPTW*IPCW cumulative weight (05 sections 4-6)."""
    p = p.sort_values(["idauniq", "wave"]).reset_index(drop=True)
    p["arts3_lag"] = p.groupby("idauniq")["arts3"].shift(1)
    age = [("agey", p["agey"].astype(float)), ("agey2", p["agey"].astype(float) ** 2)]

    base = io.build_design(p, BASE_FACTORS, BASE_CONT, extra=age)
    lagd = io.build_design(p, ["arts3_lag"], [])
    Xnum = pd.concat([lagd, base], axis=1)
    tv = io.build_design(p, C.TV_FACTORS, C.TV_CONT)
    Xden = pd.concat([Xnum, tv], axis=1)

    in_trt = (p["wave"] >= 3) & p["arts3"].notna() & p["arts3_lag"].notna() & p["agey"].notna()

    def _std(Xm):
        mu = Xm.mean(0); sd = Xm.std(0); sd[sd == 0] = 1.0
        return (Xm - mu) / sd

    def fit_mnl(mask, X):
        m = mask & X.notna().all(axis=1)
        Xs = _std(X[m].values)   # standardise for optimiser conditioning
        theta, p1 = M.mnlogit_fit(Xs, p.loc[m, "arts3"].values)
        pred = M.mnlogit_predict(theta, Xs, p1)   # probs invariant to rescaling
        return m, pred

    mnum, Pnum = fit_mnl(in_trt, Xnum)
    mden, Pden = fit_mnl(in_trt, Xden)
    p["p_num"] = np.nan
    p.loc[mnum, "p_num"] = Pnum[np.arange(mnum.sum()), p.loc[mnum, "arts3"].astype(int)]
    p["p_den"] = np.nan
    p.loc[mden, "p_den"] = Pden[np.arange(mden.sum()), p.loc[mden, "arts3"].astype(int)]
    for k in range(3):
        p.loc[mden, f"denp_{k}"] = Pden[:, k]
    p["w_trt"] = p["p_num"] / p["p_den"]
    p.loc[p["wave"] == 2, "w_trt"] = 1.0

    p["not_cens"] = 1 - p["censored_next"]
    in_cens = p["arts3"].notna() & p["agey"].notna() & p["not_cens"].notna()
    artsd = io.build_design(p, ["arts3"], [])
    Xcnum = pd.concat([artsd, base], axis=1)
    Xcden = pd.concat([Xcnum, tv], axis=1)

    def fit_lg(mask, X):
        m = mask & X.notna().all(axis=1)
        r = M.glm_binomial(p.loc[m, "not_cens"].values, _std(X[m].values), link="logit")
        return m, r["mu"]

    mcn, pcn = fit_lg(in_cens, Xcnum)
    mcd, pcd = fit_lg(in_cens, Xcden)
    p["pc_num"] = np.nan; p.loc[mcn, "pc_num"] = pcn
    p["pc_den"] = np.nan; p.loc[mcd, "pc_den"] = pcd
    p["w_cens_raw"] = p["pc_num"] / p["pc_den"]
    p["w_cens"] = p.groupby("idauniq")["w_cens_raw"].shift(1)
    p.loc[p["wave"] == 2, "w_cens"] = 1.0

    p["w_combined"] = p["w_trt"] * p["w_cens"]
    # Cumulative product within person, propagating missingness forward: once a
    # weight is missing, every later person-wave is excluded (project rule 10).
    # pandas cumprod defaults to skipna=True, which would step over gaps, so
    # force skipna=False.
    p["cum_weight_raw"] = p.groupby("idauniq")["w_combined"].transform(
        lambda s: s.cumprod(skipna=False))
    lo, hi = np.nanpercentile(p["cum_weight_raw"], [1, 99])
    p["cum_weight"] = p["cum_weight_raw"].clip(lo, hi)
    lo5, hi5 = np.nanpercentile(p["cum_weight_raw"], [5, 95])
    p["cum_weight_t595"] = p["cum_weight_raw"].clip(lo5, hi5)
    p["in_trt"] = in_trt
    return p


HAZ_LEVELS = [2, 3, 4, 5, 68, 910]


def outcome_design(df, arts_col):
    age = [("agey", df["agey"].astype(float)), ("agey2", df["agey"].astype(float) ** 2)]
    haz = df["wave"].map(C.hazard_period)
    hazd = io.dummies(haz.rename("haz"), HAZ_LEVELS)
    artsd = io.build_design(df, [arts_col], [], factor_levels={arts_col: [0, 1, 2]})
    base = io.build_design(df, BASE_FACTORS, BASE_CONT, extra=age)
    X = pd.concat([artsd.reset_index(drop=True), base.reset_index(drop=True),
                   hazd.reset_index(drop=True)], axis=1)
    return X, [f"{arts_col}_1", f"{arts_col}_2"]


def fit_cloglog(df, arts_col, tv_cols=None, weights=None):
    X, arts_names = outcome_design(df, arts_col)
    if tv_cols is not None:
        tvd = io.build_design(df, C.TV_FACTORS, C.TV_CONT).reset_index(drop=True)
        X = pd.concat([X, tvd], axis=1)
    off = np.log(df["interval_years"].values)
    keep = X.notna().all(axis=1).values & np.isfinite(off)
    Xk = X[keep]
    y = df["died_in_interval"].values[keep]
    w = None if weights is None else np.asarray(weights)[keep]
    r = M.glm_binomial(y, Xk.values, link="cloglog", offset=off[keep], weights=w,
                       cluster=df["idauniq"].values[keep])
    # beta is [intercept, X columns]; column j -> beta[j+1]
    idx = {name: list(Xk.columns).index(name) + 1 for name in arts_names}
    n = int(keep.sum()); d = int(y.sum())
    out = {}
    for lev, name in zip((1, 2), arts_names):
        b, se = r["beta"][idx[name]], r["se"][idx[name]]
        out[lev] = M.hr_ci(b, se)
    return out, n, d


def cox_row(df, arts_levels_cols, entry, exit_, event, cluster=None):
    r = M.cox_ph(df.values, entry, exit_, event, cluster=cluster)
    out = {}
    for lev, name in arts_levels_cols.items():
        i = list(df.columns).index(name)
        out[lev] = M.hr_ci(r["beta"][i], r["se"][i])
    return out, r["n"], r["n_events"]


def fmt(x):
    return f"{x:.2f}"


def build():
    p = io.read_dta(C.DATA / "fancourt_panel.dta")
    base = io.read_dta(C.DATA / "fancourt_baseline.dta")
    p = build_tv(p)
    bmerge = base[["idauniq"] + BASE_FACTORS + BASE_CONT + ["r2agey"]]
    p = p.merge(bmerge, on="idauniq", how="left", suffixes=("", "_b"))
    p = fit_weights(p)

    p["ln_interval"] = np.log(p["interval_years"])
    p["in_outcome"] = p["cum_weight"].notna() & (p["interval_years"] > 0)
    oc = p[p["in_outcome"]].copy()

    # arts3 fixed at baseline value (for baseline-fixed cloglog on the panel)
    oc = oc.merge(base[["idauniq", "arts3"]].rename(columns={"arts3": "arts3_baseline"}),
                  on="idauniq", how="left")

    rows = []
    # (a) full-sample baseline-fixed Cox
    Xb = io.build_design(base, ["arts3"] + BASE_FACTORS, BASE_CONT,
                         factor_levels={**C.FACTOR_LEVELS})
    cox_b, nb, db = cox_row(Xb, {1: "arts3_1", 2: "arts3_2"},
                            base["r2agey"].values, (base["r2agey"] + base["fu_years"]).values,
                            (base["died"] == 1).values)
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        hr, lo, hi = cox_b[lev]
        rows.append(("Baseline-fixed Cox", lab, hr, lo, hi, nb, db))

    # (b) time-varying Cox (04 model C-cat), own sample/covariates
    tvc = tv_cox(base)
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        hr, lo, hi, ntv, dtv = tvc[lev]
        rows.append(("Time-varying Cox", lab, hr, lo, hi, ntv, dtv))

    # (a2) baseline-fixed cloglog on the panel
    bf, n_bf, d_bf = fit_cloglog(oc, "arts3_baseline")
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        hr, lo, hi = bf[lev]
        rows.append(("Baseline-fixed cloglog (panel)", lab, hr, lo, hi, n_bf, d_bf))

    # (b) unweighted time-varying cloglog
    uw, n_uw, d_uw = fit_cloglog(oc, "arts3")
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        hr, lo, hi = uw[lev]
        rows.append(("Unweighted discrete-time PH", lab, hr, lo, hi, n_uw, d_uw))

    # (b2) concurrent-confounder-adjusted cloglog
    nv, n_nv, d_nv = fit_cloglog(oc, "arts3", tv_cols=True)
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        hr, lo, hi = nv[lev]
        rows.append(
            (
                "Concurrent-confounder-adjusted PH",
                lab,
                hr,
                lo,
                hi,
                n_nv,
                d_nv,
            )
        )

    # (c) MSM IPTW+IPCW cloglog
    msm, n_msm, d_msm = fit_cloglog(oc, "arts3", weights=oc["cum_weight"].values)
    for lev, lab in ((1, "Infrequent"), (2, "Frequent")):
        hr, lo, hi = msm[lev]
        rows.append(("MSM IPTW+IPCW cloglog", lab, hr, lo, hi, n_msm, d_msm))

    C.TABLES.mkdir(parents=True, exist_ok=True)
    with open(C.TABLES / "table2.csv", "w") as f:
        f.write("Model,Exposure,HR,CI_low,CI_high,N,Deaths,Metric\n")
        for mdl, lab, hr, lo, hi, n, d in rows:
            f.write(f"{mdl},{lab},{fmt(hr)},{fmt(lo)},{fmt(hi)},{n},{d},HR\n")

    write_diagnostics(p, oc, n_msm, msm)
    write_balance(oc)
    write_stratified_balance(oc)
    write_sensitivity(oc, msm, n_msm)
    print("05 complete: table2 + diagnostics written")
    return p, oc


def tv_cox(base):
    """Time-varying Cox (04 model C-cat) re-estimated for the table2 row."""
    p = io.read_dta(C.DATA / "fancourt_panel.dta")
    p = p[p["observed"] == 1].copy()
    bm = base[["idauniq", "female", "white", "married", "edu4", "wealth5", "working",
               "poor_sight", "poor_hearing", "r2psyche"]]
    p = p.merge(bm, on="idauniq", how="left")
    for v in ["hibpe", "hearte", "stroke", "diabe", "smoken", "mobilba", "adlwaa",
              "iadlaa", "sight", "hearing", "imrc", "dlrc", "orient", "cesd_w",
              "cancre", "lunge"]:
        p.loc[p[v] < 0, v] = np.nan
    cvd = p[["hibpe", "hearte", "stroke", "diabe"]]
    p["cvd_any"] = (cvd == 1).any(axis=1).astype(float)
    p.loc[cvd.isna().all(axis=1), "cvd_any"] = np.nan
    p["smoke_now"] = np.where(p["smoken"].notna(), (p["smoken"] == 1).astype(float), np.nan)
    p["any_mobil"] = np.where(p["mobilba"].notna(), (p["mobilba"] == 1).astype(float), np.nan)
    p["any_adl"] = np.where(p["adlwaa"].notna(), (p["adlwaa"] == 1).astype(float), np.nan)
    p["any_iadl"] = np.where(p["iadlaa"].notna(), (p["iadlaa"] == 1).astype(float), np.nan)
    p["poor_sight_w"] = np.where(p["sight"].notna(), p["sight"].between(4, 6).astype(float), np.nan)
    p["poor_hear_w"] = np.where(p["hearing"].notna(), p["hearing"].between(4, 6).astype(float), np.nan)
    p["cog_mean_w"] = io.rowmean(pd.concat(
        [io.zstd(p["imrc"]), io.zstd(p["dlrc"]), io.zstd(p["orient"])], axis=1))
    p["entry_age"] = p["r2agey"] + (p["start_year"] - p["baseline_year"])
    p["exit_age"] = p["r2agey"] + (p["stop_year"] - p["baseline_year"])
    p = p[p["entry_age"].notna() & p["exit_age"].notna() & (p["exit_age"] > p["entry_age"])].copy()

    fac = ["female", "white", "married", "edu4", "wealth5", "working",
           "poor_sight_w", "poor_hear_w", "r2psyche", "cancre", "lunge", "cvd_any",
           "smoke_now", "any_mobil", "any_adl", "any_iadl"]
    X = io.build_design(p, ["arts3"] + fac, ["cesd_w", "cog_mean_w"],
                        factor_levels={"arts3": [0, 1, 2], "edu4": [1, 2, 3, 4],
                                       "wealth5": [1, 2, 3, 4, 5]})
    keep = X.notna().all(axis=1).values
    Xk = X[keep].reset_index(drop=True)
    pk = p[keep].reset_index(drop=True)
    r = M.cox_ph(Xk.values, pk["entry_age"].values, pk["exit_age"].values,
                 (pk["died_in_interval"] == 1).values, cluster=pk["idauniq"].values)
    out = {}
    n, d = r["n"], r["n_events"]
    for lev, name in ((1, "arts3_1"), (2, "arts3_2")):
        i = list(Xk.columns).index(name)
        hr, lo, hi = M.hr_ci(r["beta"][i], r["se"][i])
        out[lev] = (hr, lo, hi, n, d)
    return out


def write_diagnostics(p, oc, n_msm, msm):
    w = oc["cum_weight"]
    ess = w.sum() ** 2 / (w ** 2).sum()
    n_missing = int(p["cum_weight"].isna().sum())
    q = {k: np.percentile(w, k) for k in (1, 5, 25, 50, 75, 95, 99)}
    with open(C.TABLES / "weight_diagnostics.csv", "w") as f:
        f.write("stat,value\n")
        f.write(f"mean,{w.mean():.3f}\nsd,{w.std(ddof=1):.3f}\n")
        f.write(f"min,{w.min():.3f}\nmax,{w.max():.3f}\n")
        for k in (1, 5, 25, 50, 75, 95, 99):
            f.write(f"p{k},{q[k]:.3f}\n")
        f.write(f"n_outcome,{n_msm}\nn_missing_weight,{n_missing}\n")
        f.write(f"ess,{ess:.0f}\ness_ratio,{ess / n_msm:.3f}\n")
        f.write("weight_type,IPTW x IPCW (stabilised truncated 1/99)\n")
    # positivity
    with open(C.TABLES / "positivity.csv", "w") as f:
        f.write("exposure,min_pred_prob\n")
        for k, lab in ((0, "Never"), (1, "Infrequent"), (2, "Frequent")):
            mn = p.loc[p["in_trt"], f"denp_{k}"].min()
            f.write(f"{lab},{mn:.4f}\n")


def _smd(df, v, hi, lo, wt=None):
    a = df[df["arts3"] == hi]; b = df[df["arts3"] == lo]
    psd = np.sqrt((a[v].std(ddof=1) ** 2 + b[v].std(ddof=1) ** 2) / 2)
    if psd == 0 or np.isnan(psd):
        return np.nan
    if wt is None:
        return (a[v].mean() - b[v].mean()) / psd
    am = np.average(a[v].dropna(), weights=a.loc[a[v].notna(), wt])
    bm = np.average(b[v].dropna(), weights=b.loc[b[v].notna(), wt])
    return (am - bm) / psd


def _numerator_adjusted_smd(df, v, hi, lo, wt=None):
    """Regression-adjusted SMD conditional on the stabilised numerator.

    Jackson's Diagnostic 3 conditions balance metrics on exposure history and,
    when present in both weight models, baseline covariates. We stratify on the
    prior-wave exposure outside this function and regress each time-varying
    confounder on current exposure, current age, age squared, and the full
    baseline covariate set used by the treatment-weight numerator. The current-
    exposure coefficient is divided by the unweighted pooled SD for the same
    exposure contrast and stratum.
    """
    pair = df[df["arts3"].isin([hi, lo])].copy().reset_index(drop=True)
    age = [
        ("agey", pair["agey"].astype(float)),
        ("agey2", pair["agey"].astype(float) ** 2),
    ]
    numerator = io.build_design(
        pair, BASE_FACTORS, BASE_CONT, extra=age
    ).reset_index(drop=True)
    exposure = (pair["arts3"] == hi).astype(float).rename("exposure")
    design = pd.concat([exposure, numerator], axis=1)
    keep = pair[v].notna() & design.notna().all(axis=1)
    if wt is not None:
        keep &= pair[wt].notna() & (pair[wt] > 0)
    if not keep.any():
        return np.nan, 0

    y = pair.loc[keep, v].to_numpy(dtype=float)
    X = np.column_stack(
        [np.ones(int(keep.sum())), design.loc[keep].to_numpy(dtype=float)]
    )
    if wt is None:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
    else:
        weights = pair.loc[keep, wt].to_numpy(dtype=float)
        root_weight = np.sqrt(weights / weights.mean())
        beta = np.linalg.lstsq(
            X * root_weight[:, None], y * root_weight, rcond=None
        )[0]

    used = pair.loc[keep]
    high_values = used.loc[used["arts3"] == hi, v]
    low_values = used.loc[used["arts3"] == lo, v]
    pooled_sd = np.sqrt(
        (high_values.std(ddof=1) ** 2 + low_values.std(ddof=1) ** 2) / 2
    )
    if pooled_sd == 0 or np.isnan(pooled_sd):
        return np.nan, int(keep.sum())
    return beta[1] / pooled_sd, int(keep.sum())


def write_balance(oc):
    with open(C.TABLES / "weight_balance.csv", "w") as f:
        f.write("covariate,smd_unweighted,smd_weighted,n_used\n")
        for v in C.BALANCE_CONFOUNDERS:
            su = _smd(oc, v, 2, 0)
            sw = _smd(oc, v, 2, 0, "cum_weight")
            n = int((oc["arts3"] == 2).sum() + (oc["arts3"] == 0).sum())
            f.write(f"{v},{su:.3f},{sw:.3f},{n}\n")


def write_stratified_balance(oc):
    strata = [("pooled", oc["arts3"].notna()), ("lag_never", oc["arts3_lag"] == 0),
              ("lag_infrequent", oc["arts3_lag"] == 1), ("lag_frequent", oc["arts3_lag"] == 2)]
    with open(C.TABLES / "weight_balance_stratified.csv", "w") as f:
        f.write(
            "stratum,contrast,covariate,"
            "smd_raw_unweighted,smd_raw_weighted,"
            "smd_adjusted_unweighted,smd_adjusted_weighted,"
            "n_hi,n_lo,n_adjusted\n"
        )
        for sname, cond in strata:
            for con, cname in ((2, "freq_vs_never"), (1, "infreq_vs_never")):
                sub = oc[cond]
                for v in C.BALANCE_CONFOUNDERS:
                    raw_u = _smd(sub, v, con, 0)
                    raw_w = _smd(sub, v, con, 0, "cum_weight")
                    adj_u, n_adjusted_u = _numerator_adjusted_smd(
                        sub, v, con, 0
                    )
                    adj_w, n_adjusted_w = _numerator_adjusted_smd(
                        sub, v, con, 0, "cum_weight"
                    )
                    if n_adjusted_u != n_adjusted_w:
                        raise AssertionError(
                            "adjusted balance samples differ before and after "
                            f"weighting for {(sname, cname, v)}"
                        )
                    nh = int((sub["arts3"] == con).sum()); nl = int((sub["arts3"] == 0).sum())
                    values = (raw_u, raw_w, adj_u, adj_w)
                    fields = ["" if np.isnan(x) else f"{x:.4f}" for x in values]
                    f.write(
                        f"{sname},{cname},{v},{','.join(fields)},"
                        f"{nh},{nl},{n_adjusted_u}\n"
                    )


def write_sensitivity(oc, msm, n_msm):
    # censoring sensitivity
    terminal = oc["censored_next"] == 1
    known_alive = terminal & oc["next_iwstat"].isin([1, 4])
    unknown = terminal & (oc["next_iwstat"] == 9)
    terminal_total = int(terminal.sum())
    known_alive_n = int(known_alive.sum())
    unknown_n = int(unknown.sum())
    if known_alive_n + unknown_n != terminal_total:
        raise AssertionError(
            "terminal censoring status counts do not sum to the terminal total"
        )
    known_alive_pct = 100 * known_alive_n / terminal_total
    unknown_pct = 100 * unknown_n / terminal_total
    keep = ~unknown
    sub = oc[keep]
    s, ns, ds = fit_cloglog(sub, "arts3", weights=sub["cum_weight"].values)
    n_removed = int((~keep).sum())
    hr, lo, hi = msm[2]
    hs, ls, hs2 = s[2]
    with open(C.TABLES / "sensitivity_censoring.csv", "w") as f:
        f.write(
            "spec,HR,CI_low,CI_high,N,n_removed,terminal_total,"
            "known_alive_next,unknown_next,known_alive_pct,unknown_pct\n"
        )
        diagnostics = (
            f"{terminal_total},{known_alive_n},{unknown_n},"
            f"{known_alive_pct:.1f},{unknown_pct:.1f}"
        )
        f.write(
            f"MSM primary (full outcome sample),{fmt(hr)},{fmt(lo)},{fmt(hi)},"
            f"{n_msm},0,{diagnostics}\n"
        )
        f.write("MSM unknown-status terminal intervals censored at last interview,"
                f"{fmt(hs)},{fmt(ls)},{fmt(hs2)},{ns},{n_removed},{diagnostics}\n")
    # weight-truncation sensitivity
    raw, nr, dr = fit_cloglog(oc, "arts3", weights=oc["cum_weight_raw"].values)
    t595, n5, d5 = fit_cloglog(oc, "arts3", weights=oc["cum_weight_t595"].values)
    with open(C.TABLES / "sensitivity_weights.csv", "w") as f:
        f.write("truncation,HR,CI_low,CI_high,max_weight\n")
        f.write(f"Untruncated,{fmt(raw[2][0])},{fmt(raw[2][1])},{fmt(raw[2][2])},"
                f"{oc['cum_weight_raw'].max():.2f}\n")
        f.write(f"1st/99th percentile (primary),{fmt(hr)},{fmt(lo)},{fmt(hi)},"
                f"{oc['cum_weight'].max():.2f}\n")
        f.write(f"5th/95th percentile,{fmt(t595[2][0])},{fmt(t595[2][1])},{fmt(t595[2][2])},"
                f"{oc['cum_weight_t595'].max():.2f}\n")


if __name__ == "__main__":
    build()
