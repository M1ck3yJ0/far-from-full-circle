# 2024 dry run, November 24, 2026

Provisional: reported 2024 waste and material use, with Eurostat's imputed 2024 rate (12.2%) and its November 2025 env_wassd and env_ac_sd, all values imputed. Everything below moves again once the rate is recalculated on reported waste. Never on the page. Used at the rebase to compare against.

## Inputs, as of November 24

- env_ac_cur: last updated November 24, 2025; every 2024 rate imputed. Eurostat lists an update on December 1, 2026.
- env_wassd, env_ac_sd: last updated November 25, 2025; every value imputed.
- env_wastrt 2024: reported (Greece provisional, Denmark a break in series); Romania missing.
- env_ac_mfa 2024: reported for every country.
- env_ac_rmefd: 2024 only as an EU total, so the footprint table uses 2023.
- ETC CE 2025/3 is still the newest source for Figure 3-4's shares and F53's total (checked November 24): Reports 2026/1 and 2026/2 give neither. The tables stay on 2022 for both, and the build warns.

## Running the rebase

1. Milcah replaces the raw files that changed (`data/raw/README.md`).
2. Set `YEAR = 2024` and `DATA_AS_OF`, run `python build_data.py`, and read every warning.
3. `python3 -I compare_years.py 2022 2024`: every finding the page rests on, old against new.
4. Merge the build into the site's data file, keeping `center_shards` and `food_heaps`, then run `make_shards.py` and check the five discs by eye.
5. `check_numbers.py` on the page against the rebuilt repo: every figure it reports is a word to redraft. It accepts the trend table's rows for any year, so a sentence that names 2022 (about 100 on the page) still passes with 2022's figures: search the page for "2022" too.
6. In `check_numbers_by_hand.csv`, remove the entries for 2026: at 2024, years up to 2027 are read as times, so they go unused.

The rehearsal of steps 2 to 5, on November 24: the discs solve within 0.0001% of their shares; 93 figures fail against the 2024 tables (sections `sec-ring`, `notes-method`, `notes-ring`, `notes-closer`, `notes-explore`, `notes-game`, the hero and the closer's captions), besides the sentences naming 2022.

## Findings that change

- At 0:1, recycling alone closes the ring: every tonne reaches 24.7%, and it closes at 96.2% recycled. This breaks the reveal's 0:1 line and the Method table's "never closes".
- The ring is 50.8% closed, so "less than halfway" fails.
- Countries that would still have to use less at 70% recycled: 20 of 27 at 0.5:1 and at 0:1, 19 at 1:1 (2022: 19, 19 and 23). "Holds at 0.5:1 and 1:1" fails: Slovenia passes at 1:1 only (23.9% at 0.5:1).
- Past 24% at 70%, at 0.5:1: Austria, Bulgaria, Estonia, Finland, Malta, the Netherlands and Sweden (Luxembourg drops out, at 21.3%). At 0:1, all seven pass, so the "four pass even at 0:1" line changes.
- Soil and rock lines: Austria (19.5%, soil and rock 60% of treated), Bulgaria (8.6%, 87%) and Finland (4.7%, 90%); Luxembourg drops out. Sweden now publishes its treated soil and rock (89.3%) but not what it recycles of it, so its line still can't be drawn, for a different reason.
- Germany at 70%: 19.2% less (4.1% replaced, 15.2% not replaced), its rate 21.0%, after a 14% fall in use.
- Ireland: rate 2.0%; every tonne recycled 9.5%, 9.9% and 10.3%; at 70% recycled, 76.4% less for 24% and 45.3% for its own 12%. See the data quality note below before using any of them.
- Over 80% cut at 70%: Lithuania and Portugal (Latvia drops out).
- 16 flagged splits: France and Hungary in, Luxembourg out.
- The Netherlands has the EU's second most fossil mix, not the most, and exports 59.5%.
- Waste traded for recycling no longer nets out (35.7 Mt out, 46.7 Mt in).
- 79 of 178 rows in `headline_numbers` move at one decimal.

## Moving but holding

- Recycling alone at 0.5:1 closes at 88.8% recycled, 2.1 times the base year's, 7.6% less new material. Using less alone, 56.0%.
- At 70%, 27.1% less (4.6% replaced, 22.5% not replaced).
- Waste back, 32.7% of material consumed. 13.3 t a person.
- 3.4% of climate impact when recycling closes the ring.
- The waterfall's figures don't move, but its last step stops being an estimate; the chart's marks follow the data, the words ("an estimated 12.2%") don't.

## Data quality to settle at the rebase

- Ireland reports 0 t of other mineral waste (W12B) for 2024, against 2.7 Mt in 2022 and 2.8 to 3.3 Mt in 2018 and 2020, while its soils (W126) recycled jump from 4 kt to 297 kt. That reads as a reporting change, not a real one: it cuts Ireland's soil and rock share from 69.9% to 50.9% and its every-tonne ceiling by about a tenth. Check it against Ireland's EPA before the closer's figures move.
- Denmark's break in series cuts its soil and rock share from 45.6% to 23.4%; its card and highlight need the flag.
- Greece's 2024 waste is provisional.

## Romania

Romania has no 2024 waste. `build_data.py` (November 24) now moves any such country to its latest year with rate, consumption and waste all reported, every input together, and records it in the ceilings table's `data_year` and the page data's `data_year`; the ring explorer's card, key and source line read it and add one sentence saying so. At 2022 it changes nothing. Romania on 2022 gives the explorers' title 20 of 27. The ring explorer's note still needs a sentence on it.

## Recheck after Eurostat's update

These rest on the 2024 estimate: Belgium's second highlight and last sentence; Germany; Latvia's second highlight; the Netherlands' second highlight, last sentence and lead-in line; Finland's estimate line; Hungary (no 2024 text until then); Sweden's last sentence. The warning lines that say "2022 may not be a typical year" (Estonia, Finland, Bulgaria) and Sweden's (its doubling and its 10.4% in 2024) change with the year.
