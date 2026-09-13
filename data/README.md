# Data

## Source records

`yangcheng_lake_center_station_3187.csv` holds the complete record set analysed in the paper:
8517 rows of automatic-monitoring data from the Yangcheng Lake Center Monitoring Station
(station 3187), covering 17 December 2020 to 5 January 2026.

The file was retrieved from the MoonAPI open-data platform, which aggregates and republishes
automatic-monitoring records from China's national surface-water monitoring network:

    https://moonapi.com/WaterQuality/station/history/id/3187.html   (retrieved 15 July 2026)

The file here is byte-identical to the retrieved original; only the filename was changed from
its original Chinese form to an ASCII name. Integrity can be checked with:

    SHA-256  3b9e2ab7a2d6ef0c2f9cd0209fca41656c8cb0d75482a9fd0a7c69107f924642
    MD5      1162cf2a503404b8d615f1f19b0a809b
    Size     1,656,680 bytes

The underlying measurements are produced by China's national surface-water monitoring
programme. They are redistributed here to make the analysis reproducible; the MIT licence in
this repository covers the code only, not these records.

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
