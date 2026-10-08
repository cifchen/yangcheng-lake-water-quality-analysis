# Data

## Source records

The analysis uses one source file, which is **not redistributed in this repository**:

    data/yangcheng_lake_center_station_3187.csv

It contains **8516 monitoring records** from the Yangcheng Lake Center Monitoring Station (station 3187), covering 17 December 2020 to 5 January 2026. The CSV also contains two header rows: field names and units. The file was retrieved through the MoonAPI station-history page on 15 July 2026:

    https://moonapi.com/WaterQuality/station/history/id/3187.html

The authors do not redistribute or relicense the third-party source records. Obtain a fresh copy from the source page and save it at the path above before running the analysis.

## Verifying the analyzed file

The file used for the manuscript has these properties:

    SHA-256  3b9e2ab7a2d6ef0c2f9cd0209fca41656c8cb0d75482a9fd0a7c69107f924642
    MD5      1162cf2a503404b8d615f1f19b0a809b
    Size     1,656,680 bytes
    Records  8516 monitoring records plus a two-row header

A dynamically served source page may not be retrievable by every automated audit client. Reproducibility therefore relies on the fixed station-history URL, retrieval date, file size, cryptographic checksums, and column dictionary in addition to a fresh source export.

On Linux or macOS, the SHA-256 checksum can be checked with:

```bash
shasum -a 256 data/yangcheng_lake_center_station_3187.csv
```

## File layout

The CSV has a two-row header: row 1 holds field names and row 2 holds units. Analysis scripts skip the units row. Relevant columns are:

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
| `水质` | archived water-quality class (Ⅰ–劣Ⅴ, or `UNKNOWN`) |

The class field contains `UNKNOWN` in 343 records. Those records are excluded, leaving the **8173-record analysis set**.

## Important provenance note

The monitoring archive is treated as a third-party automatic-monitoring archive rather than as the official annual assessment dataset. The manuscript separately discusses differences between the automatic archive and official assessment values and procedures. The station-history URL, retrieval date, file metadata, and checksums above identify the exact source file used for the reported analyses.
