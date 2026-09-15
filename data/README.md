# Data

## Source records

The analysis uses one file, which is **not redistributed in this repository**:

    data/yangcheng_lake_center_station_3187.csv

It holds 8517 rows of automatic-monitoring data from the Yangcheng Lake Center Monitoring
Station (station 3187), covering 17 December 2020 to 5 January 2026, and was retrieved from
the MoonAPI open-data platform, which aggregates and republishes automatic-monitoring records
from China's national surface-water monitoring network:

    https://moonapi.com/WaterQuality/station/history/id/3187.html   (retrieved 15 July 2026)

Reuse of those records is governed by the platform's access and reuse conditions, which the
authors do not relicense. Obtain your own copy from MoonAPI and save it at the path above;
both scripts then run without further configuration.

## Verifying that you have the same file

The file used for the published results has these properties. Checking them confirms that a
freshly downloaded copy is byte-identical to the one analysed in the paper.

    SHA-256  3b9e2ab7a2d6ef0c2f9cd0209fca41656c8cb0d75482a9fd0a7c69107f924642
    MD5      1162cf2a503404b8d615f1f19b0a809b
    Size     1,656,680 bytes
    Rows     8517 data rows plus a two-row header

On Linux or macOS:

    shasum -a 256 data/yangcheng_lake_center_station_3187.csv

## File layout

The CSV has a two-row header: row 1 holds the field names and row 2 holds units. Both scripts
skip row 2. Relevant columns:

| Column | Meaning |
| --- | --- |
| `监测时间` | monitoring timestamp |
| `水温` | water temperature (°C) |
| `pH` | pH (dimensionless) |
| `溶解氧` | dissolved oxygen (mg/L) |
| `电导率` | electrical conductivity (µS/cm) |
| `浊度` | turbidity (NTU) |
| `高锰酸盐指数` | permanganate index (mg/L) |
| `氨氮` | ammonia nitrogen (mg/L) |
| `总磷` | total phosphorus (mg/L) |
| `总氮` | total nitrogen (mg/L) |
| `叶绿素α` | chlorophyll a (mg/L) |
| `藻密度` | algal density (cells/L) |
| `水质` | archived water-quality class (Ⅰ–劣Ⅴ, or UNKNOWN) |

Invalid or absent measurements appear as empty fields. The class field carries `UNKNOWN` in
343 records; those records are dropped, leaving the 8173-record analysis set.

## Derived data

`outputs/analysis_set.csv` is written on the first run of `src/reproduce_analysis.py`. It is
the post-quality-control analysis set with the reconstructed grade, the tie count and the
binding-indicator attribution appended. It is git-ignored because it is fully regenerable
from the source file.
