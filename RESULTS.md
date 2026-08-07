# Results Summary

**Analysis run:** 7 August 2026
**Data:** NZTA Crash Analysis System public extract, national, 2010-2024 (CC-BY 4.0)
**Sample:** 153,597 reported injury crashes, 32,918 (21.43%) fatal or serious
**Clusters:** 67 territorial authorities

---

## Proposed title

*Adverse weather is associated with lower injury severity in New Zealand road crashes: a national analysis of 153,597 injury crashes and the limits of severity-based risk inference*

## The headline finding, in one sentence

Across fifteen years of national crash data, precipitation is associated with **lower** odds that a reported injury crash killed or seriously injured someone, the protective association strengthens monotonically as the speed environment rises, and darkness runs in the opposite direction, all of which is consistent with behavioural compensation but cannot by itself establish that driving in rain is safer.

---

## 1. Sample derivation (Table S1)

| Exclusion | Dropped | Remaining |
|---|---:|---:|
| Starting extract, 2010-2024 | 0 | 502,792 |
| Non-injury crashes excluded | 345,562 | 157,230 |
| Light condition unknown | 130 | 157,100 |
| Weather unrecorded | 545 | 156,555 |
| Speed limit missing or out of range | 763 | 155,792 |
| Terrain unrecorded | 259 | 155,533 |
| Road lane configuration unrecorded | 62 | 155,471 |
| Lane count missing | 1,871 | 153,600 |
| Territorial authority missing | 3 | 153,597 |

Only 2.31% of injury crashes were lost to item missingness, so complete-case analysis is defensible and multiple imputation is not required. State this explicitly; a reviewer will ask.

## 2. Crude associations (Table 1)

| Variable | Level | n | DSI % | Crude OR [95% CI] |
|---|---|---:|---:|---|
| Light | Bright sun | 59,677 | 21.62 | 1.00 (ref) |
| | Overcast | 45,265 | 18.87 | 0.844 [0.818, 0.870] |
| | Twilight | 7,301 | 20.75 | 0.949 [0.894, 1.008] |
| | Dark | 41,354 | 24.08 | 1.150 [1.117, 1.185] |
| Weather | Fine | 123,992 | 22.05 | 1.00 (ref) |
| | Light rain | 21,399 | 18.36 | 0.795 [0.766, 0.825] |
| | Heavy rain | 5,542 | 18.69 | 0.813 [0.759, 0.871] |
| | Mist or fog | 2,386 | 23.34 | 1.076 [0.978, 1.185] |
| | Snow or hail | 278 | 19.06 | 0.833 [0.617, 1.123] |
| Speed | ≤50 km/h | 80,441 | 17.27 | 1.00 (ref) |
| | 60-80 km/h | 20,649 | 21.72 | 1.329 [1.280, 1.380] |
| | ≥90 km/h | 52,507 | 27.70 | 1.835 [1.787, 1.884] |

## 3. Adjusted model (Table 2, Model M2)

Logistic regression, DSI vs minor injury. Adjusted for speed environment, urban/open, road class, traffic control, road feature, street lighting, terrain, carriageway type, lane count, holiday period, road-user mix (motorcycle, pedestrian, cyclist, heavy vehicle), year and region. Cluster-robust standard errors on territorial authority.

**Exposures of interest:**

| Term | aOR [95% CI] | p |
|---|---|---|
| Dark (ref: bright sun) | **1.355 [1.262, 1.455]** | 4.4e-17 |
| Overcast | 0.945 [0.912, 0.980] | 0.002 |
| Twilight | 1.040 [0.985, 1.099] | 0.158 |
| Light rain (ref: fine) | **0.835 [0.795, 0.877]** | 3.9e-13 |
| Heavy rain | **0.822 [0.748, 0.904]** | 5.3e-05 |
| Mist or fog | 0.858 [0.758, 0.971] | 0.015 |
| Snow or hail | 0.689 [0.523, 0.910] | 0.009 |

