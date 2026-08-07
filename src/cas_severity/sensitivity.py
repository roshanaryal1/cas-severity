"""Interaction contrasts and sensitivity analyses.

Two questions are addressed here:

1. Does the association between precipitation and injury severity vary across
   speed environments? (Model 4 interaction, decomposed by the delta method.)
2. How much of the headline result depends on the decision to restrict the
   sample to reported injury crashes? (Alternative outcome definitions.)
"""

from __future__ import annotations

import itertools
import logging

import numpy as np
import pandas as pd
from scipy import stats

from . import config, model

logger = logging.getLogger(__name__)


def interaction_contrasts(
    fit: model.FitResult,
    *,
    exposure_prefix: str = "C(weather_tok, Treatment('fine'))",
    modifier_prefix: str = "C(speed_tok, Treatment('spd50'))",
    exposure_levels: tuple[str, ...] = ("lightrain", "heavyrain", "mistfog", "snowhail"),
    modifier_levels: tuple[str, ...] = ("spd50", "spd60_80", "spd90plus"),
    modifier_reference: str = "spd50",
) -> pd.DataFrame:
    """Odds ratio for each exposure level within each modifier stratum.

    The stratum-specific log odds ratio is ``beta_exposure`` plus, off the
    modifier reference level, the corresponding interaction coefficient. The
    variance follows from the delta method using the cluster-robust covariance
    matrix, so intervals inherit the TLA clustering.
    """
    params = fit.result.params
    cov = fit.result.cov_params()
    z_crit = stats.norm.ppf(1 - config.ALPHA / 2)
    rows: list[dict[str, object]] = []

    for exposure, modifier in itertools.product(exposure_levels, modifier_levels):
        main = f"{exposure_prefix}[T.{exposure}]"
        if main not in params.index:
            continue
        terms = [main]
        if modifier != modifier_reference:
            for candidate in (
                f"{main}:{modifier_prefix}[T.{modifier}]",
                f"{modifier_prefix}[T.{modifier}]:{main}",
            ):
                if candidate in params.index:
                    terms.append(candidate)
                    break

        contrast = np.zeros(len(params))
        for term in terms:
            contrast[params.index.get_loc(term)] = 1.0

        log_or = float(contrast @ params.to_numpy())
        var = float(contrast @ cov.to_numpy() @ contrast)
        se = float(np.sqrt(var))
        rows.append(
            {
                "weather": model.WEATHER_DISPLAY[exposure],
                "speed_environment": model.SPEED_DISPLAY[modifier],
                "or": float(np.exp(log_or)),
                "or_lo": float(np.exp(log_or - z_crit * se)),
                "or_hi": float(np.exp(log_or + z_crit * se)),
                "p": float(2 * stats.norm.sf(abs(log_or / se))),
                "n_terms": len(terms),
            }
        )
    return pd.DataFrame(rows)


def _refit_alternative(
    raw: pd.DataFrame, label: str, outcome: str
) -> model.FitResult | None:
    """Refit the adjusted model under an alternative outcome definition."""
    from . import clean

    frame, _ = clean.build_analysis_sample(raw)
    frame = model.prepare(frame)

    if outcome == "dsi_vs_minor":
        pass  # the primary specification
    elif outcome == "fatal_vs_other_injury":
        frame["dsi"] = (frame["crashSeverity"] == "Fatal Crash").astype(int)
    else:
        raise ValueError(outcome)

    formula = "dsi ~ " + " + ".join(model.EXPOSURE_TERMS + model.ADJUSTMENT_TERMS)
    try:
        return model.fit_logit(frame, formula, label)
    except Exception as exc:  # noqa: BLE001
        logger.error("Alternative model %s failed: %s", label, exc)
        return None


def _refit_including_non_injury(raw: pd.DataFrame) -> model.FitResult | None:
    """Refit with non-injury crashes retained in the denominator.

    This is the specification the primary analysis deliberately avoids. It is
    reported to quantify how much the headline estimate moves once the most
    differentially under-reported crash category is admitted.
    """
    from . import clean

    original = config.INJURY_LEVELS
    try:
        patched = frozenset(original | {"Non-Injury Crash"})
        clean.config.INJURY_LEVELS = patched  # type: ignore[misc]
        frame, _ = clean.build_analysis_sample(raw)
    finally:
        clean.config.INJURY_LEVELS = original  # type: ignore[misc]

    frame = model.prepare(frame)
    formula = "dsi ~ " + " + ".join(model.EXPOSURE_TERMS + model.ADJUSTMENT_TERMS)
    try:
        return model.fit_logit(frame, formula, "S1 all crashes incl. non-injury")
    except Exception as exc:  # noqa: BLE001
        logger.error("Non-injury sensitivity failed: %s", exc)
        return None


def run() -> None:
    config.ensure_dirs()
    artefacts = model.run()
    fits = artefacts["fits"]

    contrasts = interaction_contrasts(fits["M4 weather x speed"])
    contrasts.to_csv(config.OUTPUTS / "table_6_weather_by_speed.csv", index=False)

    raw = pd.read_parquet(config.RAW_PARQUET)
    sensitivity_fits = [
        f
        for f in (
            _refit_including_non_injury(raw),
            _refit_alternative(raw, "S2 fatal vs other injury", "fatal_vs_other_injury"),
        )
        if f is not None
    ]

    frames = [model.odds_ratios(fits["M2 adjusted"])]
    frames.extend(model.odds_ratios(f) for f in sensitivity_fits)
    table = pd.concat(frames, ignore_index=True)
    table["label"] = table["term"].map(model._pretty)
    table = table[table["label"].str.startswith(("Light", "Weather"))]
    table.to_csv(config.OUTPUTS / "table_7_sensitivity.csv", index=False)

    print("\n" + "=" * 92)
    print("WEATHER ODDS RATIOS BY SPEED ENVIRONMENT (M4, delta method, TLA-clustered)")
    print("=" * 92)
    for weather, block in contrasts.groupby("weather", sort=False):
        print(f"  {weather}")
        for _, row in block.iterrows():
            flag = "*" if row["p"] < 0.05 else " "
            print(
                f"    {row['speed_environment']:<12} OR={row['or']:.3f} "
                f"[{row['or_lo']:.3f}, {row['or_hi']:.3f}]  p={row['p']:.2e} {flag}"
            )

    print("\n" + "=" * 92)
    print("SENSITIVITY TO SAMPLE AND OUTCOME DEFINITION")
    print("=" * 92)
    for name, block in table.groupby("model", sort=False):
        print(f"  {name}")
        for _, row in block.iterrows():
            print(
                f"    {row['label']:<28} OR={row['or']:.3f} "
                f"[{row['or_lo']:.3f}, {row['or_hi']:.3f}]"
            )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    run()


if __name__ == "__main__":
    main()
