"""Build the data behind The Leaky Loop from Eurostat's raw downloads.

Reads Eurostat datasets from data/raw/ and writes these tables to
data/processed/:

    ceilings_2022.csv        every country's circularity rate and how far
                             recycling alone could take it, in 2022
    trend.csv                the same measures in every waste reporting year
                             from 2010 to 2024
    trend_drivers.csv        what moved each country's rate from 2012 to 2022:
                             more recycling, or a change in consumption
    materials_2022.csv       what each country consumes, in kg per person a day
    loop_2022.csv            where each country's processed material goes:
                             built into stock, burned or eaten, exported, spread
                             on land, or back as waste
    footprint_2022.csv       what the EU's material footprint ends up as, and how
                             much of each is investment or spending (EU only)

Run from the repository root:

    python build_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/processed")

FILES = {
    "rate": "env_ac_cur_linear_2_0.csv",    # circular material use rate
    "mfa": "env_ac_mfa_linear_2_0.csv",     # material flow accounts
    "waste": "env_wastrt_linear_2_0.csv",   # treatment of waste
    "flows": "env_ac_sd_linear_2_0.csv",    # material flows for the circular economy
    "waste_by_material": "env_wassd_linear_2_0.csv",   # waste treated, by material
    "footprint": "env_ac_rmefd_linear_2_0.csv",        # material footprint by final use
}

YEAR = 2022                      # latest year where every figure is reported
REPORTING_YEARS = list(range(2010, 2025, 2))   # waste is reported in even years
TREND_FROM, TREND_TO = 2012, 2022
TARGETS = {"eu": 0.24, "ireland": 0.12}         # EU and Irish goals for 2030

# Soil and rock: soils, dredging spoils and other mineral waste (mostly from mining)
SOIL_AND_ROCK = ["W126", "W127", "W12B"]
WASTE_CODES = ["TOTAL", "TOT_X_MIN", "W121"] + SOIL_AND_ROCK
OPERATIONS = ["TRT", "RCV_R", "RCV_B"]          # treated, recycled, backfilled

# Material groups for consumption, built from Eurostat's material codes
MATERIAL_CODES = ["TOTAL", "MF1", "MF122", "MF2", "MF3", "MF38", "MF4", "MF5", "MF6"]

# Where processed material goes, from Eurostat's Sankey data; waste comes from env_wassd
LOOP_FLOWS = {
    "built_into_stock": "MAT_ACCUM",
    "burned_or_eaten": "EMIS",
    "exported": "EXP_X_RCV_R",
    "spread_on_land": "DFLOW",
}

# What the footprint ends up as: Eurostat's 63 product groups, grouped; the rest is services
FOOTPRINT_GROUPS = {
    "Buildings and infrastructure": ["CPA_F"],
    "Food": ["CPA_A01", "CPA_A03", "CPA_C10-12", "CPA_I"],   # restaurants and catering included
    "Energy and fuels": ["CPA_B", "CPA_C19", "CPA_D"],
    "Wood from forestry": ["CPA_A02"],
    "Vehicles, machinery and electronics": ["CPA_C26", "CPA_C27", "CPA_C28", "CPA_C29", "CPA_C30"],
    "Other manufactured goods": ["CPA_C13-15", "CPA_C16", "CPA_C17", "CPA_C18", "CPA_C20", "CPA_C21",
                                 "CPA_C22", "CPA_C23", "CPA_C24", "CPA_C25", "CPA_C31_32", "CPA_C33"],
}
# Investment is gross capital formation, households buying new homes included; spending is
# what households, governments and non-profits buy and use up
FINAL_USES = ["RMC", "RMC_P5", "RMC_P3", "RMC_P3_S14"]


def read_eurostat(name, columns, keep):
    """Read a Eurostat SDMX-CSV file in chunks, keeping only the rows we need."""
    parts = []
    for chunk in pd.read_csv(RAW / FILES[name], usecols=columns, dtype=str,
                             keep_default_na=False, chunksize=250_000):
        parts.append(chunk[keep(chunk)])
    df = pd.concat(parts, ignore_index=True)
    df["value"] = pd.to_numeric(df["OBS_VALUE"].replace("", np.nan), errors="coerce")
    if "CONF_STATUS" in df:
        df.loc[df["CONF_STATUS"] == "C", "value"] = np.nan   # confidential
    df["year"] = df["TIME_PERIOD"].astype(int)
    return df


def load():
    rate = read_eurostat(
        "rate",
        ["geo", "Geopolitical entity (reporting)", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"],
        lambda d: d["TIME_PERIOD"].astype(int) >= 2010,
    )
    mfa = read_eurostat(
        "mfa",
        ["indic_env", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["indic_env"] == "DMC") & d["unit"].isin(["THS_T", "T_HAB"])
        & d["material"].isin(MATERIAL_CODES),
    )
    waste = read_eurostat(
        "waste",
        ["unit", "hazard", "wst_oper", "waste", "geo", "TIME_PERIOD", "OBS_VALUE",
         "OBS_FLAG", "CONF_STATUS"],
        lambda d: (d["unit"] == "T") & (d["hazard"] == "HAZ_NHAZ")
        & d["wst_oper"].isin(OPERATIONS) & d["waste"].isin(WASTE_CODES),
    )
    return rate, mfa, waste


def load_loop():
    in_year = lambda d: (d["material"] == "TOTAL") & (d["unit"] == "THS_T") & (d["TIME_PERIOD"] == str(YEAR))
    flows = read_eurostat(
        "flows",
        ["indic_env", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        in_year,
    )
    waste = read_eurostat(
        "waste_by_material",
        ["wst_oper", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: in_year(d) & (d["wst_oper"] == "TRT"),
    )
    return flows, waste


def per_hundred(shares):
    """Round shares to whole tonnes out of 100 by largest remainder, so they add up to 100."""
    total = sum(shares.values())
    scaled = {k: v / total * 100 for k, v in shares.items()}
    whole = {k: int(np.floor(v)) for k, v in scaled.items()}
    for k in sorted(scaled, key=lambda k: scaled[k] - whole[k], reverse=True)[:100 - sum(whole.values())]:
        whole[k] += 1
    return whole


def loop_table(flows, waste, ceilings, names, geos):
    """Of every 100 tonnes of material processed, where it went. Processed material is
    what's extracted at home, imported, recycled or backfilled."""
    f = flows.set_index(["geo", "indic_env"])["value"]
    w = waste.set_index("geo")["value"]
    soil_rock = ceilings.set_index("geo")["share_soil_rock_pct"] / 100
    rows = []
    for g in geos:
        processed = f.get((g, "DMI_RCV_R_B"), np.nan)
        kt = {name: f.get((g, code), np.nan) for name, code in LOOP_FLOWS.items()}
        kt["back_as_waste"] = w.get(g, np.nan)
        shares = {name: v / processed * 100 for name, v in kt.items()}
        row = {"geo": g, "country": names[g], "processed_kt": processed}
        row.update({f"{name}_kt": v for name, v in kt.items()})
        row.update({f"{name}_pct": v for name, v in shares.items()})
        row["unaccounted_pct"] = 100 - sum(shares.values())
        # Approximate: soil and rock's share of all treated waste, applied to the waste in the flows
        row["back_as_soil_rock_pct"] = shares["back_as_waste"] * soil_rock.get(g, np.nan)
        if not any(np.isnan(list(shares.values()))):
            row.update({f"{name}_per_100": v for name, v in per_hundred(shares).items()})
        rows.append(row)
    return pd.DataFrame(rows)


