"""03_build_panel — monotone-censored person-wave panel.

Port of 03_build_panel.do. Produces:
  data/arts_long.dta
  data/fancourt_panel.dta

Each row is a person-wave interval [wave_t, wave_t+1). Monotone censoring:
once a person misses an interview or has no observed arts item, all later
waves are dropped. Wave-10 rows survive only as terminal death intervals.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C
from pyelsa import io

WY = C.WAVE_YEAR
SCHED_NEXT = {2: 2006.5, 3: 2008.5, 4: 2010.5, 5: 2012.5, 6: 2014.5,
              7: 2016.5, 8: 2018.5, 9: 2022.0}   # wave 10 has no scheduled next

TV_STUBS = ["iwstat", "agey", "mstat", "lbrf_e", "cesd", "cancre", "lunge",
            "hearte", "stroke", "hibpe", "diabe", "smoken", "mobilba", "adlwaa",
            "iadlaa", "imrc", "dlrc", "orient", "sight", "hearing", "proxy"]
RENAME = {"cesd": "cesd_w"}   # rcesd -> cesd_w; others keep stub name


def build_arts_long():
    frames = []
    for w, fname in C.WAVE_FILES.items():
        df = io.read_dta(C.WAVES / fname, columns=["idauniq", "scacta", "scactc", "scactd"])
        io.clean_sentinels(df, ["scacta", "scactc", "scactd"])
        df["wave"] = w
        df["arts_freq_w"] = df[["scactc", "scactd"]].min(axis=1, skipna=True)
        df["arts3_w"] = np.select(
            [df["arts_freq_w"] == 6, df["arts_freq_w"].isin([4, 5]), df["arts_freq_w"].isin([1, 2, 3])],
            [0, 1, 2], default=np.nan)
        frames.append(df[["idauniq", "wave", "arts3_w", "arts_freq_w"]])
    arts = pd.concat(frames, ignore_index=True)
    io.save_dta(arts, C.DATA / "arts_long.dta")
    return arts


def build():
    arts = build_arts_long()
    base = io.read_dta(C.DATA / "fancourt_baseline.dta")
    base_ids = set(base["idauniq"])

    # ---- pull wide TV covariates + constants, restrict to baseline ids ----
    const = ["idauniq", "ragender", "raracem", "raeduc_e", "r2wtresp"]
    wide_cols = list(const)
    for w in range(2, 11):
        for stub in TV_STUBS:
            pre = "h" if stub == "atotb" else "r"
            wide_cols.append(f"{pre}{w}{stub}")
    # atotb handled separately (h-prefix); add explicitly
    for w in range(2, 11):
        wide_cols.append(f"h{w}atotb")
    wide_cols = list(dict.fromkeys(wide_cols))  # dedupe, keep order
    wide = io.read_dta(C.HARM, columns=wide_cols)
    wide = wide[wide["idauniq"].isin(base_ids)].copy()

    # ---- reshape long over waves 2..10 ----
    long_frames = []
    stubs_all = TV_STUBS + ["atotb"]
    for w in range(2, 11):
        cols = {}
        for stub in stubs_all:
            pre = "h" if stub == "atotb" else "r"
            src = f"{pre}{w}{stub}"
            dst = RENAME.get(stub, stub)
            cols[dst] = wide[src]
        block = pd.DataFrame(cols)
        block["idauniq"] = wide["idauniq"].values
        block["wave"] = w
        long_frames.append(block)
    panel = pd.concat(long_frames, ignore_index=True)
    panel = panel.merge(wide[const], on="idauniq", how="left")

    io.clean_sentinels(panel, [RENAME.get(s, s) for s in TV_STUBS if s != "iwstat"]
                        + ["atotb"])

    # ---- monotone censoring: interviewed + observed arts, contiguous run ----
    panel = panel[panel["iwstat"] == 1].copy()
    panel = panel.merge(arts, on=["idauniq", "wave"], how="left")
    panel["arts3"] = panel["arts3_w"]
    panel = panel[panel["arts3"].notna()].copy()

    panel = panel.sort_values(["idauniq", "wave"]).reset_index(drop=True)
    g = panel.groupby("idauniq")["wave"]
    gap = (panel["wave"] != g.shift(1) + 1) & g.shift(1).notna()
    panel["_first_gap"] = gap.groupby(panel["idauniq"]).cumsum()
    panel = panel[panel["_first_gap"] == 0].drop(columns=["_first_gap"]).copy()
    panel["observed"] = 1

    # ---- death info from baseline ----
    bcols = ["idauniq", "died", "died_wave", "death_year", "death_source", "r2agey",
             "last_alive_wave", "last_interviewed_wave", "baseline_year",
             "hcap_last_productive_wave", "hcap_last_ivw_year", "hcap_last_ivw_month"]
    panel = panel.merge(base[bcols], on="idauniq", how="inner")
    panel = panel.sort_values(["idauniq", "wave"]).reset_index(drop=True)
    panel["last_panel_wave"] = panel.groupby("idauniq")["wave"].transform("max")

    # ---- next-wave iwstat from harmonised file ----
    iw = io.read_dta(C.HARM, columns=["idauniq"] + [f"r{w}iwstat" for w in range(2, 11)])
    panel = panel.merge(iw, on="idauniq", how="left")
    panel["next_iwstat"] = np.nan
    for w in range(2, 10):
        panel.loc[panel["wave"] == w, "next_iwstat"] = panel.loc[panel["wave"] == w, f"r{w+1}iwstat"]
    panel = panel.drop(columns=[f"r{w}iwstat" for w in range(2, 11)])

    panel["wave_year"] = panel["wave"].map(WY)
    panel["scheduled_next_year"] = panel["wave"].map(SCHED_NEXT)

    # ---- died_in_interval ----
    cond_evidence = (
        panel["next_iwstat"].isin([5, 6])
        | (panel["scheduled_next_year"].notna() & (panel["death_year"] <= panel["scheduled_next_year"]))
        | ((panel["wave"] == 10) & (panel["death_year"] > panel["wave_year"]))
    )
    hcap_ok = panel["hcap_last_productive_wave"].isna() | (
        panel["hcap_last_productive_wave"] == panel["last_panel_wave"])
    panel["died_in_interval"] = (
        (panel["died"] == 1) & (panel["wave"] == panel["last_panel_wave"])
        & cond_evidence & hcap_ok).astype(int)

    panel["censored_next"] = (
        (panel["wave"] == panel["last_panel_wave"]) & panel["scheduled_next_year"].notna()
        & (panel["died_in_interval"] == 0)).astype(int)

    # ---- drop wave-10 rows without a terminal death ----
    panel = panel[~((panel["wave"] == 10) & (panel["died_in_interval"] == 0))].copy()
    panel = panel.sort_values(["idauniq", "wave"]).reset_index(drop=True)

    # ---- start/stop/interval ----
    panel["start_year"] = panel["wave_year"]
    panel["next_wave_year"] = panel.groupby("idauniq")["wave_year"].shift(-1)
    stop = panel["next_wave_year"].copy()
    stop = stop.where(panel["died_in_interval"] != 1, panel["death_year"])
    clamp = (panel["died_in_interval"] == 1) & (stop <= panel["wave_year"])
    stop = stop.where(~clamp, panel["wave_year"] + 0.25)
    fill2 = stop.isna() & (panel["died_in_interval"] == 0) & (panel["wave"] <= 8)
    stop = stop.where(~fill2, panel["wave_year"] + 2.0)
    fill9 = stop.isna() & (panel["died_in_interval"] == 0) & (panel["wave"] == 9)
    stop = stop.where(~fill9, panel["wave_year"] + 3.5)
    panel["stop_year"] = stop
    panel["interval_years"] = panel["stop_year"] - panel["start_year"]

    assert (panel["interval_years"] > 0).all(), "non-positive interval_years"
    assert panel["stop_year"].notna().all(), "missing stop_year"
    assert panel["arts3"].notna().all(), "missing arts3"

    panel = panel.drop(columns=["next_wave_year", "last_panel_wave", "scheduled_next_year"])
    io.save_dta(panel, C.DATA / "fancourt_panel.dta")

    n_persons = panel["idauniq"].nunique()
    print(f"Panel person-waves: {len(panel)}  persons: {n_persons}")
    print(f"Death intervals: {int(panel['died_in_interval'].sum())}  "
          f"censored-next: {int(panel['censored_next'].sum())}")
    assert 20000 < len(panel) < 40000
    return panel


if __name__ == "__main__":
    build()