Note the direction of confounding: the darkness effect is **stronger** after adjustment (1.150 crude → 1.355 adjusted), because dark crashes are disproportionately urban and low-speed. Say this in the results; it is evidence the adjustment set is doing real work.

**Adjustment covariates behave as the literature predicts**, which is your internal validity argument:

| Term | aOR [95% CI] |
|---|---|
| Motorcycle involved | 3.523 [3.407, 3.643] |
| Pedestrian involved | 3.125 [3.000, 3.256] |
| Cyclist involved | 2.188 [2.007, 2.384] |
| Heavy vehicle involved | 1.691 [1.619, 1.766] |
| Speed environment ≥90 km/h | 1.988 [1.819, 2.172] |
| Speed environment 60-80 km/h | 1.581 [1.502, 1.664] |
| One-way carriageway | 0.544 [0.434, 0.683] |
| Traffic signals | 0.828 [0.770, 0.890] |
| Hill road | 1.120 [1.064, 1.179] |

## 4. Model performance (Table 3)

| Model | AUC | Brier | Pseudo-R² | AIC |
|---|---:|---:|---:|---:|
| M1 exposures only | 0.537 | 0.1678 | 0.0031 | 159,145 |
| M2 adjusted | 0.681 | 0.1558 | 0.0699 | 148,589 |
| M3 + light × weather | 0.681 | 0.1558 | 0.0700 | 148,602 |
| M4 + weather × speed | 0.681 | 0.1557 | 0.0702 | 148,567 |

Calibration is excellent: observed/predicted ratios range 0.937 to 1.038 across deciles (Table 4, Figure 3).

**Use these numbers to make a methodological point.** A well-specified model with strong calibration and sensible coefficients explains roughly 7% of the variation in severity. Crash outcomes are dominated by unmeasured mechanism: impact angle, delta-v, occupant age, restraint use, vehicle safety rating, none of which are in CAS. Any paper reporting high explained variance on crash data is almost certainly leaking its target. This framing turns a modest R² from a weakness into a contribution.

## 5. Interaction: weather × speed environment (Table 6, Figure 2)

Light × weather interaction: **not significant** (LR χ² = 10.63, df = 12, p = 0.560). Report the null; it says the two exposures act independently.

Weather × speed environment: **significant** (LR χ² = 38.03, df = 8, p = 7.0e-06).

| Weather | ≤50 km/h | 60-80 km/h | ≥90 km/h |
|---|---|---|---|
| Light rain | 0.908 [0.866, 0.951] | 0.830 [0.741, 0.930] | 0.776 [0.741, 0.812] |
| Heavy rain | 0.971 [0.909, 1.037] | 0.812 [0.658, 1.003] | 0.730 [0.662, 0.807] |
| Mist or fog | **1.190 [1.023, 1.385]** | 0.890 [0.731, 1.083] | 0.748 [0.648, 0.863] |
| Snow or hail | 0.575 [0.336, 0.983] | 0.582 [0.151, 2.235] | 0.709 [0.512, 0.983] |

**This is the paper's most interesting result.** Two things to draw out:

1. **Monotonic dose-response.** Rain's protective association strengthens as speed rises. This is what behavioural compensation predicts: drivers in a 100 km/h environment have far more speed available to surrender than drivers in a 50 km/h environment, so the compensation effect is largest where the speed headroom is largest.

2. **Mist and fog reverse sign.** Harmful at ≤50 km/h (aOR 1.190), protective at ≥90 km/h (aOR 0.748), with non-overlapping intervals. A plausible mechanism worth offering cautiously: in low-speed urban environments the dominant severity pathway is failure to detect vulnerable road users, and reduced visibility worsens detection without materially reducing already-low speeds. On open roads, fog triggers substantial speed reduction. Flag this as hypothesis-generating, not established.

## 6. Sensitivity (Table 7)

