# Data

## Source records

The analysis uses one source file, which is **not redistributed in the GitHub repository**:

`data/yangcheng_lake_center_station_3187.csv`

It contains **8516 monitoring records** from the Yangcheng Lake Center Monitoring Station (station 3187), covering 17 December 2020 to 5 January 2026. The CSV contains a field-name row and a units row. The file was retrieved through the MoonAPI station-history page on 15 July 2026:

`https://moonapi.com/WaterQuality/station/history/id/3187.html`

The authors do not redistribute or relicense the third-party source records. Obtain the file from the source and save it at the path above before running the analysis.

## Identity of the analyzed file

The attached source CSV supplied for the final package matches these properties:

- SHA-256: `3b9e2ab7a2d6ef0c2f9cd0209fca41656c8cb0d75482a9fd0a7c69107f924642`
- MD5: `1162cf2a503404b8d615f1f19b0a809b`
- Size: `1,656,680 bytes`
- Records: `8516` monitoring records plus the units/header structure used by the scripts

Use:

```bash
python src/verify_source.py
```

to check a local copy.

## Column dictionary

| Column | Meaning |
| --- | --- |
| `监测时间` | monitoring timestamp |
| `水温` | water temperature (°C) |
| `pH` | pH |
| `溶解氧` | dissolved oxygen (mg/L) |
| `电导率` | electrical conductivity (µS/cm) |
| `浊度` | turbidity (NTU) |
| `高锰酸盐指数` | permanganate index (mg/L) |
| `氨氮` | ammonia nitrogen (mg/L) |
| `总磷` | total phosphorus (mg/L) |
| `总氮` | total nitrogen (mg/L) |
| `叶绿素α` | chlorophyll a |
| `藻密度` | algal density |
| `水质` | archived water-quality class (Ⅰ–劣Ⅴ, or UNKNOWN) |

The class field contains `UNKNOWN` in 343 records; those records are excluded, leaving the 8173-record analysis set.