def footprint_table():
    """The EU's raw material consumption by what it ends up as. Eurostat publishes
    this table for the EU only."""
    fp = read_eurostat(
        "footprint",
        ["indic_env", "material", "cpa08", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["geo"] == "EU27_2020") & (d["unit"] == "THS_T") & (d["material"] == "TOTAL")
        & (d["TIME_PERIOD"] == str(YEAR)) & d["indic_env"].isin(FINAL_USES),
    )
    kt = fp.pivot(index="cpa08", columns="indic_env", values="value")
    total = kt.loc["TOTAL", "RMC"]
    named = [code for codes in FOOTPRINT_GROUPS.values() for code in codes]
    groups = {**FOOTPRINT_GROUPS, "Services": [p for p in kt.index if p not in named + ["TOTAL"]]}
    rows = []
    for group, codes in groups.items():
        g = kt.loc[codes].sum()
        rows.append({
            "group": group,
            "footprint_kt": g["RMC"],
            "share_of_footprint_pct": g["RMC"] / total * 100,
            "investment_pct": g["RMC_P5"] / g["RMC"] * 100,
            "spending_pct": g["RMC_P3"] / g["RMC"] * 100,
            "households_pct": g["RMC_P3_S14"] / g["RMC"] * 100,
        })
    return pd.DataFrame(rows).sort_values("share_of_footprint_pct", ascending=False)


