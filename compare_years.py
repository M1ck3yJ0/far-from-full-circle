"""Compare the findings the page rests on between two data years, for the rebase.

Usage:
    python3 -I compare_years.py <old year> <new year> [<old processed dir>]

Run from the repo root after rebuilding at the new year. Reads the new year's tables from
data/processed, and the old year's from the given directory, or else data/processed, or else
the last commit (git show HEAD:...). Prints each finding the page states that depends on the
data year, old against new, marking every one that changes. Figures are the page's
replacement (half a new tonne) unless named.
"""
import io
import subprocess
import sys
from pathlib import Path

import pandas as pd

OLD, NEW = int(sys.argv[1]), int(sys.argv[2])
OUT = Path("data/processed")
OLD_DIR = Path(sys.argv[3]) if len(sys.argv) > 3 else OUT
EU, KS = "EU27_2020", ("k0", "k05", "k1")
K_NAMES = {"k0": "0:1", "k05": "0.5:1", "k1": "1:1"}


def table(name, year, directory):
    path = directory / f"{name}_{year}.csv"
    if path.exists():
        return pd.read_csv(path)
    text = subprocess.run(["git", "show", f"HEAD:{OUT / path.name}"], capture_output=True, text=True, check=True).stdout
    return pd.read_csv(io.StringIO(text))


def tables(year, directory):
    c = table("ceilings", year, directory).set_index("geo")
    h = table("headline_numbers", year, directory).drop_duplicates("metric").set_index("metric")["value"]
    w = table("waste_by_material", year, directory)
    return c, h, w


def countries(c):
    return c.drop(index=EU)


def names(c, geos):
    return ", ".join(c.loc[g, "country"] for g in geos) or "none"


def findings(year, c, h, w):
    eu, ctry = c.loc[EU], countries(c)
    reported = ctry.dropna(subset=["rate_pct", "consumption_kt", "waste_treated_kt"])
    f = {}
    f["Countries without the year's rate, consumption or waste"] = names(c, ctry.index.difference(reported.index))
    if "data_year" in c:
        earlier = ctry[ctry["data_year"] != year]
        f["Countries on an earlier year"] = "; ".join(
            f"{x.country} {int(x.data_year)}" for x in earlier.itertuples()) or "none"
    f["EU rate"] = f"{eu.rate_pct:.1f}%"
    f["Ring closed (rate over 24%)"] = f"{eu.rate_pct / 24 * 100:.1f}%"
    for k in KS:
        every = eu[f"ceiling_{k}_pct"]
        f[f"Every tonne recycled reaches, {K_NAMES[k]}"] = f"{every:.1f}%"
        close = eu[f"recycled_share_to_close_eu_alone_{k}_pct"]
        f[f"Recycling alone closes the ring, {K_NAMES[k]}"] = (
            "never" if every < 24 else
            f"at {close:.1f}% recycled, {eu[f'recycling_multiple_to_close_eu_alone_{k}']:.1f} times, "
            f"{eu[f'less_new_material_to_close_eu_alone_{k}_pct']:.1f}% less new material")
    f["Share of waste recycled"] = f"{eu.share_recycled_pct:.1f}%"
    f["Using less alone"] = f"{eu.less_consumption_for_eu_target_today_pct:.1f}%"
    f["At 70% recycled: cut, replaced, not replaced"] = (
        f"{eu.less_consumption_for_eu_target_70pct_recycled_pct:.1f}%, "
        f"{eu.replaced_by_recycling_for_eu_target_70pct_recycled_k05_pct:.1f}%, "
        f"{eu.gone_without_for_eu_target_70pct_recycled_k05_pct:.1f}%")
    f["Waste back, share of material consumed"] = f"{eu.waste_treated_per_consumption_pct:.1f}%"
    for k in KS:
        passing = reported.index[reported[f"rate_70pct_recycled_{k}_pct"] >= 24]
        f[f"Still have to use less at 70% recycled, {K_NAMES[k]}"] = f"{len(reported) - len(passing)} of {len(reported)}"
        f[f"Past 24% at 70% recycled, {K_NAMES[k]}"] = names(c, passing)
    passing = reported[reported["rate_70pct_recycled_k05_pct"] >= 24]
    short = passing.index[passing["rate_without_soil_rock_k05_pct"] < 24]
    f["Past 24% at 70%, short with all but soil and rock recycled"] = "; ".join(
        f"{c.loc[g, 'country']} {c.loc[g, 'rate_without_soil_rock_k05_pct']:.1f}%, soil and rock "
        f"{c.loc[g, 'share_soil_rock_pct']:.0f}% of treated" for g in short) or "none"
    over80 = reported.index[reported["less_consumption_for_eu_target_70pct_recycled_pct"] > 80]
    f["Cut over 80% at 70% recycled"] = names(c, over80)
    flagged = sorted(w.loc[w["check"].notna() & (w["geo"] != EU), "geo"].unique())
    f["Flagged per-material splits"] = f"{len(flagged)}: {names(c, flagged)}"
    f["Countries past 24% now"] = names(c, reported.index[reported["rate_pct"] >= 24])
    de = c.loc["DE"]
    f["Germany at 70%: cut, replaced, not replaced; its rate at 70%"] = (
        f"{de.less_consumption_for_eu_target_70pct_recycled_pct:.1f}%, "
        f"{de.replaced_by_recycling_for_eu_target_70pct_recycled_k05_pct:.1f}%, "
        f"{de.gone_without_for_eu_target_70pct_recycled_k05_pct:.1f}%; {de.rate_70pct_recycled_k05_pct:.1f}%")
    ie = c.loc["IE"]
    f["Ireland rate"] = f"{ie.rate_pct:.1f}%"
    f["Ireland every tonne recycled, 0:1 / 0.5:1 / 1:1"] = " / ".join(f"{ie[f'ceiling_{k}_pct']:.1f}%" for k in KS)
    f["Ireland at 70%: cut for 24%, for 12%"] = (
        f"{ie.less_consumption_for_eu_target_70pct_recycled_pct:.1f}%, "
        f"{ie.less_consumption_for_ireland_target_70pct_recycled_pct:.1f}%")
    f["Ireland soil and rock, share of treated"] = f"{ie.share_soil_rock_pct:.1f}%"
    for metric in ("use_per_person", "climate_cut_by_recycling_at_close_k05"):
        if metric in h:
            f[f"headline {metric}"] = f"{h[metric]:.2f}"
    return f


old, new = findings(OLD, *tables(OLD, OLD_DIR)), findings(NEW, *tables(NEW, OUT))
print(f"Findings, {OLD} against {NEW} (* changes)\n")
for key in old:
    mark = "*" if old[key] != new[key] else " "
    print(f"{mark} {key}\n    {OLD}: {old[key]}\n    {NEW}: {new[key]}")

h_old, h_new = tables(OLD, OLD_DIR)[1], tables(NEW, OUT)[1]
both = h_old.index.intersection(h_new.index)
moved = [(m, h_old[m], h_new[m]) for m in both if pd.notna(h_old[m]) and round(h_old[m], 1) != round(h_new[m], 1)]
print(f"\nheadline_numbers: {len(moved)} of {len(both)} rows move at one decimal; "
      f"only in {OLD}: {', '.join(h_old.index.difference(h_new.index)) or 'none'}; "
      f"only in {NEW}: {', '.join(h_new.index.difference(h_old.index)) or 'none'}")
