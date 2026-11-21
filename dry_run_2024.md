# 2024 dry run, November 21, 2026

Provisional: reported 2024 waste and material use, but Eurostat's estimated 2024 rate, 12.2%, and its November 2025 env_wassd. It moves again once the rate is recalculated on reported waste. Never on the page. Used at step 7 (the rebase to 2024) to compare against.

## Inputs

- env_wastrt 2024: reported (Greece provisional, Denmark a break in series).
- env_ac_mfa 2024: reported.
- env_ac_cur and env_wassd 2024: still estimates.
- env_ac_rmefd: 2024 only as an EU total, so the footprint table uses 2023.

## Findings that change

- At 0:1, recycling alone closes the ring (every tonne reaches 24.7%; it closes at 96.2% recycled). This breaks panel 4's second card and the Method table's "never closes".
- The ring is 50.8% closed, so card 2's "less than halfway" fails.
- Germany's cut at 70% falls to 19.2% (4.1% replaced, 15.2% gone without, its rate at 70% 21.0%), after its 14% fall in use.
- The Netherlands has the EU's second most fossil mix, not the most, and exports 59.5%.
- Waste traded for recycling no longer nets out (35.7 Mt out, 46.7 Mt in).

## Moving but holding

- The floor, 7.6%. Recycling alone closes at 88.8%, 2.1 times the base year's recycling. Using less alone, 56.0%.
- At 70%, 27.1% less (4.6% replaced, 22.5% gone without).
- The rate needing to climb 2.0% of material used a year. Waste back, 33% of material consumed.
- 13.3 t a person, 36 kg a day, 7.5 t to cut.
- 3.4% of climate impact (97 Mt) when recycling closes the ring.
- 7 countries past 24% at 70% (Luxembourg drops out). Over 80% cut: Lithuania and Portugal.
- 17 flagged splits (France, Hungary and Romania in, Luxembourg out).
- The waterfall doesn't move.

## Romania

Romania has no 2024 waste. Decided November 21: it defaults to its last reported year, 2022, stated in its card and the notes. Build that at step 7 only if Romania still hasn't reported, moving every Romania input (mix, `not_recycled_mix`, per-material split, tonnes per person) to 2022 together, with a `data_year` field the card and notes read. Counting Romania on 2022, the explorers' title reads 20 of 27 on the dry run's figures.

## 20b: recheck after Eurostat's update

These rest on the 2024 estimate: Belgium's second highlight and last sentence; Germany; Latvia's second highlight; the Netherlands' second highlight, last sentence and lead-in line; Finland's estimate line; Hungary (no 2024 text until then); Sweden's last sentence.