def country_names(rate):
    names = rate.drop_duplicates("geo").set_index("geo")["Geopolitical entity (reporting)"]
    return names.replace({names.get("EU27_2020", ""): "EU"}).to_dict()


def measures(geo, year, rate, consumption, waste):
    """The published rate and the counterfactual ceilings for one country and year.

    Eurostat's rate is U / (U + DMC), where U is circular use (recycled waste,
    adjusted for waste traded for recycling) and DMC is domestic material
    consumption. The rate doesn't rebuild exactly from Eurostat's own component
    tables, so every counterfactual starts from the published rate, r:
    U = r / (1 - r) x DMC.
    """
    r = rate.get((geo, year), np.nan) / 100
    dmc = consumption.get((geo, year), np.nan)                    # thousand tonnes

    def w(code, op):
        return waste.get((geo, year, code, op), np.nan) / 1000   # tonnes to kt

    treated, recycled, backfilled = w("TOTAL", "TRT"), w("TOTAL", "RCV_R"), w("TOTAL", "RCV_B")

    def soil_and_rock(op):
        parts = [w(code, op) for code in SOIL_AND_ROCK]
        if not any(np.isnan(parts)):
            return sum(parts), "reported"
        # Some countries keep a part confidential; the sum still follows from the totals
        rest = w("TOTAL", op) - w("TOT_X_MIN", op) - w("W121", op)
        return (rest, "derived from totals") if not np.isnan(rest) else (np.nan, "not published")

    sr_treated, how_treated = soil_and_rock("TRT")
    sr_recycled, how_recycled = soil_and_rock("RCV_R")

    U = r / (1 - r) * dmc
    extra = treated - recycled                                # treated but not yet recycled
    extra_without_sr = (treated - sr_treated) - (recycled - sr_recycled)

    def ceiling(u):          # consumption unchanged
        return u / (u + dmc) * 100

    def cut_for(target, u):  # % less consumption needed to reach a target at that recycling
        return (1 - u * (1 - target) / target / dmc) * 100

    row = {
        "geo": geo,
        "year": year,
        "rate_pct": r * 100,
        "consumption_kt": dmc,
        "waste_treated_kt": treated,
        "waste_recycled_kt": recycled,
        "waste_backfilled_kt": backfilled,
        "soil_rock_treated_kt": sr_treated,
        "soil_rock_recycled_kt": sr_recycled,
        "soil_rock_source": how_treated if how_treated == how_recycled else f"{how_treated}; {how_recycled}",
        "circular_use_kt": U,
        "ceiling_pct": ceiling(U + extra),
        "ceiling_replacing_new_pct": (U + extra) / (U + dmc) * 100,   # each recycled tonne replaces a new one
        "ceiling_without_soil_rock_pct": ceiling(U + extra_without_sr),
        "rate_with_backfilling_pct": ceiling(U + backfilled),
        "waste_treated_per_consumption_pct": treated / dmc * 100,
        "share_recycled_pct": recycled / treated * 100,
        "share_backfilled_pct": backfilled / treated * 100,
        "share_soil_rock_pct": sr_treated / treated * 100,
        "ceiling_used_pct": r * 100 / ceiling(U + extra) * 100,
    }
    for name, target in TARGETS.items():
        row[f"less_consumption_for_{name}_target_today_pct"] = cut_for(target, U)
        row[f"less_consumption_for_{name}_target_without_soil_rock_pct"] = cut_for(target, U + extra_without_sr)
        row[f"less_consumption_for_{name}_target_everything_pct"] = cut_for(target, U + extra)
    return row


def drivers(a, b):
    """Split the change in the rate between two years into a recycling effect and a
    consumption effect, each holding the other at its starting value."""
    recycling = b["circular_use_kt"] / (b["circular_use_kt"] + a["consumption_kt"]) * 100 - a["rate_pct"]
    consumption = a["circular_use_kt"] / (a["circular_use_kt"] + b["consumption_kt"]) * 100 - a["rate_pct"]
    return {
        "rate_change_pts": b["rate_pct"] - a["rate_pct"],
        "recycling_effect_pts": recycling,
        "consumption_effect_pts": consumption,
        "consumption_change_pct": (b["consumption_kt"] / a["consumption_kt"] - 1) * 100,
        "waste_recycled_change_pct": (b["waste_recycled_kt"] / a["waste_recycled_kt"] - 1) * 100,
        "waste_treated_change_pct": (b["waste_treated_kt"] / a["waste_treated_kt"] - 1) * 100,
        "ceiling_change_pts": b["ceiling_pct"] - a["ceiling_pct"],
        "ceiling_without_soil_rock_change_pts": b["ceiling_without_soil_rock_pct"] - a["ceiling_without_soil_rock_pct"],
    }


