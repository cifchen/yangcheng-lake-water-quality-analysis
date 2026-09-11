# Data

## Raw data

The raw record set (`江苏省_苏州市_太湖流域_阳澄湖_阳澄湖心_3187.csv`, 8516 rows) was retrieved
from the MoonAPI open-data platform, which aggregates and republishes automatic-monitoring
records from China's national surface-water monitoring network:

https://moonapi.com/WaterQuality/station/history/id/3187.html (accessed 15 July 2026)

**The raw file is not redistributed in this repository.** Its reuse is governed by the
platform's access conditions. Place your own copy in this directory before running the
analysis:

```
data/yangcheng_lake_center_station.csv
```

## File layout

The CSV has a two-row header: row 1 holds the field names, row 2 holds units. The analysis
script skips row 2. Relevant columns:

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

## Derived data

`outputs/analysis_set.csv` (8173 rows, produced by the script) is the post-quality-control
analysis set with the reconstructed grade and binding-indicator attribution appended. It is
git-ignored by default; enable sharing only after confirming that redistribution is
compatible with the source platform's terms.
