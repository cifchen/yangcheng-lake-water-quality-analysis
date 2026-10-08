# Audit before automation: Yangcheng Lake water-quality classification

Code and reproducibility materials for:

> Tang K, Meng X, Zheng Y. *Audit before automation: a rule-benchmarked protocol for machine
> learning in threshold-based water-quality classification, with evidence from Yangcheng
> Lake, China.* Manuscript (2026).

## What this repository does

Water-quality status is often assigned by a worst-indicator ("one-out, all-out") rule:
each regulated indicator is graded against fixed thresholds and the poorest grade sets the
class. A classifier trained on such classes, using the same concurrent measurements as
inputs, is partly rediscovering the rule, so its accuracy says little on its own. The revised
manuscript uses an audit-before-automation protocol with four diagnostics:

| Diagnostic | Question | Required implementation |
| --- | --- | --- |
| D1 Rule recovery | How much of the archived classification does the regulatory rule reproduce, and why do the remaining records disagree? | Core reconstruction plus audit-set diagnostics |
| D2 Rule-benchmarked skill | What share of the rule's residual errors does a model resolve (SS<sub>R</sub> = 1 − E<sub>model</sub>/E<sub>rule</sub>, exact McNemar test)? | Rule/model paired comparison |
| D3 Order-invariant attribution | Which indicators set the class when several tie at the worst grade? Equal-credit (Shapley) shares versus forced priority orders | Tie-aware and equal-credit attribution |
| D4 Reliability by class and time | Are rare classes and later years handled reliably, and is a decline due to the model or to how labels were generated? | Repeated splits and rule-benchmarked temporal validation |

## Headline results

| Quantity | Value |
| --- | ---: |
| Records retrieved / analyzed | 8516 / 8173 |
| Four-indicator rule (R4), exact agreement | 92.02% (audit set 652 records) |
| R4 plus pH constraint on observed pH (R5) | 93.55% |
| Audit set explained by pH excursions / reporting precision / invalid indicator values / near-limit TP | 233 / 198 / 80 / 77 records; 64 unexplained |
| Archived Below Class V records with pH outside 6–9 | 233 of 274 |
| Random forest (TP, COD<sub>Mn</sub>, pH), held-out accuracy | 95.96% vs 92.05% for R4 on the same records |
| Rule-benchmarked skill score SS<sub>R4</sub> / SS<sub>R5</sub> | 0.49 / 0.36 |
| Worst-grade ties | 2021 records (24.7%); August 58.5% |
| August share credited to TP: equal credit / range over 24 priority orders | 62.2% / 33.1–91.6% |
| Forward accuracy, model trained 2021–2023: 2024 → 2025 | 96.66% → 88.71% |
| R4 agreement in the same years | 92.82% → 97.85% |

## Reproducibility environment

The manuscript was verified with Python 3.13, pandas 2.2.3, NumPy 2.3.5,
scikit-learn 1.8.0, SciPy 1.18.1, and Matplotlib 3.10.8. For a public archival
release, `requirements.txt` should pin these exact package versions.

Random-forest results use fixed seeds (42 for the primary split and forests; 0–49 for repeated
splits). Deterministic results (quality control, rule reconstruction, tie structure, attribution,
and audit decomposition) do not depend on random seeds.

## Data provenance

The analysis uses 8516 monitoring records retrieved on 15 July 2026 through the MoonAPI
station-history page for the Yangcheng Lake Center Monitoring Station (station 3187), covering
17 December 2020 to 5 January 2026. The source data are third-party records and are not
redistributed here.

Source page:

`https://moonapi.com/WaterQuality/station/history/id/3187.html`

Analyzed-file SHA-256:

`3b9e2ab7a2d6ef0c2f9cd0209fca41656c8cb0d75482a9fd0a7c69107f924642`

The repository should provide the retrieval notes, column dictionary, and content-verification
instructions needed to compare a newly retrieved copy with the analyzed file.

## Figures

Figures 1 (protocol) and 2 (study-area schematic) are author-drawn. Data-derived figures should
be regenerated from the analysis scripts, with final publication styling applied separately.

## Citation and licence

Please cite the article once publication details are available. The code is released under the
MIT License. The license covers the code only and does not extend to third-party monitoring
records obtained separately from MoonAPI.

## Contact

Corresponding author: Xiaolu Meng (meng_xiaolu@126.com)
