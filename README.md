# Far from Full Circle

The analysis behind [Far from Full Circle](https://milcahjoseph.com/projects/far_from_full_circle/a_circularity_story.html), by Milcah M. Joseph: what it would take for the EU to double its circularity rate, to 24% by 2030, and what that target really asks.

## The finding

The rate can rise in only two ways: recycle more, or use less new material. On Eurostat's data for 2022, neither gets the EU to 24% alone at any practical scale, and every route there takes less new material, even recycling almost all of its waste. So what Europe cuts matters more than the rate. The page has the numbers.

## How it works

- The rate is circular use over circular use plus domestic material consumption (Eurostat's env_ac_cur). Every calculation starts from the published rate.
- Recycling more is modeled as a rising share of the waste the EU treats, with waste held at 2022's tonnes. Using less takes the same share of every material, or whole material groups in a chosen order.
- Each extra recycled tonne is assumed to replace half a new tonne of the same material. That's an assumed midpoint, not an estimate, between replacing none (recycled tonnes adding to new ones) and replacing a whole tonne (an upper limit). `REPLACEMENT` in `build_data.py` sets it, and every table that depends on it gives all three cases.
- The main numbers use only figures Eurostat reports, never its estimates. The waterfall of what moved the rate, from 2004, may carry Eurostat's estimates for its latest steps, flagged.
- Climate impact by material is read from ETC CE Report 2025/3 (Figure 3-4).

## What it can't say

- The ceilings are bounds, not forecasts: they count every treated tonne as recyclable, contaminated soil and mine waste included.
- The rate is measured by weight, and weight isn't impact. The climate shares stop at the factory gate, so burning fuel isn't counted.
- Whether a recycled tonne replaces a new one is set by markets, and can be zero.
- The arithmetic is static: using less material today also means less waste later.

## Files

```
build_data.py          builds every table in data/processed; its settings set the year and the replacement
data/raw/              Eurostat downloads, gzip-compressed (see data/raw/README.md)
data/examples/         datapoints for the page's examples, with their sources
data/processed/        the tables the page uses; headline_numbers_2022.csv holds every card figure with its calculation
research.md            the research register: every published finding the page cites, with its source and check status
compare_years.py       lists what moves between two data years
dry_run_2024.md        a provisional run on 2024 data, never on the page
```

## Sources

- Eurostat, [circular material use rate (env_ac_cur)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_cur/default/table?lang=en), [material flow accounts (env_ac_mfa)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_mfa/default/table?lang=en), [treatment of waste (env_wastrt)](https://ec.europa.eu/eurostat/databrowser/view/env_wastrt/default/table?lang=en), [generation of waste (env_wasgen)](https://ec.europa.eu/eurostat/databrowser/view/env_wasgen/default/table?lang=en), [material flows for circular economy (env_ac_sd)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_sd/default/table?lang=en), [management of waste by type of material (env_wassd)](https://ec.europa.eu/eurostat/databrowser/view/env_wassd/default/table?lang=en) and [material footprints (env_ac_rmefd)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_rmefd/default/table?lang=en)
- Vercalsteren and others (2025), [Measuring environmental benefits of circular economy](https://www.eionet.europa.eu/etcs/etc-ce/products/etc-ce-report-2025-3-measuring-environmental-benefits-of-circular-economy), ETC CE Report 2025/3
- Every other source is in `research.md` and `data/examples/sources.csv`.

## Rebuild

```
pip install -r requirements.txt
python build_data.py
```
