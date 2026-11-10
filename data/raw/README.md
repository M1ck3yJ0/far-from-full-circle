# Raw data

Eurostat's full downloads come to about 335 MB, too large to store here. To rebuild the tables in `data/processed`, download each dataset below from Eurostat's data browser as a full dataset in SDMX-CSV 2.0 format, with codes and labels, and save it in this folder under the name shown.

| Dataset | Save as |
|---|---|
| [Circular material use rate (env_ac_cur)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_cur/default/table?lang=en) | `env_ac_cur_linear_2_0.csv` |
| [Material flow accounts (env_ac_mfa)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_mfa/default/table?lang=en) | `env_ac_mfa_linear_2_0.csv` |
| [Treatment of waste by waste category (env_wastrt)](https://ec.europa.eu/eurostat/databrowser/view/env_wastrt/default/table?lang=en) | `env_wastrt_linear_2_0.csv` |

The processed tables were built from the versions Eurostat last updated on November 24, 2025 (env_ac_cur), July 2, 2026 (env_ac_mfa) and October 28, 2026 (env_wastrt). Eurostat revises these datasets, so a newer download may give slightly different numbers.
