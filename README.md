# CAS Injury Severity Analysis

[![DOI](https://zenodo.org/badge/DOI/PENDING.svg)](https://doi.org/PENDING)

Author: Roshan Aryal ([ORCID 0009-0001-4758-4977](https://orcid.org/0009-0001-4758-4977))
Otago Polytechnic Auckland International Campus

Reproducible pipeline for the SSD 2026 submission: association between light
condition, weather and injury severity in New Zealand road crashes, 2010-2024.

## Data

NZ Transport Agency Waka Kotahi, Crash Analysis System (CAS), public extract.
Licensed CC-BY 4.0. Downloaded programmatically from the ArcGIS FeatureServer;
no manual download step. **The public extract contains no crash date or time**,
only `crashYear`, which is why this is a severity analysis rather than a
crash-occurrence or case-crossover analysis.

## Run

```bash
pip install -r requirements.txt
export PYTHONPATH=$PWD/src
python -m cas_severity.extract      # ~60s, caches to data/raw/
python -m cas_severity.clean        # builds analysis sample
python -m cas_severity.model        # fits M1-M4, writes tables 1-5
python -m cas_severity.sensitivity  # interaction contrasts + tables 6-7
python -m cas_severity.figures      # figures 1-3, png + pdf
```

`sensitivity` re-runs `model` internally, so running it alone reproduces
everything except the figures.

## Outputs

| File | Contents |
|---|---|
| `table_s1_sample_derivation.csv` | Exclusion cascade for the methods section |
| `table_1_crude.csv` | Unadjusted DSI proportions and crude ORs |
| `table_2_odds_ratios.csv` | All coefficients, models M1-M4 |
| `table_3_fit_statistics.csv` | AUC, Brier, pseudo-R2, AIC, BIC |
| `table_4_calibration_m2.csv` | Decile calibration |
| `table_5_lr_tests.csv` | Likelihood-ratio tests for interactions |
| `table_6_weather_by_speed.csv` | Stratum-specific ORs (delta method) |
| `table_7_sensitivity.csv` | Alternative sample and outcome definitions |

## Specification

Outcome: death or serious injury vs minor injury, among reported injury
crashes. Non-injury crashes are excluded from the primary sample because their
reporting propensity plausibly varies with the conditions under study.

Standard errors are clustered on territorial authority (67 clusters).

## Attribution

Contains data sourced from the NZ Transport Agency Waka Kotahi Crash Analysis
System, licensed for reuse under CC-BY 4.0.