| Specification | Light rain aOR | Heavy rain aOR | Dark aOR |
|---|---|---|---|
| Primary (injury crashes only) | 0.835 [0.795, 0.877] | 0.822 [0.748, 0.904] | 1.355 [1.262, 1.455] |
| All crashes incl. non-injury | 0.828 [0.792, 0.867] | 0.786 [0.711, 0.868] | 1.248 [1.159, 1.344] |
| Fatal vs other injury | 0.790 [0.708, 0.881] | 0.881 [0.716, 1.083] | 1.556 [1.353, 1.789] |

Conclusions are stable across all three. The darkness effect strengthens as the outcome becomes more severe (1.248 → 1.355 → 1.556), a coherent gradient worth remarking on.

---

## 7. Limitations to write properly

This section is where the paper earns its keep. Do not compress it.

1. **Conditioning on a crash is a collider.** Every estimate is conditional on a crash having occurred and been reported. Selecting on a common effect of exposure and outcome can induce association where none exists. Severity odds are not occurrence risk, and the two can move in opposite directions.

2. **No exposure denominator.** The public CAS extract has no traffic volume, so crash *rates* per vehicle-kilometre cannot be computed. If rain generates disproportionately many low-severity crashes, the DSI share falls even if absolute harm rises.

3. **No crash timestamp.** The public extract carries only `crashYear`. Time of day, day of week and season cannot be recovered, so external meteorological reanalysis cannot be joined and case-crossover or time-stratified designs are impossible. Weather is as recorded by attending police, which is coarse, categorical and potentially subject to post-hoc rationalisation.

4. **Under-reporting.** Roughly two thirds of injury crashes reach CAS, and reporting propensity is not random. Non-injury crashes are excluded from the primary sample for exactly this reason, but residual bias within injury crashes remains.

5. **No occupant or vehicle detail.** Age, restraint use, impairment, vehicle safety rating and impact configuration are all absent and are among the strongest severity determinants. This is the main reason for the modest pseudo-R².

6. **Ecological speed measure.** Posted limit is not travelled speed. The compensation interpretation is inferred, not measured.

7. **`roadSurface` is Sealed/Unsealed, not wet/dry.** There is no surface-condition variable, so wet-road state is proxied only through `weatherA`.

## 8. What this means practically

Write a short subsection making the applied point, because it is the bridge to SDG 3.6 and to your wider work: **a severity model must not be used as a route risk score.** A system that tells drivers a wet route is safer, on the strength of severity odds alone, would be drawing an unsupported conclusion from a collider-conditioned estimate. Establishing conditional occurrence risk requires crash timestamps and exposure denominators, neither of which the open data provides. That is a concrete, defensible recommendation for what NZTA should add to the public release, and it doubles as your future work section.

## 9. SDG alignment

- **SDG 3.6** (halve global deaths and injuries from road traffic crashes): the analysis identifies which conditions concentrate serious harm and, more usefully, warns against a specific class of inferential error in road safety analytics.
- **SDG 11.2** (safe, accessible and sustainable transport systems): the speed-environment interaction supports speed management as the dominant lever, and the mist/fog reversal identifies vulnerable road user detection in low-speed urban settings as a distinct problem.

## 10. Data availability and ethics statements

> **Data availability.** This study analysed the publicly available Crash Analysis System extract published by the NZ Transport Agency Waka Kotahi under a Creative Commons Attribution 4.0 International licence. Analysis code is available at [repository].

> **Ethics.** This study is a secondary analysis of publicly available, de-identified aggregate crash records containing no personal information. It did not involve human participants and did not require ethics committee approval.

---

## Suggested figure captions

**Fig. 1.** Crude and adjusted odds ratios for death or serious injury by light condition and weather, New Zealand reported injury crashes 2010-2024 (n = 153,597). Adjusted estimates from Model M2. Horizontal bars are 95% confidence intervals with standard errors clustered on territorial authority.

**Fig. 2.** Adjusted odds ratios for death or serious injury by weather, stratified by posted speed environment (Model M4, n = 153,597). Reference is fine weather within each stratum. The protective association with precipitation strengthens as the speed environment rises, while mist or fog reverses direction between low- and high-speed environments.

**Fig. 3.** Calibration of the adjusted model (M2) by decile of predicted probability. The dashed line is perfect calibration.
