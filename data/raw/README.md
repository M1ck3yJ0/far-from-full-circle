# Raw data

Eurostat's full downloads, gzip-compressed. `build_data.py` reads them from here.

| Dataset | File | Eurostat's last update | Downloaded |
|---|---|---|---|
| [Circular material use rate (env_ac_cur)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_cur/default/table?lang=en) | `env_ac_cur_linear_2_0.csv.gz` | November 24, 2025 | October 24, 2026 |
| [Material flow accounts (env_ac_mfa)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_mfa/default/table?lang=en) | `env_ac_mfa_linear_2_0.csv.gz` | July 2, 2026 | October 24, 2026 |
| [Treatment of waste by waste category (env_wastrt)](https://ec.europa.eu/eurostat/databrowser/view/env_wastrt/default/table?lang=en) | `env_wastrt_linear_2_0.csv.gz` | October 28, 2026 | November 10, 2026 |
| [Material flows for circular economy, Sankey diagram data (env_ac_sd)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_sd/default/table?lang=en) | `env_ac_sd_linear_2_0.csv.gz` | November 25, 2025 | October 24, 2026 |
| [Management of waste by type of material, Sankey diagram data (env_wassd)](https://ec.europa.eu/eurostat/databrowser/view/env_wassd/default/table?lang=en) | `env_wassd_linear_2_0.csv.gz` | November 25, 2025 | October 24, 2026 |
| [Material footprints by final use of products (env_ac_rmefd)](https://ec.europa.eu/eurostat/databrowser/view/env_ac_rmefd/default/table?lang=en) | `env_ac_rmefd_linear_2_0.csv.gz` | July 21, 2026 | October 24, 2026 |
| [Generation of waste by waste category (env_wasgen)](https://ec.europa.eu/eurostat/databrowser/view/env_wasgen/default/table?lang=en) | `env_wasgen_linear_2_0.csv.gz` | October 28, 2026 | November 10, 2026 |

## Replacing a file with a newer release

1. In Eurostat's data browser, download the full dataset in SDMX-CSV 2.0 format, with codes and labels.
2. Name it as in the table, without `.gz`, and compress it: `gzip -9 env_ac_cur_linear_2_0.csv`
3. On GitHub, open `data/raw`, choose Add file, then Upload files, and upload the `.csv.gz` file. It replaces the old one.
4. Update its dates in the table above.
