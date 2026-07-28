"""01_build_sample — wave-2 baseline analytic sample and mortality endpoint.

Port of 01_build_sample.do. Produces:
  data/fancourt_baseline.parquet
  output/tables/baseline_missingness.csv

The reporting gate verifies the resulting sample and death counts against the
reviewed analysis contract after a complete run.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyelsa import config as C
from pyelsa import io

WAVE_YEAR = C.WAVE_YEAR
SEASON_OFFSET = {1: 0.125, 2: 0.375, 3: 0.625, 4: 0.875}


def build_arts_w2():
    df = io.read_dta(C.WAVES / C.WAVE_FILES[2], columns=["idauniq", "scacta", "scactc", "scactd"])
    io.clean_sentinels(df, ["scactc", "scactd"])
    df["arts_freq"] = df[["scactc", "scactd"]].min(axis=1, skipna=True)
    df["arts3"] = np.select(
        [df["arts_freq"] == 6, df["arts_freq"].isin([4, 5]), df["arts_freq"].isin([1, 2, 3])],
        [0, 1, 2], default=np.nan)
    return df


def build():
    arts = build_arts_w2()

    iwcols = [f"r{w}iwstat" for w in range(2, 11)]
    cols = (["idauniq", "ragender", "raracem", "raeduc_e", "r2agey", "r2mstat",
             "r2lbrf_e", "h2atotb", "r2proxy", "r2wtresp", "r2sight", "r2hearing",
             "r2cesd", "r2psyche", "r2cancre", "r2lunge", "r2hearte", "r2stroke",
             "r2hibpe", "r2diabe", "r2arthre", "r2osteoe", "r2smoken", "r2drinkd_e",
             "r2mobilba", "r2adlwaa", "r2iadlaa", "r2imrc", "r2dlrc", "r2orient"]
            + iwcols)
    df = io.read_dta(C.HARM, columns=cols)

    df = df[df["r2iwstat"] == 1].copy()
    print(f"Wave 2 respondents (r2iwstat==1): {len(df)}")
    df = df[
        (df["r2agey"] >= C.BASELINE_MIN_AGE) & df["r2agey"].notna()
    ].copy()
    print(f"Wave 2 age {C.BASELINE_MIN_AGE}+: {len(df)}")
    df = df.merge(arts[["idauniq", "arts3", "arts_freq", "scacta", "scactc", "scactd"]],
                  on="idauniq", how="inner")
    print(f"With arts engagement data: {len(df)}")

    io.clean_sentinels(df, ["ragender", "raracem", "r2mstat", "raeduc_e", "r2lbrf_e",
                            "r2sight", "r2hearing", "r2cesd", "r2cancre", "r2lunge",
                            "r2hearte", "r2stroke", "r2hibpe", "r2diabe", "r2arthre",
                            "r2osteoe", "r2psyche", "r2smoken", "r2drinkd_e", "r2mobilba",
                            "r2adlwaa", "r2iadlaa", "r2imrc", "r2dlrc", "r2orient"])

    df["female"] = np.where(df["ragender"].notna(), (df["ragender"] == 2).astype(float), np.nan)
    df["white"] = np.where(df["raracem"].notna(), (df["raracem"] == 1).astype(float), np.nan)
    df["married"] = np.where(df["r2mstat"].notna(), df["r2mstat"].isin([1, 3]).astype(float), np.nan)
    df["edu4"] = np.select(
        [df["raeduc_e"] <= 2, df["raeduc_e"] == 3, df["raeduc_e"] == 4, df["raeduc_e"] >= 5],
        [1, 2, 3, 4], default=np.nan)
    df["wealth5"] = io.xtile(df["h2atotb"], 5)
    df["working"] = np.where(df["r2lbrf_e"].notna(), df["r2lbrf_e"].isin([1, 2]).astype(float), np.nan)
    df["poor_sight"] = np.where(df["r2sight"].notna(), df["r2sight"].between(4, 6).astype(float), np.nan)
    df["poor_hearing"] = np.where(df["r2hearing"].notna(), df["r2hearing"].between(4, 6).astype(float), np.nan)

    cvd = df[["r2hibpe", "r2hearte", "r2stroke", "r2diabe"]]
    df["cvd_any"] = (cvd == 1).any(axis=1).astype(float)
    df.loc[cvd.isna().all(axis=1), "cvd_any"] = np.nan
    ltc = df[["r2arthre", "r2osteoe"]]
    df["other_ltc"] = (ltc == 1).any(axis=1).astype(float)
    df.loc[ltc.isna().all(axis=1), "other_ltc"] = np.nan

    df["smoke_now"] = np.where(df["r2smoken"].notna(), (df["r2smoken"] == 1).astype(float), np.nan)
    df["alcfreq"] = df["r2drinkd_e"].where(df["r2drinkd_e"] >= 0)
    df["any_mobil"] = np.where(df["r2mobilba"].notna(), (df["r2mobilba"] == 1).astype(float), np.nan)
    df["any_adl"] = np.where(df["r2adlwaa"].notna(), (df["r2adlwaa"] == 1).astype(float), np.nan)
    df["any_iadl"] = np.where(df["r2iadlaa"].notna(), (df["r2iadlaa"] == 1).astype(float), np.nan)
    df["cesd"] = df["r2cesd"]
    df["cog_mean"] = io.rowmean(pd.concat(
        [io.zstd(df["r2imrc"]), io.zstd(df["r2dlrc"]), io.zstd(df["r2orient"])], axis=1))

    # ---- mortality endpoint ----
    df["died_wave"] = np.nan
    for w in range(3, 11):
        c = f"r{w}iwstat"
        mask = df["died_wave"].isna() & df[c].isin([5, 6])
        df.loc[mask, "died_wave"] = w
    df["last_alive_wave"] = 2.0
    df["last_interviewed_wave"] = 2.0
    df["last_contact_wave"] = 2.0
    for w in range(3, 11):
        c = f"r{w}iwstat"
        df.loc[df[c].isin([1, 4]), "last_alive_wave"] = w
        df.loc[df[c] == 1, "last_interviewed_wave"] = w
        df.loc[df[c].isin([1, 4, 5, 6, 7, 9]), "last_contact_wave"] = w

    eol = io.read_dta(C.EOL, columns=["idauniq", "raxyear", "raxseason"])
    df = df.merge(eol, on="idauniq", how="left", indicator="_eolm")
    df["in_eol_harm"] = (df["_eolm"] == "both").astype(int)
    df = df.drop(columns="_eolm")
    io.clean_sentinels(df, ["raxyear", "raxseason"])

    hcap = io.read_dta(C.EOL_W10, columns=["idauniq", "wave", "eidatey", "dveidates",
                                           "eidatlayy", "eidatlamm"])
    hcap = hcap.rename(columns={"wave": "hcap_last_productive_wave", "eidatey": "hcap_death_year",
                                "dveidates": "hcap_death_season", "eidatlayy": "hcap_last_ivw_year",
                                "eidatlamm": "hcap_last_ivw_month"})
    df = df.merge(hcap, on="idauniq", how="left", indicator="_hm")
    df["in_eol_hcap"] = (df["_hm"] == "both").astype(int)
    df = df.drop(columns="_hm")
    io.clean_sentinels(df, ["hcap_last_productive_wave", "hcap_death_year", "hcap_death_season",
                            "hcap_last_ivw_year", "hcap_last_ivw_month"])

    df["death_year_harm"] = df["raxyear"] + df["raxseason"].map(SEASON_OFFSET)
    df["death_year_hcap"] = df["hcap_death_year"] + df["hcap_death_season"].map(SEASON_OFFSET)
    df["died_wave_year"] = df["died_wave"].map(WAVE_YEAR)
    df["last_alive_year"] = df["last_alive_wave"].map(WAVE_YEAR)
    df["death_year_iwstat"] = np.where(df["died_wave_year"].notna(),
                                       (df["last_alive_year"] + df["died_wave_year"]) / 2, np.nan)

    df["death_year"] = df["death_year_hcap"]
    df["death_year"] = df["death_year"].fillna(df["death_year_harm"]).fillna(df["death_year_iwstat"])
    df["death_source"] = np.select(
        [df["death_year_hcap"].notna(),
         df["death_year_hcap"].isna() & df["death_year_harm"].notna(),
         df["death_year_hcap"].isna() & df["death_year_harm"].isna() & df["death_year_iwstat"].notna()],
        [1, 2, 3], default=np.nan)
    df["died"] = df["death_year"].notna().astype(int)

    df["exit_year"] = np.where(df["died"] == 1, df["death_year"], df["last_alive_year"])
    df["baseline_year"] = C.BASELINE_YEAR
    df["fu_years"] = df["exit_year"] - df["baseline_year"]
    df = df[(df["fu_years"] > 0) & df["fu_years"].notna()].copy()

    # ---- completeness + per-variable missingness ----
    covars = ["female", "white", "married", "edu4", "wealth5", "working", "poor_sight",
              "poor_hearing", "cesd", "r2psyche", "r2cancre", "r2lunge", "cvd_any",
              "other_ltc", "smoke_now", "alcfreq", "any_mobil", "any_adl", "any_iadl", "cog_mean"]
    n_elig = len(df)
    miss_rows = []
    for v in ["arts3"] + covars:
        nmiss = int(df[v].isna().sum())
        miss_rows.append({"variable": v, "n_eligible": n_elig, "n_missing": nmiss,
                          "pct_missing": f"{100 * nmiss / n_elig:.2f}"})
    C.TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(miss_rows).to_csv(C.TABLES / "baseline_missingness.csv", index=False)

    complete = df["arts3"].notna()
    for v in covars:
        complete &= df[v].notna()
    df = df[complete].copy()
    print(f"Final baseline sample: {len(df)}")
    assert 5500 < len(df) < 8000, f"baseline N={len(df)} outside expected range"

    keep = (["idauniq", "arts3", "arts_freq", "scactc", "scactd", "scacta", "r2agey",
             "female", "white", "married", "edu4", "wealth5", "working", "poor_sight",
             "poor_hearing", "cesd", "r2psyche", "r2cancre", "r2lunge", "r2hearte",
             "r2stroke", "r2hibpe", "r2diabe", "r2arthre", "r2osteoe", "cvd_any",
             "other_ltc", "smoke_now", "alcfreq", "any_mobil", "any_adl", "any_iadl",
             "cog_mean", "r2proxy", "r2wtresp", "died", "death_year", "death_source",
             "fu_years", "baseline_year", "exit_year", "last_alive_wave",
             "last_interviewed_wave", "last_contact_wave", "died_wave", "in_eol_harm",
             "in_eol_hcap", "hcap_last_productive_wave", "hcap_last_ivw_year",
             "hcap_last_ivw_month"])
    out = df[keep].reset_index(drop=True)
    C.DATA.mkdir(parents=True, exist_ok=True)
    io.save_dta(out, C.DATA / "fancourt_baseline.dta")
    print(f"Saved data/fancourt_baseline.dta  N={len(out)}  deaths={int(out['died'].sum())}")
    return out


if __name__ == "__main__":
    build()
