# Audit before automation: Yangcheng Lake water-quality classification

Code, environment, and data-provenance materials accompanying:

> Tang K, Meng X, Zheng Y. *Audit before automation: a rule-benchmarked protocol for machine learning in threshold-based water-quality classification, with evidence from Yangcheng Lake, China.* Manuscript (2026).

## Study in brief

Water-quality status is often assigned by a worst-indicator ("one-out, all-out") rule. When a machine-learning classifier is trained on archived regulatory classes using the same concurrent measurements that contribute to those classes, high accuracy can partly reflect recovery of the regulatory rule rather than independent predictive information. The manuscript evaluates this issue using an audit-before-automation framework and a Yangcheng Lake monitoring archive.

## Headline results

| Quantity | Value |
| --- | ---: |
| Records retrieved / analyzed | 8516 / 8173 |
| Four-indicator rule (R4), exact agreement | 92.02% (audit set: 652 records) |
| R4 plus pH constraint on observed pH (R5) | 93.55% |
| Audit-set mechanisms: pH excursions / reporting precision / invalid rule-indicator values / near-limit TP | 233 / 198 / 80 / 77 records; 64 unexplained |
| Archived Below Class V records with observed pH outside 6–9 | 233 of 274 |
| Random forest (TP, CODMn, pH), held-out accuracy | 95.96% vs 92.05% for R4 on the same records |
| Rule-benchmarked skill score SSR4 / SSR5 | 0.49 / 0.36 |
| Worst-grade ties | 2021 records (24.7%); August 58.5% |
| August TP attribution: equal credit / range across 24 forced priority orders | 62.2% / 33.1–91.6% |
| Forward accuracy, model trained on 2021–2023: 2024 → 2025 | 96.66% → 88.71% |
| R4 agreement in the same years | 92.82% → 97.85% |

## Reproducibility environment

The manuscript analyses were verified with:

- Python 3.13
- pandas 2.2.3
- NumPy 2.3.5
- scikit-learn 1.8.0
- SciPy 1.18.1
- Matplotlib 3.10.8

These exact package versions are listed in the root `requirements.txt`.

Random-forest results use fixed seeds (42 for the primary split and forests; 0–49 for repeated splits). Deterministic quantities such as rule reconstruction and tie structure do not depend on random seeds.

## Data provenance

The analysis uses 8516 monitoring records retrieved on 15 July 2026 through the MoonAPI station-history page for the Yangcheng Lake Center Monitoring Station (station 3187), covering 17 December 2020 to 5 January 2026. The third-party source records are not redistributed in this repository.

Source page:

`https://moonapi.com/WaterQuality/station/history/id/3187.html`

Analyzed-file SHA-256:

`3b9e2ab7a2d6ef0c2f9cd0209fca41656c8cb0d75482a9fd0a7c69107f924642`

Detailed retrieval notes, file metadata, checksums, and the column dictionary are provided in `data/README.md`.

## Repository contents relevant to the manuscript

- `requirements.txt` — exact Python package versions used for the reported analyses
- `data/README.md` — source URL, retrieval date, file metadata, checksums, and column dictionary
- `src/reproduce_analysis.py` — core reconstruction, binding, random-forest, repeated-split, and sensitivity analyses
- `src/make_figures.py` — data-derived figure generation available in the repository

Figures 1 and 2 in the manuscript are author-drawn schematics. Final publication styling of data-derived figures may be applied separately from the analysis scripts.

## Data and code availability

The source monitoring records are third-party data and are not redistributed. A newly obtained file can be checked against the analyzed file using the provenance metadata in `data/README.md`.

Core analysis and figure-generation code is publicly available in this repository. The code is released under the MIT License; that license does not extend to the third-party monitoring records.

## Citation

Please cite the article once publication details are available. Until then, cite the manuscript title above when referring to this repository.

## Contact

Corresponding author: Xiaolu Meng (meng_xiaolu@126.com)