def main():
    rate_df, mfa, waste_df = load()
    names = country_names(rate_df)
    geos = ["EU27_2020"] + sorted(g for g in names if g != "EU27_2020")

    rate = {(r.geo, r.year): r.value for r in rate_df.itertuples()}
    rate_flag = {(r.geo, r.year): r.OBS_FLAG for r in rate_df.itertuples()}
    total = mfa[mfa["material"] == "TOTAL"]
    consumption = {(r.geo, r.year): r.value for r in total[total["unit"] == "THS_T"].itertuples()}
    waste = {(r.geo, r.year, r.waste, r.wst_oper): r.value for r in waste_df.itertuples()}
    waste_flag = {(r.geo, r.year): r.OBS_FLAG for r in
                  waste_df[(waste_df["waste"] == "TOTAL") & (waste_df["wst_oper"] == "TRT")].itertuples()}

    OUT.mkdir(parents=True, exist_ok=True)

    # 1. The ceilings in 2022
    ceilings = pd.DataFrame([measures(g, YEAR, rate, consumption, waste) for g in geos])
    ceilings.insert(1, "country", ceilings["geo"].map(names))
    ceilings.drop(columns="year").round(3).to_csv(OUT / f"ceilings_{YEAR}.csv", index=False)

    # 2. The same measures in every reporting year; 2024 values are Eurostat estimates
    trend = pd.DataFrame([measures(g, y, rate, consumption, waste) for g in geos for y in REPORTING_YEARS])
    trend.insert(1, "country", trend["geo"].map(names))
    trend["rate_flag"] = [rate_flag.get((g, y), "") for g, y in zip(trend["geo"], trend["year"])]
    trend["waste_flag"] = [waste_flag.get((g, y), "") for g, y in zip(trend["geo"], trend["year"])]
    trend.round(3).to_csv(OUT / "trend.csv", index=False)

    # 3. What moved the rate between the two ends of the trend
    by_year = trend.set_index(["geo", "year"])
    rows = []
    for g in geos:
        a, b = by_year.loc[(g, TREND_FROM)], by_year.loc[(g, TREND_TO)]
        rows.append({"geo": g, "country": names[g], "from_year": TREND_FROM, "to_year": TREND_TO,
                     "rate_from_pct": a["rate_pct"], "rate_to_pct": b["rate_pct"], **drivers(a, b)})
    pd.DataFrame(rows).round(3).to_csv(OUT / "trend_drivers.csv", index=False)

    # 4. What each country consumes, in kg per person a day
    per_person = mfa[(mfa["unit"] == "T_HAB") & (mfa["year"] == YEAR)].pivot(
        index="geo", columns="material", values="value")
    kg_a_day = 1000 / 365
    materials = pd.DataFrame({
        "sand_and_gravel": per_person["MF38"],
        "limestone_and_other_minerals": per_person["MF3"] - per_person["MF38"],
        "grass_and_fodder": per_person["MF122"],
        "other_biomass": per_person["MF1"] - per_person["MF122"],
        "fossil_fuels": per_person["MF4"],
        "metal_ores_and_other": per_person["MF2"] + per_person["MF5"] + per_person["MF6"],
        "total": per_person["TOTAL"],
    }) * kg_a_day
    materials = materials.reindex(geos)
    materials.insert(0, "country", materials.index.map(names))
    materials.index.name = "geo"
    materials.round(3).to_csv(OUT / f"materials_{YEAR}.csv")

    # 5. Where each country's processed material goes
    loop = loop_table(*load_loop(), ceilings, names, geos)
    loop.round(3).to_csv(OUT / f"loop_{YEAR}.csv", index=False)

    # 6. What the EU's material footprint ends up as
    footprint_table().round(3).to_csv(OUT / f"footprint_{YEAR}.csv", index=False)

    eu = ceilings.set_index("geo").loc["EU27_2020"]
    print(f"EU {YEAR}: rate {eu.rate_pct:.1f}%, ceiling {eu.ceiling_pct:.1f}% "
          f"({eu.ceiling_replacing_new_pct:.1f}% replacing new), "
          f"{eu.ceiling_without_soil_rock_pct:.1f}% without soil and rock")
    print(f"Wrote {len(ceilings)} countries to {OUT}/")


if __name__ == "__main__":
    main()
