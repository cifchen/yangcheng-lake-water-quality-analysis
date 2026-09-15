# Yangcheng Lake water-quality analysis

Code for:

> Tang, K.; Meng, X.; Zheng, Y. **Seasonal Shifts in Binding and Co-Binding Indicators of
> Regulatory Water-Quality Classification: Separating Rule Recovery from Ecological
> Inference at a National Monitoring Station in Yangcheng Lake, China.** Submitted to
> *Water* (MDPI), 2026.

## What this repository does

Machine-learning classifiers are often trained on regulatory water-quality classes that are
themselves assigned by comparing same-time measurements against fixed thresholds. When that
is the case, a high accuracy score may mostly reflect recovery of the classification rule
rather than any independent predictive skill.

This repository implements the evaluation sequence used in the paper:

1. **Rule reconstruction.** Grade dissolved oxygen, permanganate index, ammonia nitrogen and
   total phosphorus against GB 3838-2002 and take the worst of the four. This deterministic
   benchmark reproduces **92.02%** of the archived classes with no model fitting.
2. **Tie-aware binding attribution.** Record which indicator (or indicators) attained the
   worst grade. Ties are kept rather than resolved by an arbitrary priority rule, because
   forced resolution manufactures an apparent change in dominance that the data do not show.
3. **Feature ablation.** Quantify how much accuracy depends on the indicators that generate
   the rule.
4. **Forward temporal validation.** Fit on 2021–2023, test on 2024 and then 2025.

## Headline results reproduced by the script

| Quantity | Value |
| --- | --- |
| Records retrieved / analysed | 8516 / 8173 |
| Four-indicator reconstruction, exact agreement | 92.02% |
| Within one class | 96.72% |
| Tuned random forest, held-out accuracy | 95.96% (+3.91 pp over the rule) |
| Worst-grade ties | 2021 records (24.7%) |
| Total phosphorus–permanganate index ties | 1869 records (22.9%) |
| August: tied / TP–CODMn co-bound / uniquely TP-bound | 58.5% / 56.6% / 33.1% |
| Forward accuracy 2024 → 2025 | 96.66% → 88.71% |

## Quick start

```bash
git clone https://github.com/cifchen/yangcheng-lake-water-quality-analysis.git
cd yangcheng-lake-water-quality-analysis
pip install -r requirements.txt

# obtain the source CSV from MoonAPI and save it as
#   data/yangcheng_lake_center_station_3187.csv   (see data/README.md)

python src/reproduce_analysis.py    # all reported quantities, plus Tables 5, 6 and 8 as CSV
python src/make_figures.py          # Figures 3, 4 and 5 as 600 dpi PNG
```

Both scripts read that path by default, so no further configuration is needed once the file
is in place. `reproduce_analysis.py` prints every quantity cited in the manuscript and writes
`outputs/analysis_set.csv`; `make_figures.py` regenerates the three data-derived figures.
Figures 1 and 2 of the paper are a study-area schematic and a workflow diagram, which are
drawn rather than computed.

## Reproducibility notes

Everything deterministic (quality control, the four-indicator reconstruction, the tie
structure, and every cell of Table 5) reproduces exactly on any machine.

Random-forest figures depend on the scikit-learn version. The reported numbers were produced
with the versions pinned in `requirements.txt`; on newer releases the held-out accuracy
typically lands within about half a percentage point, and electrical conductivity sits close
enough to the 0.05 Gini screening threshold that it can fall on either side. Neither affects
any conclusion in the paper: the gap between the deterministic benchmark and the fitted model
stays small, and the forward-transfer decline stays large.

## Repository layout

```
data/README.md                                how to obtain the source records, plus checksums
                                              and the column dictionary
src/reproduce_analysis.py                     full pipeline; prints all reported quantities
src/make_figures.py                           regenerates Figures 3, 4 and 5
requirements.txt                              dependencies
outputs/                                      created on first run (git-ignored)
```

## Data

The source records were retrieved from the MoonAPI open-data platform, which aggregates and
republishes automatic-monitoring data from China's national surface-water monitoring network.
They are **not redistributed here**: their reuse is governed by the platform's access and
reuse conditions, which the authors do not relicense. `data/README.md` gives the retrieval
details, the checksums needed to confirm you have the identical file, and the column
dictionary.

## Licence

The code is released under the MIT Licence (`LICENSE`). That licence covers the code only and
does not extend to the monitoring records, which are obtained separately from MoonAPI under
that platform's terms.

## Contact

Corresponding author: Xiaolu Meng (meng_xiaolu@126.com)
