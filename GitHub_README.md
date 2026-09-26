# Yangcheng Lake water-quality analysis

Code and reproducibility materials for:

> Tang, K.; Meng, X.; Zheng, Y. Seasonal binding and co-binding in regulatory water-quality classification: Separating rule recovery from ecological inference at Yangcheng Lake, China. Manuscript (2026).

## What this repository does

Machine-learning classifiers are often trained on regulatory water-quality classes that are themselves assigned by comparing same-time measurements against fixed thresholds. When that is the case, a high accuracy score may mostly reflect recovery of the classification rule rather than independent predictive skill.

This repository implements the evaluation sequence used in the manuscript:

1. **Rule reconstruction.** Grade dissolved oxygen, permanganate index, ammonia nitrogen, and total phosphorus against GB 3838-2002 and take the worst of the four. This deterministic benchmark reproduces 92.02% of the archived classes with no model fitting.
2. **Tie-aware binding attribution.** Record which indicator or indicators attained the worst grade. Ties are retained rather than resolved by an arbitrary priority rule.
3. **Feature ablation.** Quantify how much accuracy depends on the indicators that generate the rule.
4. **Forward temporal validation.** Fit on 2021–2023 and test on 2024 and 2025 without refitting.

## Headline results reproduced by the scripts

| Quantity | Value |
|---|---:|
| Records retrieved / analyzed | 8516 / 8173 |
| Four-indicator reconstruction, exact agreement | 92.02% |
| Agreement within one class | 96.72% |
| Tuned random forest, held-out accuracy | 95.96% (+3.91 pp over the rule) |
| Worst-grade ties | 2021 records (24.7%) |
| Total phosphorus–permanganate index ties | 1869 records (22.9%) |
| August: tied / TP–CODMn co-bound / uniquely TP-bound | 58.5% / 56.6% / 33.1% |
| Forward accuracy, 2024 → 2025 | 96.66% → 88.71% |

## Quick start

```bash
git clone https://github.com/cifchen/yangcheng-lake-water-quality-analysis.git
cd yangcheng-lake-water-quality-analysis
pip install -r requirements.txt

# Obtain the source CSV from MoonAPI and save it as:
# data/yangcheng_lake_center_station_3187.csv
# See data/README.md for retrieval details and checksums.

python src/reproduce_analysis.py
python src/make_figures.py
```

`reproduce_analysis.py` prints the reported analytical quantities and writes the analysis output files. `make_figures.py` regenerates the data-derived figures. Figures 1 and 2 of the manuscript are a study-area schematic and an analytical workflow diagram rather than computed plots.

## Reproducibility notes

The deterministic steps (quality control, four-indicator reconstruction, tie structure, and Table 5) are designed to reproduce exactly when the same source file and pinned dependencies are used. Random-forest results can vary slightly across scikit-learn versions; use the versions in `requirements.txt` to reproduce the manuscript results.

## Repository layout

```text
data/README.md               retrieval instructions, checksums, column dictionary
src/reproduce_analysis.py    analysis pipeline and reported quantities
src/make_figures.py          regenerates Figures 3–5
requirements.txt             pinned dependencies
outputs/                     generated locally (git-ignored)
```

## Data

The source records were retrieved from the MoonAPI open-data platform, which aggregates and republishes automatic-monitoring data from China's national surface-water monitoring network. They are not redistributed here because reuse is governed by the platform's access and reuse conditions. `data/README.md` provides retrieval details, checksums, and the column dictionary.

## License

The code is released under the MIT License (`LICENSE`). The license covers the code only and does not extend to the monitoring records obtained separately from MoonAPI.

## Contact

Corresponding author: Xiaolu Meng (meng_xiaolu@126.com)
