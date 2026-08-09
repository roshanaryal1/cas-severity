# Provenance

CAS is a live database: NZTA revises severity classifications as hospital
data arrives and adds late-reported crashes. This file pins the exact
extraction this repository's committed outputs and analysis parquet were
generated from.

- **Source:** NZ Transport Agency Waka Kotahi, Crash Analysis System (CAS),
  public extract. Licensed CC-BY 4.0.
- **Endpoint:** `https://services.arcgis.com/CXBb7LAjgIIdcsPt/ArcGIS/rest/services/CAS_Data_Public/FeatureServer/0/query`
- **Extraction date:** 2026-08-09 03:00 NZST (2026-08-08 15:00 UTC)
- **Query window:** `crashYear >= 2010 AND crashYear <= 2024`
- **Raw row count:** 502,792
- **Analysis sample (after exclusion cascade):** 153,597
- **DSI (death or serious injury) in analysis sample:** 32,918 (21.43%)
- **Raw cache checksum (SHA-256):**
  `eeb08521776160205a6a0e4d33ae3a262da67d2f9137c38aa0e186d4615d837d`
  (`data/raw/cas_raw.parquet`)

To verify: re-run `python -m cas_severity.extract`, hash the resulting file,
and compare. A mismatch means CAS has been revised since this checksum was
taken, not that the pipeline is broken — that is expected over time and is
the reason this file, the committed `outputs/`, and the committed analysis
parquet are the fixed record of what the paper reports.

## Note on the two dates in this repository

`RESULTS.md` records "Analysis run: 7 August 2026" — that is the original
modeling run. The extraction date above (9 August 2026) is a later
cold-start re-pull of raw CAS data, performed to verify that `temporal.py`
reproduces its own published results before it was added to the archive.
These are not in conflict: the 7 August and 9 August extracts produced
identical sample counts (153,597 crashes / 32,918 DSI), so the pipeline is
stable across the two-day gap and both dates correctly describe different
events, not different results.
