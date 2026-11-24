"""Build the data behind Far from Full Circle from Eurostat's raw downloads.

Reads Eurostat datasets from data/raw/ and writes these tables to
data/processed/:

    ceilings_2022.csv        every country's circularity rate and how far
                             recycling alone could take it, in 2022, at each
                             replacement in REPLACEMENTS (columns end _k0,
                             _k05 or _k1)
    trend.csv                the same measures in every waste reporting year
                             from 2010 to 2024
    material_vs_circular_use.csv
                             material use against circular use in every
                             reporting year, with both ceilings as circular use
    trend_drivers.csv        what moved each country's rate from 2012 to 2022:
                             more recycling, or a change in consumption
    trend_steps.csv          the same split for every two-year step, from 2004
                             for the EU and from 2010 for each country
    materials_2022.csv       what each country consumes, in kg per person a day
    weight_mix_2022.csv      each country's consumption split into the four
                             material groups the ring's shards draw, by weight
    loop_2022.csv            where each country's processed material goes:
                             built into stock, burned or eaten, exported, spread
                             on land, or back as waste
    flows_by_material_2022.csv
                             the same, by material, for the EU and the 13
                             member states that publish it
    levers_2022.csv          how much each lever would raise each country's
                             2022 rate
    two_levers_2022.csv      for the EU, the new material the 2030 target takes
                             away at each share of waste recycled from 2022's to
                             70%, how much of it recycling stands in for, and
                             what it removes, one row set per replacement
    cut_by_recycling_2022.csv
                             for the EU, the new material the 2030 target takes
                             away at each share of waste recycled, from 2022's to
                             every tonne, the same at every replacement, and how
                             much of it recycling stands in for at each
    waste_by_material_2022.csv
                             waste treated, recycled and traded for recycling, by
                             material, with circular use and the waste not yet
                             recycled scaled to the rate's own totals
    headline_numbers_2022.csv
                             the figures the page's cards quote, each with its
                             calculation
    unrecycled_waste_2022.csv
                             waste treated but not recycled, other than soil and
                             rock, by kind of waste
    footprint_2022.csv       what the EU's material footprint ends up as, and how
                             much of each is investment or spending (EU only)
    weight_vs_climate_2022.csv
                             each material group's share of EU material use by
                             weight and by the climate impact of producing it,
                             and its impact per tonne against minerals' (EU
                             only, from ETC CE Report 2025/3)
    examples.csv             every figure the page states for its examples, from
                             the datapoints in data/examples, each with its
                             calculation, F numbers and sources
    far_from_full_circle_data_build.js
                             everything the web page draws, before the site's
                             own blocks are merged in

Tables are named by YEAR. To move the piece to a new year, replace the raw files,
set YEAR (and LATEST_STEP_YEAR if the waterfall gains a step) and rerun; the script
warns if the ETC CE shares are for another year. A country without YEAR's rate,
consumption or waste keeps its latest year with all three, every input together,
recorded as data_year; the script warns. compare_years.py then lists what moved.

Run from the repository root:

    python build_data.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/processed")
EXAMPLES = Path("data/examples")
SECONDS_A_YEAR = 365 * 24 * 3600

FILES = {
    "rate": "env_ac_cur_linear_2_0.csv.gz",    # circular material use rate
    "mfa": "env_ac_mfa_linear_2_0.csv.gz",     # material flow accounts
    "waste": "env_wastrt_linear_2_0.csv.gz",   # treatment of waste
    "flows": "env_ac_sd_linear_2_0.csv.gz",    # material flows for the circular economy
    "waste_by_material": "env_wassd_linear_2_0.csv.gz",   # waste treated, by material
    "footprint": "env_ac_rmefd_linear_2_0.csv.gz",        # material footprint by final use
    "generated": "env_wasgen_linear_2_0.csv.gz",          # waste generated, by activity
}

YEAR = 2022                      # latest year where every figure is reported
DATA_AS_OF = "2026-10-28"        # latest Eurostat update among the files in data/raw
LATEST_STEP_YEAR = 2024          # last even year in the waterfall; may be estimated
REPORTING_YEARS = list(range(2010, LATEST_STEP_YEAR + 1, 2))   # waste is reported in even years
TREND_FROM, TREND_TO = 2012, YEAR
STEP_YEARS = list(range(2004, LATEST_STEP_YEAR + 1, 2))        # two-year steps; country rates start in 2010
TARGETS = {"eu": 0.24, "ireland": 0.12}         # EU and Irish goals for 2030
EEA_RECYCLED_SHARE = 0.70                       # share of treated waste recycled in the EEA's 2030 scenario
SHARES_YEAR = 2022          # year of CLIMATE_TOTAL_MT and WEIGHT_VS_CLIMATE, from ETC CE Report 2025/3
CLIMATE_TOTAL_MT = 2890     # climate impact of the raw materials used in the EU-27 in 2022, Mt CO2e
                            # (ETC CE Report 2025/3, Table 3-1); a footprint of final demand

# Replacement: each extra recycled tonne replaces k new tonnes of the same material. The page
# uses REPLACEMENT, an assumed midpoint; the tables also carry both bounds: 0, recycled tonnes
# adding to new ones (the EEA's 2030 scenarios), and 1, the upper limit (ETC CE Report 2025/3).
REPLACEMENT = 0.5
REPLACEMENTS = {"k0": 0.0, "k05": 0.5, "k1": 1.0}
PAGE_K = next(key for key, k in REPLACEMENTS.items() if k == REPLACEMENT)

# Countries whose figures the explorers flag, and why
EXPLORER_WARNINGS = {
    "RO": "imputed_use",       # material use imputed by Eurostat for 2009 to 2019; reported minerals then jump
    "SE": "recycling_jump",    # recycled waste doubled from 2020 to 2022, in mineral wastes unpublished by category
    "EE": "swings",            # rates that swing widely on recycling alone
    "FI": "swings",
    "BG": "swings",
}
# The waterfall explorer's highlighted steps: country, then (first year of the step, the arrow its label names),
# "use" for material use and "recycling" for circular use. "imports" names the recycling arrow
# but labels it as waste brought in. Romania has none.
WATERFALL_HIGHLIGHTS = {
    "AT": [(2012, "recycling")], "BE": [(2020, "recycling"), (2022, "use")],
    "BG": [(2018, "recycling"), (2020, "recycling")], "HR": [(2010, "recycling")],
    "CY": [(2020, "recycling")], "CZ": [(2016, "recycling")],
    "DK": [(2014, "use"), (2020, "recycling")], "EE": [(2010, "recycling"), (2018, "use")],
    "FI": [(2012, "recycling")], "FR": [(2014, "use"), (2018, "recycling")],
    "DE": [(2022, "use")], "EL": [(2010, "use"), (2020, "recycling")], "HU": [(2012, "use")],
    "IE": [(2010, "use")], "IT": [(2012, "use"), (2020, "use")],
    "LV": [(2012, "imports"), (2022, "use")], "LT": [(2012, "use")], "LU": [(2012, "recycling")],
    "MT": [(2010, "use"), (2018, "recycling")], "NL": [(2014, "use"), (2022, "use")],
    "PL": [(2018, "recycling")], "PT": [(2020, "recycling")], "SK": [(2018, "recycling")],
    "SI": [(2010, "use"), (2020, "use")], "ES": [(2010, "use")], "SE": [(2020, "recycling")],
}
# The four material groups of the ring's shards, in the shard solver's order
MIX_GROUPS = {"minerals": "MF3", "biomass": "MF1", "fossil": "MF4", "metals": "MF2"}
FLOW_ORDER = ["Non-metallic minerals", "Biomass", "Fossil fuels", "Metal ores"]   # MIX_GROUPS' order, by name

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
FLOW_MATERIALS = {"Non-metallic minerals": "MF3", "Biomass": "MF1", "Fossil fuels": "MF4", "Metal ores": "MF2"}

# Levers, as the change in the 2022 rate each brings with everything else unchanged
LEVERS = ["recycling_all_but_soil_rock", "recycling_every_tonne", "using_15pct_less", "using_no_fossil_fuels"]

# Waste treated but not recycled, other than soil and rock, by kind (env_wastrt categories)
UNRECYCLED_GROUPS = {
    "Mixed household and similar waste": ["W101"],
    "Sorting residues and other mixed waste": ["W102", "W103"],
    "Construction and demolition rubble": ["W121"],
    "Ash and residues from burning and treating waste": ["W124", "W128_13"],
    "Chemical and medical waste, and sludges": ["W011", "W012", "W013", "W02A", "W032", "W033", "W05", "W11"],
    "Metal, glass, paper, plastic, wood and textiles": ["W061", "W062", "W063", "W071", "W072", "W073",
                                                        "W074", "W075", "W076", "W077"],
    "Food, plant waste and manure": ["W091", "W092", "W093"],
    "Discarded vehicles and equipment": ["W081", "W0841", "W08A"],
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

# Shares of EU material use in 2022, in %, by weight and by the climate impact of producing
# the materials, from extraction to the factory gate. Read from Figure 3-4 of ETC CE Report
# 2025/3, Measuring environmental benefits of circular economy (Vercalsteren and others, 2025).
WEIGHT_VS_CLIMATE = {
    "Non-metallic minerals": (52.3, 11.4),
    "Biomass": (22.7, 45.7),
    "Fossil fuels": (19.5, 26.6),
    "Metal ores": (5.5, 16.3),
}


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


GEO_YEAR = {}   # countries without YEAR's rate, consumption or waste: their latest year with all three


def data_year(geo):
    """The year a country's figures come from: YEAR, or its fallback in GEO_YEAR."""
    return GEO_YEAR.get(geo, YEAR)


def in_data_year(d):
    """Rows from each country's own data year."""
    return d["TIME_PERIOD"] == d["geo"].map(lambda g: str(data_year(g)))


def fallback_years(geos, rate, consumption, waste):
    """For each country missing YEAR's rate, consumption or waste treated, its latest reporting year
    with all three."""
    def complete(g, y):
        return all(pd.notna(v) for v in (rate.get((g, y)), consumption.get((g, y)), waste.get((g, y, "TOTAL", "TRT"))))
    years = [y for y in REPORTING_YEARS if y < YEAR]
    return {g: max((y for y in years if complete(g, y)), default=YEAR)
            for g in geos if g != "EU27_2020" and not complete(g, YEAR)}


