# Audit before automation: Yangcheng Lake water-quality classification

Code and reproducibility materials for:

> Tang K, Meng X, Zheng Y. *Audit before automation: a rule-benchmarked protocol for machine learning in threshold-based water-quality classification, with evidence from Yangcheng Lake, China.* Manuscript (2026).

## Purpose

Water-quality status can be assigned by a worst-indicator (“one-out, all-out”) rule. A classifier trained on the same concurrent measurements may therefore partly recover the regulatory rule rather than provide independent predictive skill. The repository implements four diagnostics:

| Diagnostic | Main question | Script |
| --- | --- | --- |
| D1 Rule recovery | How much of the archived classification does the regulatory rule reproduce, and why do residual disagreements occur? | `src/reproduce_analysis.py`, `src/audit_diagnostics.py` |
| D2 Rule-benchmarked skill | How much of the rule’s residual error does the model resolve? | `src/audit_diagnostics.py` |
| D3 Order-invariant attribution | Which indicators set the class when several indicators tie at the worst grade? | `src/reproduce_analysis.py`, `src/audit_diagnostics.py` |
| D4 Reliability by class and time | Are rare classes and later years handled reliably? | `src/reproduce_analysis.py`, `src/audit_diagnostics.py` |

## Headline results

| Quantity | Value |
| --- | ---: |
| Records retrieved / analysed | 8516 / 8173 |
| Four-indicator rule (R4), exact agreement | 92.02% |
| R4 plus pH constraint on observed pH (R5) | 93.55% |
| Random forest (TP, CODMn, pH), held-out accuracy | 95.96% |
| Worst-grade ties | 2021 records (24.7%) |
| August tie share | 58.5% |
| Forward accuracy, 2024 → 2025 | 96.66% → 88.71% |

## Quick start

```bash
git clone https://github.com/cifchen/yangcheng-lake-water-quality-analysis.git
cd yangcheng-lake-water-quality-analysis
python -m venv .venv
pip install -r requirements.txt

# Obtain the source CSV separately (see data/README.md) and save it as:
# data/yangcheng_lake_center_station_3187.csv

python src/verify_source.py
python src/reproduce_analysis.py
python src/audit_diagnostics.py
python src/make_figures.py

# Optional: rerun the full 180-combination grid search
python src/tune_random_forest.py
```

The scripts accept `--csv` and, where applicable, `--outdir`. Generated outputs are written locally and are excluded by `.gitignore`.

## Repository layout

```text
README.md
requirements.txt
.gitignore
LICENSE
CITATION.cff
run_all.py
data/
  README.md
src/
  reproduce_analysis.py
  audit_diagnostics.py
  verify_source.py
  tune_random_forest.py
  make_figures.py
psy_copies/
  reproduce_analysis.psy
  audit_diagnostics.psy
  verify_source.psy
  tune_random_forest.psy
  make_figures.psy
```

`*.py` files are the canonical executable Python scripts. The `*.psy` files are byte-equivalent text copies included only because they were requested; `.psy` is not the standard Python module extension and should not replace the `.py` files in normal execution.

## Reproducibility environment

The final validated environment file pins:

- Python 3.13
- pandas 2.2.3
- NumPy 2.3.5
- scikit-learn 1.8.0
- SciPy 1.17.0
- Matplotlib 3.10.8

Random-forest procedures use fixed seeds (42 for the primary split/forests and 0–49 for repeated splits).

## Source data

The monitoring records were retrieved through the MoonAPI open-data platform. The raw third-party CSV is not redistributed in the GitHub upload package. See `data/README.md` for the fixed station-history URL, retrieval metadata, checksums, and column dictionary.

## Citation and license

No GitHub release number, Zenodo DOI, or repository DOI is claimed in this package. Add one only after an actual archived release/DOI exists.

Code is released under the MIT License. The license covers the code only and does not extend to third-party monitoring records obtained separately from MoonAPI.

## Contact

Corresponding author: Xiaolu Meng (meng_xiaolu@126.com)
