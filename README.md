# Far from Full Circle

*How far could recycling take every EU country's circularity rate? Eurostat data for 2022, with a trend from 2010.*

The analysis behind [Far from Full Circle](https://milcahjoseph.com/projects/eu_circularity/far_from_full_circle.html), by Milcah M. Joseph.

## Bottom line

Most of what Europe uses never comes back as waste. Of every 100 tonnes of material moving through its economy in 2022, 40 were built into buildings, roads and machines, 29 were burned or eaten, 8 were exported and 3 were spread on land. Only 20 came back as waste, and more than half of that was soil and rock.

The EU wants to double the share of its materials that comes from recycled waste, to 24% by 2030. In 2022 it was 11.4%. Had Europe recycled every tonne of waste it treated that year, soil and mining rock included, its rate would have reached 23.7%: about the target, and no further. Leave out the soil and rock, and it reaches 15.4%. Latvia, Lithuania, Portugal, Croatia and Ireland would have stayed below 12% even recycling everything.

The trend points the same way. From 2012 to 2022 the rate rose only 0.4 points. Europe recycled 8% more waste, but it also consumed 3% more material and treated 7% less waste, so the most recycling could deliver fell from 25.5% to 23.7%.

Recycling alone can't close the gap. Using less material can, and that lever has no ceiling.

## The question

Eurostat's circular material use rate measures the share of the material an economy uses that comes from recycled waste. It can rise in only two ways: recycle more of the waste that comes back, or use less material. This analysis asks how far the first one could go, for the EU and each of its 27 countries, by setting a ceiling on the rate: the rate each country would have had if it had recycled every tonne of waste it treated.

## Method

The rate is U / (U + DMC), where DMC is domestic material consumption and U is circular use: waste recycled at home, adjusted for waste traded for recycling. Recycling here means recovery operations R2 to R11; energy recovery and backfilling don't count.

The published rate doesn't rebuild exactly from Eurostat's component tables, so every calculation starts from the published rate, r:

- Circular use implied by the rate: U = r / (1 - r) × DMC.
- Ceiling, recycling every treated tonne with consumption unchanged: (U + treated - recycled) / (U + treated - recycled + DMC).
- Ceiling if each recycled tonne replaced a tonne of new material, so U + DMC stays the same: (U + treated - recycled) / (U + DMC).
- Ceiling without soil and rock: as above, adding only the waste that isn't soils, dredging spoils or other mineral waste (codes W126, W127 and W12B). Where a country keeps part of that confidential, the sum is derived from Eurostat's totals.
- Rate with backfilling counted as recycling: (U + backfilled) / (U + backfilled + DMC).
- Consumption needed for a target t, holding recycling fixed: DMC falls to U × (1 - t) / t.
- What moved the rate between two years: the recycling effect is U₂ / (U₂ + DMC₁) - r₁, and the consumption effect is U₁ / (U₁ + DMC₂) - r₁.

Waste is reported every two years, so the trend uses the even years from 2010 to 2024.

The other tables:

- The loop follows Eurostat's Sankey data. Processed material (extracted at home, imported, recycled or backfilled) is split into material built into stock, emissions (burned or eaten), exports, dissipative flows (spread on land) and waste treated. Shares are rounded to whole tonnes out of 100 by largest remainder. The soil and rock part of the waste is approximate: each country's soil and rock share of all its treated waste, applied to the waste in the flows.
- The footprint is the EU's raw material consumption by product, with Eurostat's 63 product groups gathered into seven. Investment is gross capital formation, households buying new homes included. Spending is what households, governments and non-profits buy and use up.
- Weight against climate impact is read from Figure 3-4 of ETC CE Report 2025/3. The climate impact covers producing the materials, up to the factory gate, so burning fuel isn't included.

## What the numbers can't say

- The ceilings are bounds, not forecasts. They count every treated tonne as recyclable, contaminated soil and mining waste included, so real limits are lower. Mining waste lifts the ceilings of Finland, Bulgaria, Romania and Sweden.
- They count only waste treated at home, so waste a country exports for energy recovery or disposal is left out.
- The consumption figures are static arithmetic. In reality, using less material also means less waste later.
- 2024 values are Eurostat estimates, flagged in `trend.csv`, until reported data replaces them.
- In the loop, Malta's flows record no emissions and leave about a fifth of its material unaccounted for.

## Data

Built by `build_data.py` into `data/processed`:

| File | What it holds |
|---|---|
| `ceilings_2022.csv` | For the EU and each country in 2022: the published rate, consumption, waste treated, recycled and backfilled, soil and rock, every ceiling, and the consumption cut each target would need |
| `trend.csv` | The same measures in every waste reporting year from 2010 to 2024, with Eurostat's flags |
| `trend_drivers.csv` | The change in each rate from 2012 to 2022, split into a recycling effect and a consumption effect |
| `materials_2022.csv` | What each country consumed in 2022, in kg per person a day, by material group |
| `loop_2022.csv` | Where each country's processed material went in 2022, in tonnes and out of every 100 tonnes |
| `footprint_2022.csv` | What the EU's material footprint ended up as in 2022, and how much of each group was investment or spending |
| `weight_vs_climate_2022.csv` | Each material group's share of EU material use in 2022 by weight and by climate impact |
| `far_from_full_circle_data.js` | Everything the web page draws, rounded for display, in one file the page loads |

Weights are in thousand tonnes (kt) and shares in percent.

## Repository structure

```
build_data.py       builds every table in data/processed from the raw downloads
data/raw/           Eurostat downloads, gzip-compressed (see data/raw/README.md)
data/processed/     the tables the page uses
requirements.txt
```

## Reproducing the data

The Eurostat downloads are stored in `data/raw`. [data/raw/README.md](data/raw/README.md) lists their versions and how to replace one with a newer release.

1. Install the requirements: `pip install -r requirements.txt`
2. From the repository root, run `python build_data.py`

## Sources

- Eurostat, [circular material use rate (env_ac_cur)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_cur/default/table?lang=en) and its [metadata](https://ec.europa.eu/eurostat/cache/metadata/EN/env_ac_cur_esms.htm)
- Eurostat, [material flow accounts (env_ac_mfa)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_mfa/default/table?lang=en)
- Eurostat, [treatment of waste by waste category (env_wastrt)](https://ec.europa.eu/eurostat/databrowser/view/env_wastrt/default/table?lang=en)
- Eurostat, [material flows for circular economy (env_ac_sd)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_sd/default/table?lang=en) and [management of waste by type of material (env_wassd)](https://ec.europa.eu/eurostat/databrowser/view/env_wassd/default/table?lang=en)
- Eurostat, [material footprints by final use of products (env_ac_rmefd)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_rmefd/default/table?lang=en)
- Vercalsteren and others (2025), [Measuring environmental benefits of circular economy](https://www.eionet.europa.eu/etcs/etc-ce/products/etc-ce-report-2025-3-measuring-environmental-benefits-of-circular-economy), ETC CE Report 2025/3
- European Commission, [Clean Industrial Deal](https://commission.europa.eu/topics/competitiveness/clean-industrial-deal_en), which sets the EU's 24% goal for 2030
- Government of Ireland, [Whole of Government Circular Economy Strategy 2026-2028](https://www.gov.ie/en/department-of-climate-energy-and-the-environment/publications/whole-of-government-circular-economy-strategy-2026-2028-accelerating-action/), which sets Ireland's 12% goal for 2030