def load():
    rate = read_eurostat(
        "rate",
        ["geo", "Geopolitical entity (reporting)", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG"],
        lambda d: d["TIME_PERIOD"].astype(int) >= STEP_YEARS[0],
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
    materials = ["TOTAL"] + list(FLOW_MATERIALS.values())
    in_year = lambda d: d["material"].isin(materials) & (d["unit"] == "THS_T") & in_data_year(d)
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
    f = flows[flows["material"] == "TOTAL"].set_index(["geo", "indic_env"])["value"]
    w = waste[waste["material"] == "TOTAL"].set_index("geo")["value"]
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


def flows_by_material_table(flows, waste, ceilings, names, geos):
    """Where each material goes, for the EU and the member states that split every flow by
    material. Soil and rock sit in non-metallic minerals' waste, estimated as in loop_table."""
    f = flows.set_index(["geo", "material", "indic_env"])["value"]
    w = waste.set_index(["geo", "material"])["value"]
    soil_rock = ceilings.set_index("geo")["share_soil_rock_pct"] / 100
    rows = []
    for g in geos:
        by_material = {}
        for material, code in FLOW_MATERIALS.items():
            row = {"geo": g, "country": names[g], "material": material,
                   "processed_kt": f.get((g, code, "DMI_RCV_R_B"), np.nan)}
            row.update({f"{name}_kt": f.get((g, code, c), np.nan) for name, c in LOOP_FLOWS.items()})
            row["back_as_waste_kt"] = w.get((g, code), np.nan)
            by_material[material] = row
        if any(np.isnan(v) for row in by_material.values() for k, v in row.items() if k.endswith("_kt")):
            continue
        for material, row in by_material.items():
            fates = sum(row[f"{name}_kt"] for name in list(LOOP_FLOWS) + ["back_as_waste"])
            row["unaccounted_kt"] = row["processed_kt"] - fates
            row["back_as_soil_rock_kt"] = (w.get((g, "TOTAL"), np.nan) * soil_rock.get(g, np.nan)
                                           if material == "Non-metallic minerals" else 0.0)
            rows.append(row)
    return pd.DataFrame(rows)


def rate_with(u, dmc):
    return u / (u + dmc) * 100


def step(geo, a, b, rate, consumption):
    """Split the change in the rate from year a to year b into a recycling effect and a
    consumption effect. The recycling effect is the change from recycling alone, averaged
    over holding consumption at its starting and at its ending value; the consumption
    effect is the rest, so the two add up to the change."""
    ra, rb = rate.get((geo, a), np.nan) / 100, rate.get((geo, b), np.nan) / 100
    da, db = consumption.get((geo, a), np.nan), consumption.get((geo, b), np.nan)
    if np.isnan([ra, rb, da, db]).any():
        return None
    ua, ub = ra / (1 - ra) * da, rb / (1 - rb) * db
    change = (rb - ra) * 100
    recycling = ((rate_with(ub, da) - ra * 100) + (rb * 100 - rate_with(ua, db))) / 2
    return {"geo": geo, "from_year": a, "to_year": b, "rate_from_pct": ra * 100, "rate_to_pct": rb * 100,
            "rate_change_pts": change, "recycling_effect_pts": recycling,
            "consumption_effect_pts": change - recycling,
            "consumption_change_pct": (db / da - 1) * 100, "circular_use_change_pct": (ub / ua - 1) * 100}


def load_generated():
    """Waste generated by households and by everyone, in kt."""
    gen = read_eurostat(
        "generated",
        ["unit", "hazard", "nace_r2", "waste", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["unit"] == "T") & (d["hazard"] == "HAZ_NHAZ") & (d["waste"] == "TOTAL")
        & d["nace_r2"].isin(["EP_HH", "TOTAL_HH"]) & in_data_year(d),
    )
    return gen.pivot(index="geo", columns="nace_r2", values="value") / 1000


def levers_table(ceilings, mfa, households, names):
    """The change in the 2022 rate each lever would bring, with everything else unchanged.
    Recycling levers keep consumption as it is; using less keeps recycling as it is."""
    fossil = mfa[(mfa["material"] == "MF4") & (mfa["unit"] == "THS_T") & in_data_year(mfa)].set_index("geo")["value"]
    rows = []
    for x in ceilings.itertuples():
        u, dmc, r = x.circular_use_kt, x.consumption_kt, x.rate_pct
        hh = households.get(x.geo, np.nan)
        rows.append({
            "geo": x.geo, "country": names[x.geo], "rate_pct": r,
            "recycling_all_but_soil_rock_pts": x.ceiling_without_soil_rock_pct - r,
            "recycling_every_tonne_pts": x.ceiling_pct - r,
            "using_15pct_less_pts": rate_with(u, 0.85 * dmc) - r,
            "using_no_fossil_fuels_pts": rate_with(u, dmc - fossil.get(x.geo, np.nan)) - r,
            "household_waste_kt": hh,
            # an upper bound: it counts household waste as if none of it were recycled today
            "recycling_household_waste_at_most_pts": rate_with(u + hh, dmc) - r,
        })
    return pd.DataFrame(rows)


def import_shares(geo="EU27_2020"):
    """Each material group's share of all tonnes imported in YEAR, in %."""
    imp = read_eurostat(
        "mfa",
        ["indic_env", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["indic_env"] == "IMP") & (d["unit"] == "THS_T") & (d["geo"] == geo)
        & (d["TIME_PERIOD"] == str(YEAR)) & d["material"].isin(["TOTAL"] + list(FLOW_MATERIALS.values())),
    ).set_index("material")["value"]
    return {group: imp[code] / imp["TOTAL"] * 100 for group, code in FLOW_MATERIALS.items()}


def imports_block(geo="EU27_2020"):
    """The page's imports block: extra-EU imports in YEAR, in total and by material group, with each
    group's imports over its direct material input and its share of all imports."""
    m = read_eurostat(
        "mfa",
        ["indic_env", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: d["indic_env"].isin(["IMP", "DMI"]) & (d["unit"] == "THS_T") & (d["geo"] == geo)
        & (d["TIME_PERIOD"] == str(YEAR)) & d["material"].isin(["TOTAL"] + list(FLOW_MATERIALS.values())),
    ).set_index(["indic_env", "material"])["value"]
    total = m[("IMP", "TOTAL")]
    order = ["Non-metallic minerals", "Metal ores", "Fossil fuels", "Biomass"]
    return {
        "year": YEAR,
        "source": f"Eurostat env_ac_mfa, {geo}, extra-EU imports",
        "imports_kt": round(float(total), 1),
        "materials": [{"material_group": g,
                       "imports_kt": round(float(m[("IMP", FLOW_MATERIALS[g])]), 1),
                       "dmi_kt": round(float(m[("DMI", FLOW_MATERIALS[g])]), 1),
                       "imports_over_dmi_pct": round(float(m[("IMP", FLOW_MATERIALS[g])] / m[("DMI", FLOW_MATERIALS[g])] * 100), 2),
                       "share_of_imports_pct": round(float(m[("IMP", FLOW_MATERIALS[g])] / total * 100), 2)} for g in order],
    }


def two_levers_table(ceilings, imports, by_material, dmc_by_group):
    """For the EU: at each share of treated waste recycled, from today's to the EEA's 70%, the new
    material the EU target takes away, with waste held at its tonnes, split into what recycling stands
    in for (each extra recycled tonne replacing k new tonnes of the same material, one row set for each
    k in REPLACEMENTS) and what the EU goes without; and what that removes. Extra recycling is split across materials by
    each one's waste not yet recycled. What the EU goes without is taken in whole material groups,
    heaviest first or dirtiest per tonne first, on each group's share of Eurostat's consumption (the ring's
    weight shares) and Figure 3-4's climate shares; recycling's removals are each group's own share of its
    Eurostat consumption. Imports fall in proportion to each group's use; tonnes are of all extra-EU imports."""
    eu = ceilings.set_index("geo").loc["EU27_2020"]
    target = TARGETS["eu"]
    weight = {g: 100 * dmc_by_group[g] / sum(dmc_by_group.values()) for g in WEIGHT_VS_CLIMATE}
    climate = {g: c for g, (_, c) in WEIGHT_VS_CLIMATE.items()}
    routes = {
        "heaviest_first": sorted(weight, key=weight.get, reverse=True),
        "dirtiest_first": sorted(weight, key=lambda g: climate[g] / weight[g], reverse=True),
    }
    m = by_material[by_material["geo"] == "EU27_2020"].set_index("material")
    not_recycled = m["share_of_not_recycled_pct"] / 100

    today = eu.share_recycled_pct
    imports_kt = imports_block()["imports_kt"]
    rows = []
    for (key, k), s in [(kk, s) for kk in REPLACEMENTS.items()
                        for s in [today] + list(range(int(today) + 1, round(EEA_RECYCLED_SHARE * 100) + 1))]:
        e = (s - today) / 100 * eu.waste_treated_kt
        u = eu.circular_use_kt + e
        cut = (1 - u * (1 - target) / target / eu.consumption_kt) * 100
        replaced = k * e / eu.consumption_kt * 100
        by_recycling = {g: min(1.0, k * e * not_recycled[g] / dmc_by_group[g]) for g in weight}
        row = {"replacement": key, "recycled_share_pct": s, "circular_use_kt": u,
               "recycling_multiple": (eu.waste_recycled_kt + e) / eu.waste_recycled_kt,
               "rate_without_cut_pct": u / (u + eu.consumption_kt - k * e) * 100,
               "less_consumption_for_eu_target_pct": cut,
               "less_consumption_for_eu_target_mt": cut / 100 * eu.consumption_kt / 1000,
               "replaced_by_recycling_pct": replaced,
               "gone_without_pct": max(0.0, cut - replaced),
               "climate_cut_by_recycling_pct": sum(by_recycling[g] * climate[g] for g in weight),
               "imports_cut_by_recycling_pct": sum(by_recycling[g] * imports[g] for g in weight)}
        for name, order in routes.items():
            left, share = row["gone_without_pct"], dict(by_recycling)
            for g in order:
                take = min(left, weight[g] * (1 - by_recycling[g]))
                share[g] += take / weight[g]
                left -= take
            row[f"climate_cut_{name}_pct"] = sum(share[g] * climate[g] for g in order)
            row[f"climate_cut_{name}_mt"] = row[f"climate_cut_{name}_pct"] / 100 * CLIMATE_TOTAL_MT
            row[f"imports_cut_{name}_pct"] = sum(share[g] * imports[g] for g in order)
            row[f"imports_cut_{name}_mt"] = row[f"imports_cut_{name}_pct"] / 100 * imports_kt / 1000
        rows.append(row)
    return pd.DataFrame(rows)


def cut_curve_table(ceilings):
    """For the EU: at each share of treated waste recycled, from today's to every tonne, the new
    material the EU target takes away with waste held at its tonnes, which is the same at every
    replacement, and the part each extra recycled tonne stands in for at each k in REPLACEMENTS.
    Where that part passes the cut, recycling alone takes the rate past the target."""
    eu = ceilings.set_index("geo").loc["EU27_2020"]
    target = TARGETS["eu"]
    today = eu.share_recycled_pct
    rows = []
    for s in [today] + list(range(int(today) + 1, 101)):
        e = (s - today) / 100 * eu.waste_treated_kt
        u = eu.circular_use_kt + e
        row = {"recycled_share_pct": s,
               "less_consumption_for_eu_target_pct": (1 - u * (1 - target) / target / eu.consumption_kt) * 100}
        for key, k in REPLACEMENTS.items():
            row[f"replaced_by_recycling_{key}_pct"] = k * e / eu.consumption_kt * 100
            row[f"rate_recycling_alone_{key}_pct"] = u / (u + eu.consumption_kt - k * e) * 100
        rows.append(row)
    return pd.DataFrame(rows)


def waste_by_material_table(ceilings, names, geos):
    """Waste treated, recycled and traded for recycling in YEAR, by material (env_wassd, env_ac_sd),
    with circular use (recycled, plus exported and less imported for recycling) and the waste not yet
    recycled each scaled so they add up to the rate's own totals: circular use back-calculated from the
    published rate, and env_wastrt's waste treated less recycled. Recycling here is recycling alone
    (R2 to R11), as in the rate. Where trade by material isn't published, circular use is split by recycled
    tonnes alone. The check column flags splits to treat with care."""
    codes = list(FLOW_MATERIALS.values())
    wst = read_eurostat(
        "waste_by_material",
        ["wst_oper", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["unit"] == "THS_T") & in_data_year(d)
        & d["wst_oper"].isin(["TRT", "RCV_R"]) & d["material"].isin(codes),
    ).set_index(["geo", "material", "wst_oper"])["value"]
    trade = read_eurostat(
        "flows",
        ["indic_env", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["unit"] == "THS_T") & in_data_year(d)
        & d["indic_env"].isin(["EXP_RCV_R", "IMP_RCV_R"]) & d["material"].isin(codes),
    ).set_index(["geo", "material", "indic_env"])["value"]
    c = ceilings.set_index("geo")
    rows = []
    for g in geos:
        x = c.loc[g]
        parts = {}
        for name, code in FLOW_MATERIALS.items():
            trt, rec = wst.get((g, code, "TRT"), np.nan), wst.get((g, code, "RCV_R"), np.nan)
            exp, imp = trade.get((g, code, "EXP_RCV_R"), np.nan), trade.get((g, code, "IMP_RCV_R"), np.nan)
            parts[name] = {"treated_kt": trt, "recycled_kt": rec, "exported_for_recycling_kt": exp,
                           "imported_for_recycling_kt": imp,
                           "net_recycled_kt": rec + np.nan_to_num(exp) - np.nan_to_num(imp),
                           "not_recycled_raw_kt": trt - rec}
        net = sum(p["net_recycled_kt"] for p in parts.values())
        nr = sum(p["not_recycled_raw_kt"] for p in parts.values())
        u_scale = x.circular_use_kt / net
        nr_scale = (x.waste_treated_kt - x.waste_recycled_kt) / nr
        checks = []
        if any(np.isnan(p["exported_for_recycling_kt"]) for p in parts.values()):
            checks.append("trade by material not published")
        if any(p["net_recycled_kt"] < 0 for p in parts.values()):
            checks.append("a material's circular use is negative")
        if not 2 / 3 <= u_scale <= 1.5:
            checks.append("circular use scaled by over half")
        if not 2 / 3 <= nr_scale <= 1.5:
            checks.append("waste not yet recycled scaled by over half")
        for name, p in parts.items():
            rows.append({"geo": g, "country": names[g], "material": name, **p,
                         "circular_use_kt": p["net_recycled_kt"] * u_scale,
                         "not_recycled_kt": p["not_recycled_raw_kt"] * nr_scale,
                         "share_of_circular_use_pct": p["net_recycled_kt"] / net * 100,
                         "share_of_not_recycled_pct": p["not_recycled_raw_kt"] / nr * 100,
                         "recycled_share_pct": p["recycled_kt"] / p["treated_kt"] * 100,
                         "scale_circular_use": u_scale, "scale_not_recycled": nr_scale,
                         "check": "; ".join(checks)})
    return pd.DataFrame(rows)


def unrecycled_table(names, geos):
    """Waste treated but not recycled, other than soil and rock, by kind of waste, in kt."""
    codes = [c for cs in UNRECYCLED_GROUPS.values() for c in cs]
    wst = read_eurostat(
        "waste",
        ["unit", "hazard", "wst_oper", "waste", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["unit"] == "T") & (d["hazard"] == "HAZ_NHAZ") & d["wst_oper"].isin(["TRT", "RCV_R"])
        & d["waste"].isin(codes) & in_data_year(d),
    )
    v = wst.set_index(["geo", "waste", "wst_oper"])["value"] / 1000
    rows = []
    for g in geos:
        left = {group: sum(v.get((g, c, "TRT"), np.nan) - v.get((g, c, "RCV_R"), np.nan) for c in cs)
                for group, cs in UNRECYCLED_GROUPS.items()}
        total = sum(left.values())
        rows += [{"geo": g, "country": names[g], "kind": group, "unrecycled_kt": kt, "share_pct": kt / total * 100}
                 for group, kt in left.items()]
    return pd.DataFrame(rows)


def footprint_table():
    """The EU's raw material consumption by what it ends up as. Eurostat publishes
    this table for the EU only."""
    fp = read_eurostat(
        "footprint",
        ["indic_env", "material", "cpa08", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["geo"] == "EU27_2020") & (d["unit"] == "THS_T") & (d["material"] == "TOTAL")
        & (d["TIME_PERIOD"].astype(int) <= YEAR) & d["indic_env"].isin(FINAL_USES),
    )
    # Eurostat publishes the split by product later than the rest: use the latest year that has it
    year = fp.loc[fp["cpa08"] != "TOTAL", "TIME_PERIOD"].astype(int).max()
    if year != YEAR:
        print(f"Warning: the footprint table is for {year}, the latest with products, not {YEAR}")
    fp = fp[fp["TIME_PERIOD"].astype(int) == year]
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


def headline_table(ceilings, steps, two_levers, by_material, loop, mix, trend):
    """The figures the page's cards quote, EU and YEAR unless named, each with its calculation."""
    c = ceilings.set_index("geo")
    eu, ie = c.loc["EU27_2020"], c.loc["IE"]
    st = steps.set_index(["geo", "from_year"])
    wm = by_material[by_material["geo"] == "EU27_2020"].set_index("material")
    tl = two_levers.set_index(["replacement", "recycled_share_pct"])
    target = TARGETS["eu"]
    A, B = STEP_YEARS[-2], STEP_YEARS[-1]     # the latest two-year step
    N1 = B + 1                                # the year after it, imputed by Eurostat
    S0 = STEP_YEARS[0]
    U, D, T = eu.circular_use_kt, eu.consumption_kt, eu.waste_treated_kt
    N = T - eu.waste_recycled_kt
    codes = ["TOTAL", "MF1", "MF2", "MF3", "MF4", "MF41", "MF411", "MF413", "MF422", "MF5", "MF6"]   # MF411 lignite, MF413 oil shale
    mfa = read_eurostat(
        "mfa",
        ["indic_env", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: d["geo"].isin(["EU27_2020", "NL", "DE", "LV", "EE", "RO", "FI"]) & d["material"].isin(codes)
        & d["indic_env"].isin(["DMC", "IMP", "EXP", "DE"]) & d["unit"].isin(["THS_T", "T_HAB"]),
    )
    mv = mfa.set_index(["geo", "indic_env", "material", "unit", "year"])["value"]

    def dmc(geo, mat, year, unit="THS_T"):
        v = mv.get((geo, "DMC", mat, unit, year), np.nan)
        if np.isnan(v):   # natural gas has no DMC row: domestic extraction plus imports less exports
            v = sum(mv.get((geo, i, mat, unit, year), np.nan) * k for i, k in [("DE", 1), ("IMP", 1), ("EXP", -1)])
        return v

    def fall(geo, mat, a, b):
        return dmc(geo, mat, a) - dmc(geo, mat, b)

    wassd = read_eurostat(
        "waste_by_material",
        ["wst_oper", "material", "unit", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["geo"] == "EU27_2020") & (d["unit"] == "THS_T") & (d["wst_oper"] == "TRT"),
    ).set_index(["material", "year"])["value"]

    wst = read_eurostat(
        "waste",
        ["unit", "hazard", "wst_oper", "waste", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: (d["geo"] == "EU27_2020") & (d["unit"] == "T") & (d["hazard"] == "HAZ_NHAZ")
        & d["wst_oper"].isin(["TRT", "RCV_R"]) & d["waste"].isin(["TOTAL", "TOT_X_MIN", "W124", "W128_13", "W121"] + SOIL_AND_ROCK)
        & (d["TIME_PERIOD"] == str(YEAR)),
    ).set_index(["waste", "wst_oper"])["value"] / 1000

    # Waste recycled by country, for the waterfall explorer's cards, kt
    rcv = read_eurostat(
        "waste",
        ["unit", "hazard", "wst_oper", "waste", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: d["geo"].isin(["SE", "DK", "FR", "SK", "FI"]) & (d["unit"] == "T") & (d["hazard"] == "HAZ_NHAZ")
        & (d["wst_oper"] == "RCV_R") & d["waste"].isin(["TOTAL", "TOT_X_MIN"] + SOIL_AND_ROCK),
    ).set_index(["geo", "waste", "year"])["value"] / 1000

    def recycled(geo, year, code="TOTAL"):
        return rcv.get((geo, code, year), np.nan)

    def soil_rock_recycled(geo, year):     # missing if any part is confidential
        return sum(recycled(geo, year, code) for code in SOIL_AND_ROCK)

    def soil_rock_share_of_change(geo, a, b):
        return (soil_rock_recycled(geo, b) - soil_rock_recycled(geo, a)) / (recycled(geo, b) - recycled(geo, a)) * 100

    def major_mineral_share_of_change(geo, a, b):   # major mineral wastes: TOTAL less TOT_X_MIN
        return (1 - (recycled(geo, b, "TOT_X_MIN") - recycled(geo, a, "TOT_X_MIN"))
                / (recycled(geo, b) - recycled(geo, a))) * 100

    # Finland's 2024 rate if its circular use had moved as env_wastrt's recycled waste did
    fi_u22 = st.loc[("FI", 2022), "rate_from_pct"] / (100 - st.loc[("FI", 2022), "rate_from_pct"]) * dmc("FI", "TOTAL", 2022)
    fi_u24 = fi_u22 * recycled("FI", 2024) / recycled("FI", 2022)

    # Where the waste not recycled went, EU and Ireland, YEAR: buried (landfilled or backfilled) or not
    fate = read_eurostat(
        "waste",
        ["unit", "hazard", "wst_oper", "waste", "geo", "TIME_PERIOD", "OBS_VALUE", "CONF_STATUS"],
        lambda d: d["geo"].isin(["EU27_2020", "IE"]) & (d["unit"] == "T") & (d["hazard"] == "HAZ_NHAZ")
        & d["wst_oper"].isin(["TRT", "RCV_R", "RCV_B", "DSP_L", "DSP_L_OTH"]) & (d["waste"] == "TOTAL")
        & (d["TIME_PERIOD"] == str(YEAR)),
    ).set_index(["geo", "wst_oper"])["value"]

    def not_recycled_share(geo, ops):
        return sum(fate[(geo, o)] for o in ops) / (fate[(geo, "TRT")] - fate[(geo, "RCV_R")]) * 100

    # Member states' rates, ranked from the lowest (ties share the lower rank)
    ms_rates = trend[trend["geo"] != "EU27_2020"].set_index(["year", "geo"])["rate_pct"]

    def rank_from_lowest(geo, year):
        return int(ms_rates.loc[year].rank(method="min")[geo])
    rate_at = trend[trend["geo"] == "EU27_2020"].set_index("year")["rate_pct"]
    S1 = REPORTING_YEARS[0]

    def left(code):      # treated but not yet recycled, kt
        return wst[(code, "TRT")] - wst[(code, "RCV_R")]
    major_mineral = left("TOTAL") - left("TOT_X_MIN")
    ash = left("W124") + left("W128_13")
    Rc, Bf = eu.waste_recycled_kt, eu.waste_backfilled_kt   # recycled, backfilled

    def close_climate(k):   # climate impact removed when recycling alone closes the ring at replacement k
        need = (target * (U + D) - U) / (1 - target * (1 - k))
        if need > N:        # recycling every tonne falls short
            return np.nan
        return sum(min(1.0, k * need * wm.loc[g, "share_of_not_recycled_pct"] / 100 / dmc("EU27_2020", FLOW_MATERIALS[g], YEAR))
                   * WEIGHT_VS_CLIMATE[g][1] for g in FLOW_MATERIALS)
    per_pct = 0.01 * T                        # 1% of treated waste, kt
    cut_slope = per_pct * (1 - target) / target / D * 100
    eu_steps = steps[steps["geo"] == "EU27_2020"]
    fell = eu_steps[eu_steps["consumption_change_pct"] < 0]
    no_fossil = D - dmc("EU27_2020", "MF4", YEAR)
    no_fossil_metals = no_fossil - dmc("EU27_2020", "MF2", YEAR)
    cut_kt = eu.less_consumption_for_eu_target_today_pct / 100 * D
    countries = loop[loop["geo"] != "EU27_2020"]
    nl_fall = fall("NL", "TOTAL", A, B)
    rows = [
        ("ring_closed", eu.rate_pct / target, "%", "rate_pct / 24"),
        ("less_new_material_using_less_alone", eu.less_consumption_for_eu_target_today_pct, "%",
         "ceilings: less_consumption_for_eu_target_today_pct"),
        ("less_new_material_at_70pct_recycled", eu.less_consumption_for_eu_target_70pct_recycled_pct, "%",
         "ceilings: less_consumption_for_eu_target_70pct_recycled_pct; the same under both bounds"),
        ("waste_back_per_material_consumed", T / D * 100, "%", "waste_treated_kt / consumption_kt"),
        ("treated_soil_rubble_rock_share", sum(wst[(c, "TRT")] for c in ["W121"] + SOIL_AND_ROCK) / wst[("TOTAL", "TRT")] * 100, "%",
         "env_wastrt TRT: W121 (construction and demolition) + W126, W127, W12B (soils, dredging spoils, other mineral) / TOTAL"),
        ("rate_rebuilt", Rc / (Rc + D) * 100, "%", "waste_recycled_kt / (waste_recycled_kt + DMC), env_wastrt; no trade"),
        ("rate_rebuilt_with_backfilling", (Rc + Bf) / (Rc + Bf + D) * 100, "%",
         "(recycled + backfilled) / (recycled + backfilled + DMC), env_wastrt; no trade"),
        ("not_recycled_major_mineral_share", major_mineral / left("TOTAL") * 100, "%",
         "env_wastrt: (TOTAL - TOT_X_MIN) treated less recycled / TOTAL treated less recycled"),
        ("not_recycled_major_mineral_and_ash_share", (major_mineral + ash) / left("TOTAL") * 100, "%",
         "env_wastrt: as above, plus W124 (combustion) and W128_13 (mineral waste from waste treatment)"),
        ("ireland_ring_closed", ie.rate_pct / target, "%", "Ireland's rate_pct / 24"),
        ("ireland_less_using_less_alone", ie.less_consumption_for_eu_target_today_pct, "%",
         "Ireland's less_consumption_for_eu_target_today_pct"),
        ("ireland_own_target_2030", TARGETS["ireland"] * 100, "%", "Ireland's Circular Economy Strategy 2026 to 2028 (F106)"),
        *[(f"ireland_ceiling_{key}", ie[f"ceiling_{key}_pct"], "%", f"ceilings: Ireland's ceiling_{key}_pct, every tonne recycled")
          for key in REPLACEMENTS],
        ("ireland_less_for_own_target_70pct_recycled", ie.less_consumption_for_ireland_target_70pct_recycled_pct, "%",
         "ceilings: Ireland's less_consumption_for_ireland_target_70pct_recycled_pct; the same under both bounds"),
        *[row for key, k in REPLACEMENTS.items() for row in [
            (f"recycled_share_to_close_{key}", eu[f"recycled_share_to_close_eu_alone_{key}_pct"], "%",
             f"(waste_recycled_kt + extra) / waste_treated_kt, extra = (24% x (U + DMC) - U) / (1 - 24% x (1 - {k})); over 100: can't"),
            (f"recycling_multiple_to_close_{key}", eu[f"recycling_multiple_to_close_eu_alone_{key}"], "times",
             "(waste_recycled_kt + extra) / waste_recycled_kt"),
            (f"less_new_material_to_close_{key}",
             eu[f"less_new_material_to_close_eu_alone_{key}_pct"] if eu[f"recycled_share_to_close_eu_alone_{key}_pct"] <= 100 else np.nan,
             "%", f"{k} x extra / DMC: the new material recycling replaces when it alone closes the ring; blank if it can't"),
            (f"rate_every_tonne_{key}", eu[f"ceiling_{key}_pct"], "%",
             f"(U + not yet recycled) / (U + DMC + (1 - {k}) x not yet recycled)"),
            (f"rate_70pct_recycled_{key}", eu[f"rate_70pct_recycled_{key}_pct"], "%",
             f"(U + extra at 70%) / (U + DMC + (1 - {k}) x extra)"),
            (f"replaced_at_70pct_{key}", eu[f"replaced_by_recycling_for_eu_target_70pct_recycled_{key}_pct"], "%",
             f"{k} x extra recycled at 70% / DMC"),
            (f"gone_without_at_70pct_{key}", eu[f"gone_without_for_eu_target_70pct_recycled_{key}_pct"], "%",
             f"less_new_material_at_70pct_recycled - replaced_at_70pct_{key}"),
            (f"gone_without_per_1pct_recycled_{key}", cut_slope + k * per_pct / D * 100, "% per 1% of waste recycled",
             f"each 1% of treated waste recycled: cut falls by 1% of T x 0.76 / 0.24 / DMC, and recycling stands in for {k} x 1% of T / DMC more"),
            (f"climate_cut_by_recycling_at_70pct_{key}", tl.loc[(key, tl.loc[key].index.max()), "climate_cut_by_recycling_pct"], "%",
             "two_levers at 70%: climate impact removed by recycling alone, at each group's average impact per tonne"),
            (f"climate_cut_by_recycling_at_close_{key}", close_climate(k), "%",
             "recycling alone closing the ring: each group's share of its use replaced x its climate share"),
            (f"climate_cut_by_recycling_at_close_mt_{key}", close_climate(k) / 100 * CLIMATE_TOTAL_MT, "Mt CO2e",
             f"climate_cut_by_recycling_at_close_{key} x climate_total"),
            (f"countries_past_target_at_70pct_{key}", int((c.drop("EU27_2020")[f"rate_70pct_recycled_{key}_pct"] >= 24).sum()),
             "countries", "rate at 70% recycled, recycling alone, at or above 24%"),
            (f"countries_short_at_70pct_{key}", int((c.drop("EU27_2020")[f"rate_70pct_recycled_{key}_pct"] < 24).sum()),
             "countries", "rate at 70% recycled, recycling alone, below 24%: those that still have to go without"),
        ]],
        ("eu_countries", len(c.drop("EU27_2020")), "countries", "member states in the tables"),
        ("target", target * 100, "%", "the EU's aim for 2030 (TARGETS)"),
        ("eea_recycled_share_2030", EEA_RECYCLED_SHARE * 100, "%", "share of treated waste recycled in the EEA's 2030 scenario"),
        ("replacement", REPLACEMENT, "new t per recycled t", "the page's assumed midpoint; the tables also carry 0 and 1"),
        ("cut_per_1pct_recycled", cut_slope, "% per 1% of waste recycled", "1% of T x 0.76 / 0.24 / DMC; the same at every replacement"),
        ("not_recycled_minerals_share", wm.loc["Non-metallic minerals", "share_of_not_recycled_pct"], "%",
         "env_wassd: minerals' treated less recycled over all four groups'"),
        ("not_recycled_biomass_share", wm.loc["Biomass", "share_of_not_recycled_pct"], "%", "as above"),
        ("not_recycled_fossil_share", wm.loc["Fossil fuels", "share_of_not_recycled_pct"], "%", "as above"),
        ("not_recycled_metals_share", wm.loc["Metal ores", "share_of_not_recycled_pct"], "%", "as above"),
        ("climate_total", CLIMATE_TOTAL_MT, "Mt CO2e", "ETC CE Report 2025/3, Table 3-1, 2022"),
        (f"waterfall_change_{S0}_{B}", eu_steps["rate_change_pts"].sum(), "change in rate", "sum of EU steps"),
        (f"pace_{S0}_{YEAR}_per_year", (eu.rate_pct - st.loc[("EU27_2020", S0), "rate_from_pct"]) / (YEAR - S0),
         "change in rate a year", f"(rate in {YEAR} - rate in {S0}) / {YEAR - S0} years"),
        (f"waterfall_recycling_{S0}_{B}", eu_steps["recycling_effect_pts"].sum(), "change in rate", "sum of recycling effects"),
        (f"waterfall_using_less_{S0}_{B}", eu_steps["consumption_effect_pts"].sum(), "change in rate", "sum of consumption effects"),
        (f"waterfall_recycling_share_{S0}_{B}", eu_steps["recycling_effect_pts"].sum() / eu_steps["rate_change_pts"].sum() * 100,
         "%", "waterfall_recycling / waterfall_change"),
        (f"waterfall_using_less_share_{S0}_{B}", eu_steps["consumption_effect_pts"].sum() / eu_steps["rate_change_pts"].sum() * 100,
         "%", "waterfall_using_less / waterfall_change"),
        ("step_2008_2010_change", st.loc[("EU27_2020", 2008), "rate_change_pts"], "change in rate", "trend_steps"),
        ("step_2008_2010_use_share", st.loc[("EU27_2020", 2008), "consumption_effect_pts"]
         / st.loc[("EU27_2020", 2008), "rate_change_pts"] * 100, "%", "consumption effect / change"),
        ("step_2008_2010_use_change", st.loc[("EU27_2020", 2008), "consumption_change_pct"], "%", "trend_steps"),
        (f"step_{A}_{B}_change", st.loc[("EU27_2020", A), "rate_change_pts"], "change in rate", "trend_steps; 2024 estimated"),
        (f"step_{A}_{B}_use_share", st.loc[("EU27_2020", A), "consumption_effect_pts"]
         / st.loc[("EU27_2020", A), "rate_change_pts"] * 100, "%", "consumption effect / change"),
        (f"step_{A}_{B}_use_change", st.loc[("EU27_2020", A), "consumption_change_pct"], "%", "trend_steps"),
        ("steps_using_less_added", eu_steps.loc[eu_steps["consumption_change_pct"] < 0, "consumption_effect_pts"].sum(),
         "change in rate", "consumption effects in steps when use fell"),
        ("steps_using_more_took_back", eu_steps.loc[eu_steps["consumption_change_pct"] >= 0, "consumption_effect_pts"].sum(),
         "change in rate", "consumption effects in steps when use rose"),
        ("pace_needed_per_year", (target * 100 - eu.rate_pct) / (2030 - YEAR), "change in rate a year", "(24 - rate) / 8"),
        (f"rate_{B}", rate_at[B], "%", f"env_ac_cur, {B}: the newest published rate; imputed by Eurostat"),
        (f"rate_{S1}", rate_at[S1], "%", f"env_ac_cur, {S1}: the first year with country rates"),
        (f"rise_{S1}_{B}", rate_at[B] - rate_at[S1], "change in rate", f"rate in {B} - rate in {S1}"),
        (f"pace_needed_per_year_from_{B}", (target * 100 - rate_at[B]) / (2030 - B), "change in rate a year",
         f"(24 - rate in {B}) / {2030 - B}"),
        (f"ireland_rank_from_lowest_{YEAR}", rank_from_lowest("IE", YEAR), "rank", "env_ac_cur, 27 member states, 1 the lowest"),
        (f"ireland_rank_from_lowest_{B}", rank_from_lowest("IE", B), "rank",
         "env_ac_cur, 27 member states, 1 the lowest; ties share the lower rank; imputed by Eurostat"),
        ("not_recycled_buried_share", not_recycled_share("EU27_2020", ["DSP_L", "RCV_B"]), "%",
         "env_wastrt: landfilled (D1, D5, D12) plus backfilled, over treated less recycled"),
        ("not_recycled_landfill_and_other_disposal_share", not_recycled_share("EU27_2020", ["DSP_L_OTH"]), "%",
         "env_wastrt: D1 to D7 and D12, over treated less recycled"),
        ("not_recycled_backfilled_share", not_recycled_share("EU27_2020", ["RCV_B"]), "%",
         "env_wastrt: backfilled, over treated less recycled"),
        ("ireland_not_recycled_buried_share", not_recycled_share("IE", ["DSP_L", "RCV_B"]), "%",
         "env_wastrt: as above, Ireland"),
        ("ireland_not_recycled_backfilled_share", not_recycled_share("IE", ["RCV_B"]), "%",
         "env_wastrt: backfilled, over treated less recycled, Ireland"),
        (f"pace_{S0}_{B}_per_year", eu_steps["rate_change_pts"].sum() / (B - S0), "change in rate a year", "change over the steps / years"),
        ("use_per_person", dmc("EU27_2020", "TOTAL", YEAR, "T_HAB"), "t", "DMC per person"),
        ("other_products_share", (dmc("EU27_2020", "MF5", YEAR) + dmc("EU27_2020", "MF6", YEAR))
         / dmc("EU27_2020", "TOTAL", YEAR) * 100, "%", "DMC of other products and waste for final treatment (MF5, MF6) / DMC; left out of the shards"),
        ("weight_shares_max_gap", max(abs(WEIGHT_VS_CLIMATE[g][0] - mix.loc["EU27_2020", f"{k}_pct"])
                                      for g, k in zip(WEIGHT_VS_CLIMATE, ["minerals", "biomass", "fossil", "metals"])),
         "%", "largest gap between ETC Figure 3-4's weight shares and Eurostat's (weight_mix)"),
        ("use_per_person_a_day", dmc("EU27_2020", "TOTAL", YEAR, "T_HAB") * 1000 / 365, "kg", "DMC per person x 1000 / 365"),
        ("use_per_person_to_close_by_using_less", dmc("EU27_2020", "TOTAL", YEAR, "T_HAB")
         * eu.less_consumption_for_eu_target_today_pct / 100, "t", "per person x 59.3%"),
        ("threshold_recycled_per_tonne_today", U / D, "t per t", "U / DMC"),
        ("threshold_recycled_per_tonne_every_tonne", (U + N) / D, "t per t", "(U + not yet recycled) / DMC"),
        *[(f"recycled_per_tonne_used_{k}", wm.loc[g, "recycled_kt"] / dmc("EU27_2020", FLOW_MATERIALS[g], YEAR),
           "t per t", "env_wassd recycled / DMC") for k, g in
          [("fossil", "Fossil fuels"), ("biomass", "Biomass"), ("minerals", "Non-metallic minerals"), ("metals", "Metal ores")]],
        ("minerals_share_of_recycled", wm.loc["Non-metallic minerals", "recycled_kt"] / wm["recycled_kt"].sum() * 100, "%",
         "env_wassd recycled, minerals over the four groups"),
        ("record_steps_use_fell", len(fell), "steps", "EU two-year steps since 2004 with consumption falling"),
        ("record_steps_circular_use_rose_or_held", int((fell["circular_use_change_pct"] >= 0).sum()), "steps", "of those"),
        ("record_circular_use_2012_2014", st.loc[("EU27_2020", 2012), "circular_use_change_pct"], "%", "trend_steps"),
        ("record_circular_use_2018_2020", st.loc[("EU27_2020", 2018), "circular_use_change_pct"], "%", "trend_steps"),
        (f"record_minerals_use_{A}_{B}", (dmc("EU27_2020", "MF3", B) / dmc("EU27_2020", "MF3", A) - 1) * 100, "%", "DMC; 2024 estimated"),
        (f"record_minerals_waste_{A}_{B}", (wassd[("MF3", B)] / wassd[("MF3", A)] - 1) * 100, "%", "env_wassd treated"),
        (f"record_fossil_use_{A}_{B}", (dmc("EU27_2020", "MF4", B) / dmc("EU27_2020", "MF4", A) - 1) * 100, "%", "DMC"),
        (f"record_fossil_waste_{A}_{B}", (wassd[("MF4", B)] / wassd[("MF4", A)] - 1) * 100, "%", "env_wassd treated"),
        ("record_ireland_use_2010_2012", st.loc[("IE", 2010), "consumption_change_pct"], "%", "trend_steps"),
        ("record_ireland_circular_use_2010_2012", st.loc[("IE", 2010), "circular_use_change_pct"], "%", "trend_steps"),
        (f"record_finland_use_{A}_{B}", st.loc[("FI", A), "consumption_change_pct"], "%", "trend_steps"),
        (f"record_finland_circular_use_{A}_{B}", st.loc[("FI", A), "circular_use_change_pct"], "%", "trend_steps"),
        ("fall_2008_2010_minerals_share", fall("EU27_2020", "MF3", 2008, 2010) / fall("EU27_2020", "TOTAL", 2008, 2010) * 100,
         "%", "DMC fall, minerals over total"),
        (f"fall_{A}_{B}_fossil_share", fall("EU27_2020", "MF4", A, B) / fall("EU27_2020", "TOTAL", A, B) * 100,
         "%", "DMC fall, fossil over total"),
        (f"fall_{A}_{B}_minerals_share", fall("EU27_2020", "MF3", A, B) / fall("EU27_2020", "TOTAL", A, B) * 100,
         "%", "DMC fall, minerals over total"),
        (f"fall_{A}_{B}_biomass_change", -fall("EU27_2020", "MF1", A, B), "kt", "DMC, biomass 2024 less 2022"),
        (f"fossil_fall_{A}_{B}", fall("EU27_2020", "MF4", A, B) / 1000, "Mt", "DMC"),
        ("fossil_fall_coal_share", fall("EU27_2020", "MF41", A, B) / fall("EU27_2020", "MF4", A, B) * 100, "%",
         "coal and other solids over all fossil"),
        (f"fossil_imports_fall_{A}_{B}", (mv[("EU27_2020", "IMP", "MF4", "THS_T", A)]
                                           - mv[("EU27_2020", "IMP", "MF4", "THS_T", B)]) / 1000, "Mt", "imports"),
        (f"gas_imports_fall_{A}_{B}", (mv[("EU27_2020", "IMP", "MF422", "THS_T", A)]
                                        - mv[("EU27_2020", "IMP", "MF422", "THS_T", B)]) / 1000, "Mt", "imports"),
        (f"use_change_{N1}", (dmc("EU27_2020", "TOTAL", N1) / dmc("EU27_2020", "TOTAL", B) - 1) * 100, "%",
         "DMC, 2025 imputed by Eurostat"),
        (f"use_{N1}_returned_of_drop", -fall("EU27_2020", "TOTAL", B, N1) / fall("EU27_2020", "TOTAL", A, B) * 100,
         "%", "2025 rise / 2022 to 2024 fall"),
        (f"use_{N1}_rebound_minerals_share", fall("EU27_2020", "MF3", B, N1) / fall("EU27_2020", "TOTAL", B, N1) * 100,
         "%", "minerals' rise over total rise"),
        (f"use_{N1}_minerals_recovered", -fall("EU27_2020", "MF3", B, N1) / fall("EU27_2020", "MF3", A, B) * 100,
         "%", "minerals' 2025 rise / their 2022 to 2024 fall"),
        (f"use_{N1}_fossil_change", (dmc("EU27_2020", "MF4", N1) / dmc("EU27_2020", "MF4", B) - 1) * 100, "%", "DMC"),
        ("rate_with_no_fossil_fuels", rate_with(U, no_fossil), "%", "U / (U + DMC - fossil), recycling held"),
        ("rate_with_no_fossil_or_metals", rate_with(U, no_fossil_metals), "%", "U / (U + DMC - fossil - metals)"),
        ("fossil_and_metals_share_of_cut", (D - no_fossil_metals) / cut_kt * 100, "%", "(fossil + metals) / cut to close"),
        ("cut_to_close_kt", cut_kt, "kt", "59.3% x DMC"),
        ("material_not_coming_back_kt", D - T, "kt", "DMC - waste treated"),
        ("cut_share_of_material_not_coming_back", cut_kt / (D - T) * 100, "%", "cut / (DMC - waste treated)"),
        ("waste_exported_for_recycling_kt", wm["exported_for_recycling_kt"].sum(), "kt", "env_ac_sd, four groups"),
        ("waste_imported_for_recycling_kt", wm["imported_for_recycling_kt"].sum(), "kt", "env_ac_sd, four groups"),
        ("metals_exported_for_recycling_kt", wm.loc["Metal ores", "exported_for_recycling_kt"], "kt", "env_ac_sd"),
        ("metals_imported_for_recycling_kt", wm.loc["Metal ores", "imported_for_recycling_kt"], "kt", "env_ac_sd"),
        ("metals_exported_share_of_circular_use", wm.loc["Metal ores", "exported_for_recycling_kt"]
         / wm.loc["Metal ores", "net_recycled_kt"] * 100, "%", "metals exported for recycling / metals' circular use"),
        (f"nl_rate_{YEAR}", c.loc["NL", "rate_pct"], "%", "published"),
        ("nl_use_per_person", dmc("NL", "TOTAL", YEAR, "T_HAB"), "t", "DMC per person"),
        ("nl_exported_share", loop.set_index("geo").loc["NL", "exported_pct"], "%", "loop: exported / processed"),
        ("countries_exported_share_median", countries["exported_pct"].median(), "%", "loop, the 27 countries"),
        ("nl_minerals_share_rank_lowest", int(mix["minerals_pct"].drop("EU27_2020").rank().loc["NL"]), "rank", "weight_mix, 1 = least"),
        ("nl_fossil_share_rank_highest", int(mix["fossil_pct"].drop("EU27_2020").rank(ascending=False).loc["NL"]), "rank",
         "weight_mix, 1 = most"),
        (f"nl_step_{A}_{B}_change", st.loc[("NL", A), "rate_change_pts"], "change in rate", "trend_steps; 2024 estimated"),
        (f"nl_rate_{B}", st.loc[("NL", A), "rate_to_pct"], "%", "estimate"),
        (f"nl_step_{A}_{B}_use_share", st.loc[("NL", A), "consumption_effect_pts"]
         / st.loc[("NL", A), "rate_change_pts"] * 100, "%", "consumption effect / change"),
        (f"nl_step_{A}_{B}_use_change", st.loc[("NL", A), "consumption_change_pct"], "%", "trend_steps"),
        (f"nl_fall_{A}_{B}_fossil_share", fall("NL", "MF4", A, B) / nl_fall * 100, "%", "DMC fall"),
        (f"nl_fall_{A}_{B}_gas_share", fall("NL", "MF422", A, B) / nl_fall * 100, "%",
         "natural gas: extraction + imports - exports"),
        ("nl_step_2014_2016_change", st.loc[("NL", 2014), "rate_change_pts"], "change in rate", "trend_steps"),
        ("nl_step_2014_2016_use_change", st.loc[("NL", 2014), "consumption_change_pct"], "%", "trend_steps"),
        # The waterfall explorer's country cards
        ("de_step_2022_2024_use_change", st.loc[("DE", 2022), "consumption_change_pct"], "%", "trend_steps; DMC reported"),
        ("de_fall_2022_2024_minerals_share", fall("DE", "MF3", 2022, 2024) / fall("DE", "TOTAL", 2022, 2024) * 100,
         "%", "DMC fall, minerals over total; biomass rose, so the shares add to more than 100"),
        ("de_fall_2022_2024_fossil_share", fall("DE", "MF4", 2022, 2024) / fall("DE", "TOTAL", 2022, 2024) * 100,
         "%", "DMC fall, fossil over total"),
        ("de_fall_2022_2024_lignite_share", fall("DE", "MF411", 2022, 2024) / fall("DE", "TOTAL", 2022, 2024) * 100,
         "%", "DMC fall, lignite (MF411) over total"),
        ("lv_step_2022_2024_use_change", st.loc[("LV", 2022), "consumption_change_pct"], "%", "trend_steps; DMC reported"),
        ("lv_fall_2022_2024_biomass_share", fall("LV", "MF1", 2022, 2024) / fall("LV", "TOTAL", 2022, 2024) * 100,
         "%", "DMC fall, biomass over total"),
        ("lv_fall_2022_2024_minerals_share", fall("LV", "MF3", 2022, 2024) / fall("LV", "TOTAL", 2022, 2024) * 100,
         "%", "DMC fall, minerals over total"),
        ("lv_fall_2022_2024_biomass_and_minerals_share",
         (fall("LV", "MF1", 2022, 2024) + fall("LV", "MF3", 2022, 2024)) / fall("LV", "TOTAL", 2022, 2024) * 100,
         "%", "DMC fall, biomass plus minerals over total"),
        ("se_recycled_outside_major_mineral_2020", recycled("SE", 2020, "TOT_X_MIN") / 1000, "Mt",
         "env_wastrt RCV_R, TOT_X_MIN"),
        ("se_recycled_outside_major_mineral_2022", recycled("SE", 2022, "TOT_X_MIN") / 1000, "Mt",
         "env_wastrt RCV_R, TOT_X_MIN"),
        ("se_extra_recycling_2020_2022_major_mineral_share", major_mineral_share_of_change("SE", 2020, 2022), "%",
         "env_wastrt RCV_R: change in (TOTAL - TOT_X_MIN) over change in TOTAL; its kinds are confidential for 2022"),
        ("dk_extra_recycling_2020_2022_soil_rock_share", soil_rock_share_of_change("DK", 2020, 2022), "%",
         "env_wastrt RCV_R: change in W126 + W127 + W12B over change in TOTAL"),
        ("fr_recycling_fall_2018_2020_soil_rock_share", soil_rock_share_of_change("FR", 2018, 2020), "%",
         "as above, of the fall; env_wastrt's recycled fell 26%, the card's 31% is circular use (trend_steps)"),
        ("sk_extra_recycling_2018_2020_soil_rock_share", soil_rock_share_of_change("SK", 2018, 2020), "%",
         "env_wastrt RCV_R: change in W126 + W127 + W12B over change in TOTAL"),
        ("fi_rate_2024_estimated", st.loc[("FI", 2022), "rate_to_pct"], "%", "env_ac_cur, imputed by Eurostat"),
        ("fi_circular_use_2022_2024_change_estimated", st.loc[("FI", 2022), "circular_use_change_pct"], "%",
         "trend_steps, from the estimated rate"),
        ("fi_waste_recycled_2022_2024_change", (recycled("FI", 2024) / recycled("FI", 2022) - 1) * 100, "%",
         "env_wastrt RCV_R, TOTAL, 2024 as published October 2026"),
        ("fi_rate_2024_if_circular_use_followed_waste", rate_with(fi_u24, dmc("FI", "TOTAL", 2024)), "%",
         "U_2022 = rate / (100 - rate) x DMC_2022, scaled by env_wastrt's recycled 2024 / 2022; U / (U + DMC_2024)"),
        ("ee_oil_shale_2018_2020_change", (dmc("EE", "MF413", 2020) / dmc("EE", "MF413", 2018) - 1) * 100, "%",
         "DMC, oil shale and tar sands (MF413)"),
        ("ro_minerals_2018", dmc("RO", "MF3", 2018) / 1000, "Mt", "DMC; total DMC imputed by Eurostat for 2009 to 2019"),
        ("ro_minerals_2020", dmc("RO", "MF3", 2020) / 1000, "Mt", "DMC"),
        ("ro_minerals_2018_2020_change", (dmc("RO", "MF3", 2020) / dmc("RO", "MF3", 2018) - 1) * 100, "%", "DMC"),
        (f"countries_used_less_{A}_{B}", int((st.xs(A, level="from_year").drop("EU27_2020")["consumption_change_pct"] < 0).sum()),
         "countries", f"trend_steps, {A} to {B}: consumption_change_pct below 0"),
        (f"countries_rate_{B}_estimated", int((trend[(trend["year"] == B) & (trend["geo"] != "EU27_2020")]["rate_flag"]
                                               .fillna("") != "").sum()),
         "countries", f"trend: a flag on Eurostat's {B} rate"),
        ("countries_split_flagged", by_material[(by_material["geo"] != "EU27_2020")
                                                    & (by_material["check"].fillna("") != "")]["geo"].nunique(),
         "countries", "waste_by_material: any material with a check"),
        ("minerals_imported_share", next(m["imports_over_dmi_pct"] for m in imports_block()["materials"]
                                         if m["material_group"] == "Non-metallic minerals"), "%",
         "extra-EU imports of non-metallic minerals over their direct material input (env_ac_mfa)"),
        ("lu_waste_imported_for_recycling", by_material[by_material["geo"] == "LU"]["imported_for_recycling_kt"].sum(), "kt",
         "waste_by_material: imported_for_recycling_kt over the four groups (env_ac_sd)"),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "unit", "calculation"])


def examples_table():
    """Every figure the page states for its examples (ZIN, IKEA's kitchens and the two compared),
    from the datapoints in data/examples/examples_input.csv, each with its calculation and the
    register entries (F numbers) and sources behind its inputs. ZIN's carbon saving is one-off,
    Winnow's yearly, and IKEA's a total since FY17 (F66)."""
    inputs = pd.read_csv(EXAMPLES / "examples_input.csv").set_index(["example", "metric"])
    v = inputs["value"].dropna()
    zin = lambda m: v[("zin", m)]
    ikea = lambda m: v[("ikea", m)]

    def refs(names):
        """The F numbers and source ids behind the named inputs, such as "zin.structure_kept"."""
        rows = [inputs.loc[tuple(n.split("."))] for n in names]
        fs = sorted({r["f_number"] for r in rows if isinstance(r["f_number"], str)}, key=lambda f: int(f[1:]))
        return "; ".join(fs), "; ".join(sorted({r["source_id"] for r in rows if isinstance(r["source_id"], str)}))

    def given(example, metric):
        """An input the page states as published."""
        r = inputs.loc[(example, metric)]
        where = f"{r['source_id']}, {r['locator']}" if isinstance(r["locator"], str) else r["source_id"]
        return (example, metric, r["value"], r["unit"], f"as published ({where})", [f"{example}.{metric}"])

    kg_per_meal = ikea("winnow_food_saved_per_year") * 1000 / (ikea("winnow_meals_per_second") * SECONDS_A_YEAR)
    winnow_ratio = ikea("winnow_co2e_per_year") / ikea("winnow_food_saved_per_year")
    ikea_t = ikea("meals_saved") * kg_per_meal / 1000
    ikea_ratio = ikea("co2e_avoided") / ikea_t
    benchmark = zin("upfront_per_m2") + zin("upfront_saved_per_m2")
    original = zin("structure_kept") / (zin("structure_kept_share") / 100)
    zin_ratio = zin("upfront_saved_total") / zin("structure_kept")
    both_t = zin("structure_kept") + ikea_t
    both_c = zin("upfront_saved_total") + ikea("co2e_avoided")
    WINNOW = ["ikea.winnow_food_saved_per_year", "ikea.winnow_meals_per_second"]
    IKEA_T = ["ikea.meals_saved"] + WINNOW
    ZIN_PT = ["zin.upfront_saved_total", "zin.structure_kept"]
    IKEA_PT = ["ikea.co2e_avoided"] + IKEA_T
    rows = [
        # ZIN and its note
        given("zin", "upfront_per_m2"),
        given("zin", "upfront_saved_per_m2"),
        ("zin", "benchmark_upfront_per_m2", benchmark, "kg CO2/m2",
         "upfront_per_m2 + upfront_saved_per_m2, reading the 377 as the whole building",
         ["zin.upfront_per_m2", "zin.upfront_saved_per_m2"]),
        ("zin", "building_upfront_cut_check", zin("upfront_saved_per_m2") / benchmark * 100, "%",
         "upfront_saved_per_m2 / benchmark_upfront_per_m2, against the paper's 33%",
         ["zin.upfront_per_m2", "zin.upfront_saved_per_m2"]),
        given("zin", "building_upfront_cut"),
        given("zin", "structure_upfront_cut"),
        ("zin", "structure_benchmark_per_m2", zin("upfront_saved_per_m2") / (zin("structure_upfront_cut") / 100),
         "kg CO2/m2", "upfront_saved_per_m2 / structure_upfront_cut",
         ["zin.upfront_saved_per_m2", "zin.structure_upfront_cut"]),
        given("zin", "upfront_saved_total"),
        ("zin", "implied_area", zin("upfront_saved_total") * 1000 / zin("upfront_saved_per_m2"), "m2",
         "upfront_saved_total / upfront_saved_per_m2; the paper doesn't state its area basis",
         ["zin.upfront_saved_total", "zin.upfront_saved_per_m2"]),
        given("zin", "fig14_benchmark_total"),
        given("zin", "fig14_upfront_total"),
        ("zin", "fig14_benchmark_area", zin("fig14_benchmark_total") * 1000 / benchmark, "m2",
         "fig14_benchmark_total / benchmark_upfront_per_m2",
         ["zin.fig14_benchmark_total", "zin.upfront_per_m2", "zin.upfront_saved_per_m2"]),
        ("zin", "fig14_upfront_area", zin("fig14_upfront_total") * 1000 / zin("upfront_per_m2"), "m2",
         "fig14_upfront_total / upfront_per_m2", ["zin.fig14_upfront_total", "zin.upfront_per_m2"]),
        given("zin", "built_area_architects"),
        given("zin", "floor_area_above_ground"),
        given("zin", "floor_area_basements"),
        given("zin", "structure_kept"),
        given("zin", "structure_kept_share"),
        ("zin", "original_structure", original, "t", "structure_kept / structure_kept_share",
         ["zin.structure_kept", "zin.structure_kept_share"]),
        ("zin", "slabs_demolished", original - zin("structure_kept"), "t", "original_structure - structure_kept",
         ["zin.structure_kept", "zin.structure_kept_share"]),
        ("zin", "slabs_share_of_structure", 100 - zin("structure_kept_share"), "%", "100 - structure_kept_share",
         ["zin.structure_kept_share"]),
        given("zin", "rubble_to_aggregate"),
        given("zin", "aggregate_into_zin"),
        given("zin", "aggregate_radius"),
        ("zin", "tonnes_kept_per_tonne_recycled", zin("structure_kept") / zin("rubble_to_aggregate"), "t per t",
         "structure_kept / rubble_to_aggregate", ["zin.structure_kept", "zin.rubble_to_aggregate"]),
        ("zin", "tonnes_kept_per_tonne_into_zin", zin("structure_kept") / zin("aggregate_into_zin"), "t per t",
         "structure_kept / aggregate_into_zin", ["zin.structure_kept", "zin.aggregate_into_zin"]),
        ("zin", "co2_per_tonne_kept", zin_ratio, "t CO2 per t", "upfront_saved_total / structure_kept", ZIN_PT),
        ("zin", "tonnes_kept_per_tonne_co2", 1 / zin_ratio, "t per t CO2", "structure_kept / upfront_saved_total", ZIN_PT),
        ("zin", "module_d_credit_per_m2", zin("whole_life_per_m2") - zin("whole_life_with_credits_per_m2"),
         "kg CO2/m2", "whole_life_per_m2 - whole_life_with_credits_per_m2",
         ["zin.whole_life_per_m2", "zin.whole_life_with_credits_per_m2"]),
        ("zin", "existing_reused_or_recycled_share",
         zin("existing_reused_on_site_share") + zin("existing_recycled_share"), "%",
         "existing_reused_on_site_share + existing_recycled_share",
         ["zin.existing_reused_on_site_share", "zin.existing_recycled_share"]),
        # IKEA's kitchens and its note
        given("ikea", "food_waste_cut"),
        ("ikea", "heap_2022_share_of_2017", 100 - ikea("food_waste_cut"), "%",
         "100 - food_waste_cut: 2022's heap's area as a share of 2017's (make_heaps.py)", ["ikea.food_waste_cut"]),
        given("ikea", "food_waste_cut_fy24"),
        given("ikea", "meals_saved"),
        given("ikea", "co2e_avoided"),
        given("ikea", "restaurants"),
        given("ikea", "ingka_share_of_ikea_sales"),
        given("ikea", "ikea_franchisees"),
        given("ikea", "ingka_stake_in_winnow"),
        given("ikea", "kitchen_waste_share_low"),
        given("ikea", "kitchen_waste_share_high"),
        ("ikea", "food_spend_saved_by_halving_low", ikea("kitchen_waste_share_low") / 2, "%",
         "kitchen_waste_share_low / 2", ["ikea.kitchen_waste_share_low"]),
        ("ikea", "food_spend_saved_by_halving_high", ikea("kitchen_waste_share_high") / 2, "%",
         "kitchen_waste_share_high / 2", ["ikea.kitchen_waste_share_high"]),
        # Winnow's fleet, behind IKEA's tonnes of food
        given("ikea", "winnow_food_saved_per_year"),
        given("ikea", "winnow_co2e_per_year"),
        given("ikea", "winnow_meals_per_second"),
        ("ikea", "winnow_kg_per_meal", kg_per_meal, "kg",
         "winnow_food_saved_per_year / (winnow_meals_per_second x seconds in a year)", WINNOW),
        ("ikea", "winnow_co2e_per_tonne", winnow_ratio, "t CO2e per t",
         "winnow_co2e_per_year / winnow_food_saved_per_year; Winnow publishes no factor",
         ["ikea.winnow_co2e_per_year", "ikea.winnow_food_saved_per_year"]),
        ("ikea", "food_saved_to_2022", ikea_t, "t",
         "meals_saved x winnow_kg_per_meal; an estimate, as Ingka publishes meals, not tonnes", IKEA_T),
        ("ikea", "food_saved_fy17_fy25", ikea("meals_saved_fy17_fy25") * kg_per_meal / 1000, "t",
         "meals_saved_fy17_fy25 x winnow_kg_per_meal; an estimate", ["ikea.meals_saved_fy17_fy25"] + WINNOW),
        ("ikea", "food_saved_fy25", ikea("meals_saved_fy25") * kg_per_meal / 1000, "t",
         "meals_saved_fy25 x winnow_kg_per_meal; an estimate", ["ikea.meals_saved_fy25"] + WINNOW),
        ("ikea", "co2e_per_tonne", ikea_ratio, "t CO2e per t",
         "co2e_avoided / food_saved_to_2022; both totals since FY17", IKEA_PT),
        ("ikea", "share_of_winnow_2022_if_yearly",
         ikea("co2e_avoided") / winnow_ratio * 1000 / kg_per_meal / ikea("winnow_meals_per_year_2022") * 100, "%",
         "meals the 36,000 t would mean if yearly, at Winnow's ratios, over Winnow's whole fleet in 2022",
         ["ikea.co2e_avoided", "ikea.winnow_co2e_per_year", "ikea.winnow_meals_per_year_2022"] + WINNOW),
        # The two compared, no longer on the page: each column is 100% of what the two saved together
        ("comparison", "structure_share_of_tonnes_saved", zin("structure_kept") / both_t * 100, "%",
         "structure_kept / (structure_kept + food_saved_to_2022)", ["zin.structure_kept"] + IKEA_T),
        ("comparison", "food_share_of_tonnes_saved", ikea_t / both_t * 100, "%",
         "food_saved_to_2022 / (structure_kept + food_saved_to_2022)", ["zin.structure_kept"] + IKEA_T),
        ("comparison", "structure_share_of_carbon_saved", zin("upfront_saved_total") / both_c * 100, "%",
         "upfront_saved_total / (co2e_avoided + upfront_saved_total); CO2 and CO2e, one-off and total since FY17",
         ["zin.upfront_saved_total", "ikea.co2e_avoided"]),
        ("comparison", "food_share_of_carbon_saved", ikea("co2e_avoided") / both_c * 100, "%",
         "co2e_avoided / (co2e_avoided + upfront_saved_total); CO2e and CO2, total since FY17 and one-off",
         ["zin.upfront_saved_total", "ikea.co2e_avoided"]),
        ("comparison", "food_vs_structure_per_tonne", ikea_ratio / zin_ratio, "times",
         "ikea.co2e_per_tonne / zin.co2_per_tonne_kept; the page rounds it down to roughly 30", ZIN_PT + IKEA_PT),
        ("comparison", "ikea_food_vs_zin_structure", ikea_t / zin("structure_kept") * 100, "%",
         "food_saved_to_2022 / structure_kept", ["zin.structure_kept"] + IKEA_T),
        ("comparison", "ikea_co2e_vs_zin", ikea("co2e_avoided") / zin("upfront_saved_total"), "times",
         "IKEA's total since FY17 / ZIN's one-off saving", ["zin.upfront_saved_total", "ikea.co2e_avoided"]),
        ("comparison", "winnow_food_vs_zin_structure",
         ikea("winnow_food_saved_per_year") / zin("structure_kept") * 100, "%",
         "Winnow's yearly food saved / structure_kept", ["ikea.winnow_food_saved_per_year", "zin.structure_kept"]),
        ("comparison", "winnow_co2e_vs_zin", ikea("winnow_co2e_per_year") / zin("upfront_saved_total"), "times",
         "Winnow's yearly CO2e / ZIN's one-off saving", ["ikea.winnow_co2e_per_year", "zin.upfront_saved_total"]),
    ]
    table = [(e, m, val, unit, calc, *refs(names)) for e, m, val, unit, calc, names in rows]
    return pd.DataFrame(table, columns=["example", "metric", "value", "unit", "calculation", "f_numbers", "sources"])


def examples_block(examples):
    """The examples' figures the page draws (ZIN's and IKEA's kitchens' panels), from examples.csv."""
    v = examples.set_index(["example", "metric"])["value"]
    num = lambda x: int(x) if float(x).is_integer() else round(float(x), 3)
    return {
        "zin": {m: num(v[("zin", m)]) for m in ["benchmark_upfront_per_m2", "upfront_per_m2", "upfront_saved_per_m2",
                                                 "upfront_saved_total"]},
        "ikea": {m: num(v[("ikea", m)]) for m in ["food_waste_cut", "food_waste_cut_fy24", "meals_saved"]},
    }


def page_data(ceilings, trend, steps, materials, mix, loop, flows_m, levers, unrecycled, generated,
              waste_in_flows_kt, footprint, climate, by_material, dmc_by_group, names, geos, examples, cut_curve):
    """Everything the web page draws, rounded for display, as one JavaScript file."""
    def r(x, digits=2):
        return None if pd.isna(x) else round(float(x), digits)

    c = ceilings.set_index("geo")
    t = trend.set_index(["geo", "year"])
    s = steps.set_index(["geo", "from_year"])
    lv = levers.set_index("geo")
    lp = loop.set_index("geo")
    bm = by_material.set_index(["geo", "material"])

    def by_step(g, key):
        return [r(s.loc[(g, y), key], 3) if (g, y) in s.index else None for y in STEP_YEARS[:-1]]

    def where_it_goes(row):
        kt = [row[f"{name}_kt"] for name in list(LOOP_FLOWS) + ["back_as_waste"]]
        return {"material": row["material"], "processed_kt": r(row["processed_kt"], 0),
                "shares": [r(v / sum(kt) * 100) for v in kt],
                "soil_rock": r(row["back_as_soil_rock_kt"] / sum(kt) * 100)}

    eu = c.loc["EU27_2020"]
    eu_left = unrecycled[unrecycled["geo"] == "EU27_2020"].sort_values("unrecycled_kt", ascending=False)
    groups = [col for col in materials.columns if col not in ("country", "total")]
    countries = {}
    for g in geos:
        x = c.loc[g]
        countries[g] = {
            "name": names[g],
            **({"data_year": data_year(g)} if data_year(g) != YEAR else {}),
            "rate": r(x.rate_pct),
            "ceiling": r(x.ceiling_pct),
            "ceiling_without_soil_rock": r(x.ceiling_without_soil_rock_pct),
            "circular_use_kt": r(x.circular_use_kt, 0),
            "consumption_kt": r(x.consumption_kt, 0),
            "not_recycled_kt": r(x.waste_treated_kt - x.waste_recycled_kt, 0),
            "not_recycled_without_soil_rock_kt": r((x.waste_treated_kt - x.soil_rock_treated_kt)
                                                   - (x.waste_recycled_kt - x.soil_rock_recycled_kt), 0),
            "waste_treated_per_consumption": r(x.waste_treated_per_consumption_pct),
            "share_recycled": r(x.share_recycled_pct, 3),
            "share_soil_rock": r(x.share_soil_rock_pct),
            "ceiling_used": r(x.ceiling_used_pct, 1),
            "loop_per_100": [None if pd.isna(lp.loc[g, f"{k}_per_100"]) else int(lp.loc[g, f"{k}_per_100"])
                             for k in list(LOOP_FLOWS) + ["back_as_waste"]],
            "back_as_waste": r(lp.loc[g, "back_as_waste_pct"]),
            "back_as_soil_rock": r(lp.loc[g, "back_as_soil_rock_pct"]),
            "unaccounted": r(lp.loc[g, "unaccounted_pct"]),
            "materials": [r(materials.loc[g, k]) for k in groups],
            "materials_total": r(materials.loc[g, "total"]),
            "trend": {
                "rate": [r(t.loc[(g, y), "rate_pct"]) for y in REPORTING_YEARS],
                "ceiling": [r(t.loc[(g, y), "ceiling_pct"]) for y in REPORTING_YEARS],
                "ceiling_without_soil_rock": [r(t.loc[(g, y), "ceiling_without_soil_rock_pct"]) for y in REPORTING_YEARS],
            },
            "steps": {"recycling": by_step(g, "recycling_effect_pts"), "consumption": by_step(g, "consumption_effect_pts"),
                      "change": by_step(g, "rate_change_pts"), "consumption_change_pct": by_step(g, "consumption_change_pct")},
            "levers": {k: r(lv.loc[g, f"{k}_pts"], 3) for k in LEVERS},
            "less_for_target": {name: r(x[f"less_consumption_for_{name}_target_today_pct"]) for name in TARGETS},
            "less_for_target_without_soil_rock": {name: r(x[f"less_consumption_for_{name}_target_without_soil_rock_pct"])
                                                  for name in TARGETS},
            "less_for_target_70pct_recycled": {name: r(x[f"less_consumption_for_{name}_target_70pct_recycled_pct"], 3)
                                               for name in TARGETS},
            "mix": {k: r(mix.loc[g, f"{k}_pct"]) for k in MIX_GROUPS},
            # at the page's replacement, REPLACEMENT
            "extra_recycled_70pct_kt": r(np.maximum(0.0, EEA_RECYCLED_SHARE * x.waste_treated_kt - x.waste_recycled_kt), 0),
            "rate_70pct_recycled": r(x[f"rate_70pct_recycled_{PAGE_K}_pct"], 3),
            "rate_70pct_recycled_if_adding": r(x["rate_70pct_recycled_k0_pct"], 3),   # recycled tonnes replacing none
            "rate_without_soil_rock": r(x[f"rate_without_soil_rock_{PAGE_K}_pct"], 3),   # all but soil and rock recycled
            "replaced_70pct_recycled": {name: r(x[f"replaced_by_recycling_for_{name}_target_70pct_recycled_{PAGE_K}_pct"], 3)
                                        for name in TARGETS},
            "gone_without_70pct_recycled": {name: r(x[f"gone_without_for_{name}_target_70pct_recycled_{PAGE_K}_pct"], 3)
                                            for name in TARGETS},
            "recycled_share_to_close": r(x[f"recycled_share_to_close_eu_alone_{PAGE_K}_pct"], 3),
            "less_new_material_to_close": r(x[f"less_new_material_to_close_eu_alone_{PAGE_K}_pct"], 3),
            "not_recycled_mix": {k: r(bm.loc[(g, name), "share_of_not_recycled_pct"])
                                 for k, name in zip(MIX_GROUPS, FLOW_ORDER)},
            "waste_check": bm.loc[(g, "Biomass"), "check"] or None,
            "warning": EXPLORER_WARNINGS.get(g),
            "highlights": [{"from": a, "to": a + 2, "arrow": arrow,
                            "rate_from": r(s.loc[(g, a), "rate_from_pct"], 1),
                            "rate_to": r(s.loc[(g, a), "rate_to_pct"], 1),
                            "use_change_pct": r(s.loc[(g, a), "consumption_change_pct"], 1),
                            "circular_use_change_pct": r(s.loc[(g, a), "circular_use_change_pct"], 1),
                            "estimated": a + 2 > YEAR}
                           for a, arrow in WATERFALL_HIGHLIGHTS.get(g, [])],
        }
    data = {
        "year": YEAR,
        "data_as_of": DATA_AS_OF,
        "replacement": REPLACEMENT,      # new tonnes each extra recycled tonne replaces, an assumed midpoint
        "trend_years": REPORTING_YEARS,
        "trend_estimated_from": YEAR + 1,     # later years are Eurostat estimates
        "step_years": STEP_YEARS,
        "loop_flows": list(LOOP_FLOWS) + ["back_as_waste"],
        "material_groups": groups,
        "levers": LEVERS,
        "countries": countries,
        "flows_by_material": [where_it_goes(row) for row in flows_m[flows_m["geo"] == "EU27_2020"].to_dict("records")],
        "unrecycled": [{"kind": x.kind, "kt": r(x.unrecycled_kt, 0), "pct": r(x.share_pct, 1)} for x in eu_left.itertuples()],
        "household": {"generated_kt": r(generated.loc["EU27_2020", "EP_HH"], 0),
                      "share_of_generated_pct": r(generated.loc["EU27_2020", "EP_HH"] / generated.loc["EU27_2020", "TOTAL_HH"] * 100, 1),
                      "at_most_pts": r(lv.loc["EU27_2020", "recycling_household_waste_at_most_pts"], 3)},
        "waste_bases": {"in_flows_kt": r(waste_in_flows_kt, 0), "treated_kt": r(eu.waste_treated_kt, 0)},
        "footprint": [{k: (r(v) if isinstance(v, float) else v) for k, v in row.items() if k != "footprint_kt"}
                      for row in footprint.to_dict("records")],
        "climate_total_mt": CLIMATE_TOTAL_MT,
        "imports": imports_block(),
        "game": {
            "source": f"EU27_2020, {YEAR}. Material use by group: Eurostat env_ac_mfa, DMC. Waste not yet recycled by group: "
                      f"env_wassd, scaled to the rate's totals (waste_by_material_{YEAR}.csv)",
            "dmc_by_group_kt": {k: r(dmc_by_group[name], 3) for k, name in zip(MIX_GROUPS, FLOW_ORDER)},
            "not_recycled_kt": {k: r(bm.loc[("EU27_2020", name), "not_recycled_kt"], 3) for k, name in zip(MIX_GROUPS, FLOW_ORDER)},
        },
        "weight_vs_climate": [{k: (r(v) if isinstance(v, float) else v) for k, v in row.items()}
                              for row in climate.to_dict("records")],
        "examples": examples_block(examples),
        "cut_curve": {      # for the Method chart: the EU's cut for 24% at each share of waste recycled
            "recycled_share": [r(x, 2) for x in cut_curve["recycled_share_pct"]],
            "cut": [r(x, 2) for x in cut_curve["less_consumption_for_eu_target_pct"]],
            "replaced": {key: [r(x, 2) for x in cut_curve[f"replaced_by_recycling_{key}_pct"]]
                         for key in REPLACEMENTS if key != "k0"},
        },
    }
    return "window.FAR_FROM_FULL_CIRCLE_DATA = " + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + ";\n"


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
    extra_at_eea_share = np.maximum(0, EEA_RECYCLED_SHARE * treated - recycled)

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
        "ceiling_without_soil_rock_pct": ceiling(U + extra_without_sr),
        "rate_with_backfilling_pct": ceiling(U + backfilled),
        "rate_70pct_recycled_pct": ceiling(U + extra_at_eea_share),   # a higher share recycled is kept
        "waste_treated_per_consumption_pct": treated / dmc * 100,
        "share_recycled_pct": recycled / treated * 100,
        "share_backfilled_pct": backfilled / treated * 100,
        "share_soil_rock_pct": sr_treated / treated * 100,
        "ceiling_used_pct": r * 100 / ceiling(U + extra) * 100,
    }
    for name, target in TARGETS.items():
        row[f"less_consumption_for_{name}_target_today_pct"] = cut_for(target, U)
        row[f"less_consumption_for_{name}_target_without_soil_rock_pct"] = cut_for(target, U + extra_without_sr)
        row[f"less_consumption_for_{name}_target_70pct_recycled_pct"] = cut_for(target, U + extra_at_eea_share)
        row[f"less_consumption_for_{name}_target_everything_pct"] = cut_for(target, U + extra)

    # Replacement: each extra recycled tonne replaces k new tonnes of the same material. The new
    # material that has to go for a target at a given recycling level is the same at every k (the
    # columns above); k changes the rate recycling alone reaches and the split between what
    # recycling stands in for and what the country goes without.
    def rate_at(e, k):
        return (U + e) / (U + dmc + (1 - k) * e) * 100

    cases = {"today": 0.0, "without_soil_rock": extra_without_sr,
             "70pct_recycled": extra_at_eea_share, "everything": extra}
    for key, k in REPLACEMENTS.items():
        row[f"ceiling_{key}_pct"] = rate_at(extra, k)
        row[f"rate_without_soil_rock_{key}_pct"] = rate_at(extra_without_sr, k)
        row[f"rate_70pct_recycled_{key}_pct"] = rate_at(extra_at_eea_share, k)
        for name, target in TARGETS.items():
            need = (target * (U + dmc) - U) / (1 - target * (1 - k))   # extra recycled tonnes that close the ring alone
            row[f"recycled_share_to_close_{name}_alone_{key}_pct"] = (recycled + need) / treated * 100   # over 100: can't
            row[f"recycling_multiple_to_close_{name}_alone_{key}"] = (recycled + need) / recycled
            row[f"less_new_material_to_close_{name}_alone_{key}_pct"] = k * need / dmc * 100
            for case, e in cases.items():
                replaced = k * e / dmc * 100
                row[f"replaced_by_recycling_for_{name}_target_{case}_{key}_pct"] = replaced
                # zero when recycling alone passes the target; missing when its waste is unpublished
                row[f"gone_without_for_{name}_target_{case}_{key}_pct"] = np.maximum(0.0, cut_for(target, U + e) - replaced)
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
    GEO_YEAR.update(fallback_years(geos, rate, consumption, waste))
    for g, y in GEO_YEAR.items():
        print(f"Warning: {names[g]} has no rate, consumption or waste for {YEAR}; its figures are for {y}")

    # 1. The ceilings in YEAR, or a country's fallback year
    ceilings = pd.DataFrame([measures(g, data_year(g), rate, consumption, waste) for g in geos])
    ceilings.insert(1, "country", ceilings["geo"].map(names))
    ceilings.rename(columns={"year": "data_year"}).round(3).to_csv(OUT / f"ceilings_{YEAR}.csv", index=False)
    missing = ceilings.loc[ceilings[["rate_pct", "consumption_kt", "waste_treated_kt", "waste_recycled_kt"]]
                           .isna().any(axis=1), "country"].tolist()
    if missing:
        print(f"Warning: no rate, consumption or waste for {YEAR} in: {', '.join(missing)}")

    # 2. The same measures in every reporting year; 2024 values are Eurostat estimates
    trend = pd.DataFrame([measures(g, y, rate, consumption, waste) for g in geos for y in REPORTING_YEARS])
    trend.insert(1, "country", trend["geo"].map(names))
    trend["rate_flag"] = [rate_flag.get((g, y), "") for g, y in zip(trend["geo"], trend["year"])]
    trend["waste_flag"] = [waste_flag.get((g, y), "") for g, y in zip(trend["geo"], trend["year"])]
    trend.round(3).to_csv(OUT / "trend.csv", index=False)

    # 2b. Material use against circular use, with both ceilings expressed as circular use
    use = trend[["geo", "country", "year", "rate_pct", "consumption_kt", "circular_use_kt"]].copy()
    not_recycled = trend["waste_treated_kt"] - trend["waste_recycled_kt"]
    not_recycled_without_sr = ((trend["waste_treated_kt"] - trend["soil_rock_treated_kt"])
                               - (trend["waste_recycled_kt"] - trend["soil_rock_recycled_kt"]))
    use["circular_use_ceiling_kt"] = trend["circular_use_kt"] + not_recycled
    use["circular_use_ceiling_without_soil_rock_kt"] = trend["circular_use_kt"] + not_recycled_without_sr
    use["rate_flag"], use["waste_flag"] = trend["rate_flag"], trend["waste_flag"]
    use.round(3).to_csv(OUT / "material_vs_circular_use.csv", index=False)

    # 3. What moved the rate between the two ends of the trend
    by_year = trend.set_index(["geo", "year"])
    rows = []
    for g in geos:
        a, b = by_year.loc[(g, TREND_FROM)], by_year.loc[(g, TREND_TO)]
        rows.append({"geo": g, "country": names[g], "from_year": TREND_FROM, "to_year": TREND_TO,
                     "rate_from_pct": a["rate_pct"], "rate_to_pct": b["rate_pct"], **drivers(a, b)})
    trend_drivers = pd.DataFrame(rows)
    trend_drivers.round(3).to_csv(OUT / "trend_drivers.csv", index=False)

    # 3b. The same split for every two-year step
    steps = pd.DataFrame([x for g in geos for a, b in zip(STEP_YEARS, STEP_YEARS[1:])
                          if (x := step(g, a, b, rate, consumption)) is not None])
    steps.insert(1, "country", steps["geo"].map(names))
    steps.round(3).to_csv(OUT / "trend_steps.csv", index=False)

    # 4. What each country consumes, in kg per person a day
    per_person = mfa[(mfa["unit"] == "T_HAB") & in_data_year(mfa)].pivot(
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

    # 4b. The same consumption in the ring's four material groups, as shares of their sum by
    # weight; other products and waste for final treatment (MF5, MF6) are left out
    tonnes = mfa[(mfa["unit"] == "THS_T") & in_data_year(mfa)].pivot(
        index="geo", columns="material", values="value")
    four = tonnes[list(MIX_GROUPS.values())]
    mix = four.div(four.sum(axis=1), axis=0).mul(100).set_axis([f"{k}_pct" for k in MIX_GROUPS], axis=1)
    mix = mix.reindex(geos)
    mix.insert(0, "country", mix.index.map(names))
    mix.index.name = "geo"
    mix.round(3).to_csv(OUT / f"weight_mix_{YEAR}.csv")

    # 5. Where each country's processed material goes, in total and by material
    flows_sd, waste_sd = load_loop()
    loop = loop_table(flows_sd, waste_sd, ceilings, names, geos)
    loop.round(3).to_csv(OUT / f"loop_{YEAR}.csv", index=False)
    flows_m = flows_by_material_table(flows_sd, waste_sd, ceilings, names, geos)
    flows_m.round(3).to_csv(OUT / f"flows_by_material_{YEAR}.csv", index=False)

    # 5b. What each lever is worth, and what the unrecycled waste other than soil and rock is
    generated = load_generated()
    levers = levers_table(ceilings, mfa, generated["EP_HH"], names)
    levers.round(3).to_csv(OUT / f"levers_{YEAR}.csv", index=False)
    unrecycled = unrecycled_table(names, geos)
    unrecycled.round(3).to_csv(OUT / f"unrecycled_waste_{YEAR}.csv", index=False)

    # 5c. Waste by material, and recycling more and using less together, for the EU
    by_material = waste_by_material_table(ceilings, names, geos)
    by_material.round(3).to_csv(OUT / f"waste_by_material_{YEAR}.csv", index=False)
    dmc_by_group = {g: tonnes.loc["EU27_2020", code] for g, code in FLOW_MATERIALS.items()}
    two_levers = two_levers_table(ceilings, import_shares(), by_material, dmc_by_group)
    two_levers.round(3).to_csv(OUT / f"two_levers_{YEAR}.csv", index=False)

    cut_curve = cut_curve_table(ceilings)
    cut_curve.round(3).to_csv(OUT / f"cut_by_recycling_{YEAR}.csv", index=False)

    # 5d. The figures the cards quote
    headline_table(ceilings, steps, two_levers, by_material, loop, mix, trend).round(3).to_csv(
        OUT / f"headline_numbers_{YEAR}.csv", index=False)

    # 6. What the EU's material footprint ends up as
    footprint = footprint_table()
    footprint.round(3).to_csv(OUT / f"footprint_{YEAR}.csv", index=False)

    # 7. Weight against climate impact, from the report
    climate = pd.DataFrame(
        [(group, weight, impact) for group, (weight, impact) in WEIGHT_VS_CLIMATE.items()],
        columns=["material_group", "share_of_weight_pct", "share_of_climate_impact_pct"],
    )
    climate["impact_per_weight"] = climate["share_of_climate_impact_pct"] / climate["share_of_weight_pct"]
    climate["impact_per_tonne_vs_minerals"] = (
        climate["impact_per_weight"] / climate.set_index("material_group").loc["Non-metallic minerals", "impact_per_weight"])
    climate.round(3).to_csv(OUT / f"weight_vs_climate_{YEAR}.csv", index=False)

    # 7b. What the example datapoints imply
    examples = examples_table()
    examples.round(3).to_csv(OUT / "examples.csv", index=False)

    # 8. Everything the web page draws
    (OUT / "far_from_full_circle_data_build.js").write_text(
        page_data(ceilings, trend, steps, materials, mix, loop, flows_m, levers, unrecycled, generated,
                  loop.set_index("geo").loc["EU27_2020", "back_as_waste_kt"], footprint, climate, by_material,
                  dmc_by_group, names, geos, examples, cut_curve),
        encoding="utf-8")

    eu = ceilings.set_index("geo").loc["EU27_2020"]
    for key, k in REPLACEMENTS.items():
        print(f"EU {YEAR}, replacement {k}: every tonne recycled reaches {eu[f'ceiling_{key}_pct']:.1f}%; "
              f"alone, closes at {eu[f'recycled_share_to_close_eu_alone_{key}_pct']:.1f}% recycled, "
              f"{eu[f'less_new_material_to_close_eu_alone_{key}_pct']:.1f}% less new material; at 70%, "
              f"{eu[f'replaced_by_recycling_for_eu_target_70pct_recycled_{key}_pct']:.1f}% replaced and "
              f"{eu[f'gone_without_for_eu_target_70pct_recycled_{key}_pct']:.1f}% gone without")
    if YEAR != SHARES_YEAR:
        print(f"Warning: the climate total and Figure 3-4's shares are for {SHARES_YEAR}, the tables for {YEAR}")
    tl = two_levers[two_levers["replacement"] == PAGE_K]
    a, b = tl.iloc[0], tl.iloc[-1]
    print(f"EU {YEAR}, target by using less: {a.less_consumption_for_eu_target_pct:.1f}% less material at "
          f"{a.recycled_share_pct:.1f}% recycled, {b.less_consumption_for_eu_target_pct:.1f}% at "
          f"{b.recycled_share_pct:.0f}%")
    print(f"Wrote {len(ceilings)} countries to {OUT}/")


if __name__ == "__main__":
    main()
