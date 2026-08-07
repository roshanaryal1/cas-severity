"""Logistic regression of injury-crash severity on environmental conditions.

Estimates the association between light condition, weather and the odds that a
reported injury crash resulted in death or serious injury, adjusting for the
speed environment, road configuration, road-user mix, region and year.

Interpretation warning carried throughout: these are severity odds *conditional
on a crash having been reported*. They are not crash-occurrence risks. See the
limitations discussion in the manuscript.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

from . import config

logger = logging.getLogger(__name__)

# Patsy term names become unreadable when level labels contain punctuation,
# so levels are modelled under safe tokens and mapped back for reporting.
SPEED_TOKENS: dict[str, str] = {
    "<=50 km/h": "spd50",
    "60-80 km/h": "spd60_80",
    ">=90 km/h": "spd90plus",
}
SPEED_DISPLAY: dict[str, str] = {v: k for k, v in SPEED_TOKENS.items()}

LIGHT_TOKENS: dict[str, str] = {
    "Bright sun": "brightsun",
    "Overcast": "overcast",
    "Twilight": "twilight",
    "Dark": "dark",
}
LIGHT_DISPLAY: dict[str, str] = {v: k for k, v in LIGHT_TOKENS.items()}

WEATHER_TOKENS: dict[str, str] = {
    "Fine": "fine",
    "Light rain": "lightrain",
    "Heavy rain": "heavyrain",
    "Mist or fog": "mistfog",
    "Snow or hail": "snowhail",
}
WEATHER_DISPLAY: dict[str, str] = {v: k for k, v in WEATHER_TOKENS.items()}

ADJUSTMENT_TERMS: tuple[str, ...] = (
    "C(speed_tok, Treatment('spd50'))",
    "C(urban, Treatment('Urban'))",
    "C(state_highway, Treatment('Local road'))",
    "C(traffic_control, Treatment('None'))",
    "C(road_character, Treatment('Nil'))",
    "C(street_light, Treatment('Unrecorded'))",
    "C(flat_hill, Treatment('Flat'))",
    "C(road_lane, Treatment('2-way'))",
    "C(lane_count, Treatment('1-2 lanes'))",
    "C(holiday_period, Treatment('Not holiday'))",
    "motorcycle_involved",
    "pedestrian_involved",
    "cyclist_involved",
    "heavy_vehicle_involved",
    "C(year)",
    "C(region)",
)

EXPOSURE_TERMS: tuple[str, ...] = (
    "C(light_tok, Treatment('brightsun'))",
    "C(weather_tok, Treatment('fine'))",
)


@dataclass(frozen=True)
class FitResult:
    """Container for a fitted model and its derived quantities."""

    name: str
    formula: str
    result: object
    n_obs: int
    n_events: int
    auc: float
    brier: float

    def summary_line(self) -> str:
        return (
            f"{self.name}: n={self.n_obs:,} events={self.n_events:,} "
            f"AUC={self.auc:.4f} Brier={self.brier:.4f} "
            f"pseudo-R2={getattr(self.result, 'prsquared', float('nan')):.4f}"
        )


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach model-safe token columns."""
    out = frame.copy()
    out["speed_tok"] = out["speed_band"].astype(str).map(SPEED_TOKENS)
    out["light_tok"] = out["light"].astype(str).map(LIGHT_TOKENS)
    out["weather_tok"] = out["weather"].astype(str).map(WEATHER_TOKENS)
    for col in ("speed_tok", "light_tok", "weather_tok"):
        if out[col].isna().any():
            raise ValueError(f"Unmapped level in {col}")
    return out


def _auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Area under the ROC curve via the Mann-Whitney U identity."""
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    u = stats.mannwhitneyu(pos, neg, alternative="greater").statistic
    return float(u / (len(pos) * len(neg)))


def fit_logit(
    frame: pd.DataFrame,
    formula: str,
    name: str,
    *,
    cluster: str = config.CLUSTER_VAR,
) -> FitResult:
    """Fit a logit with cluster-robust standard errors.

    Clustering on territorial authority accounts for shared road design
    standards, enforcement intensity and reporting practice within councils.
    """
    logger.info("Fitting %s", name)
    model = smf.logit(formula, data=frame)
    result = model.fit(
        cov_type="cluster",
        cov_kwds={"groups": frame[cluster].to_numpy()},
        disp=False,
        maxiter=200,
    )
    y = frame["dsi"].to_numpy()
    p = np.asarray(result.predict(frame))
    return FitResult(
        name=name,
        formula=formula,
        result=result,
        n_obs=int(result.nobs),
        n_events=int(y.sum()),
        auc=_auc(y, p),
        brier=float(np.mean((p - y) ** 2)),
    )


def odds_ratios(fit: FitResult, alpha: float = config.ALPHA) -> pd.DataFrame:
    """Return a tidy odds-ratio table with cluster-robust intervals."""
    res = fit.result
    params = res.params
    conf = res.conf_int(alpha=alpha)
    conf.columns = ["lo", "hi"]
    table = pd.DataFrame(
        {
            "term": params.index,
            "beta": params.to_numpy(),
            "se": res.bse.to_numpy(),
            "z": res.tvalues.to_numpy(),
            "p": res.pvalues.to_numpy(),
            "or": np.exp(params.to_numpy()),
            "or_lo": np.exp(conf["lo"].to_numpy()),
            "or_hi": np.exp(conf["hi"].to_numpy()),
        }
    )
    table.insert(0, "model", fit.name)
    return table


def _pretty(term: str) -> str:
    """Turn a patsy term name into something a reader can parse."""
    out = term
    for token, label in {**LIGHT_DISPLAY, **WEATHER_DISPLAY, **SPEED_DISPLAY}.items():
        out = out.replace(f"T.{token}]", f"T.{label}]")
    out = (
        out.replace("C(light_tok, Treatment('brightsun'))", "Light")
        .replace("C(weather_tok, Treatment('fine'))", "Weather")
        .replace("C(speed_tok, Treatment('spd50'))", "Speed environment")
        .replace("C(urban, Treatment('Urban'))", "Area")
        .replace("C(state_highway, Treatment('Local road'))", "Road class")
        .replace("C(traffic_control, Treatment('None'))", "Traffic control")
        .replace("C(road_character, Treatment('Nil'))", "Road feature")
        .replace("C(street_light, Treatment('Unrecorded'))", "Street lighting")
        .replace("C(flat_hill, Treatment('Flat'))", "Terrain")
        .replace("C(road_lane, Treatment('2-way'))", "Carriageway")
        .replace("C(lane_count, Treatment('1-2 lanes'))", "Lanes")
        .replace("C(holiday_period, Treatment('Not holiday'))", "Holiday period")
    )
    out = out.replace("[T.", ": ").replace("]", "")
    return out


def crude_table(frame: pd.DataFrame, variable: str) -> pd.DataFrame:
    """Unadjusted DSI proportion and crude odds ratio by level of ``variable``."""
    rows: list[dict[str, object]] = []
    reference = {
        "light": "Bright sun",
        "weather": "Fine",
        "speed_band": "<=50 km/h",
    }[variable]
    grouped = frame.groupby(variable, observed=True)["dsi"].agg(["size", "sum"])
    ref_n, ref_k = grouped.loc[reference, "size"], grouped.loc[reference, "sum"]
    ref_odds = ref_k / (ref_n - ref_k)
    for level, row in grouped.iterrows():
        n, k = int(row["size"]), int(row["sum"])
        odds = k / (n - k) if n > k else np.nan
        or_ = odds / ref_odds
        se_log = np.sqrt(1 / k + 1 / (n - k) + 1 / ref_k + 1 / (ref_n - ref_k))
        z = stats.norm.ppf(1 - config.ALPHA / 2)
        rows.append(
            {
                "variable": variable,
                "level": level,
                "n": n,
                "dsi": k,
                "dsi_pct": 100 * k / n,
                "crude_or": 1.0 if level == reference else or_,
                "crude_lo": np.nan if level == reference else or_ * np.exp(-z * se_log),
                "crude_hi": np.nan if level == reference else or_ * np.exp(z * se_log),
            }
        )
    return pd.DataFrame(rows)


def calibration(frame: pd.DataFrame, fit: FitResult, bins: int = 10) -> pd.DataFrame:
    """Decile calibration table: mean predicted vs observed DSI rate."""
    p = np.asarray(fit.result.predict(frame))
    decile = pd.qcut(p, bins, labels=False, duplicates="drop")
    out = (
        pd.DataFrame({"p": p, "y": frame["dsi"].to_numpy(), "decile": decile})
        .groupby("decile")
        .agg(n=("y", "size"), predicted=("p", "mean"), observed=("y", "mean"))
        .reset_index()
    )
    out["ratio"] = out["observed"] / out["predicted"]
    return out


def run() -> dict[str, object]:
    """Execute the full model sequence and write output tables."""
    config.ensure_dirs()
    frame = prepare(pd.read_parquet(config.ANALYSIS_PARQUET))

    # ---- Crude associations -----------------------------------------
    crude = pd.concat(
        [crude_table(frame, v) for v in ("light", "weather", "speed_band")],
        ignore_index=True,
    )
    crude.to_csv(config.OUTPUTS / "table_1_crude.csv", index=False)

    # ---- Model 1: exposures only ------------------------------------
    m1 = fit_logit(frame, f"dsi ~ {' + '.join(EXPOSURE_TERMS)}", "M1 exposures only")

    # ---- Model 2: fully adjusted main effects -----------------------
    m2 = fit_logit(
        frame,
        "dsi ~ " + " + ".join(EXPOSURE_TERMS + ADJUSTMENT_TERMS),
        "M2 adjusted",
    )

    # ---- Model 3: adjusted + light x weather ------------------------
    m3 = fit_logit(
        frame,
        "dsi ~ "
        + " + ".join(ADJUSTMENT_TERMS)
        + " + C(light_tok, Treatment('brightsun'))*C(weather_tok, Treatment('fine'))",
        "M3 light x weather",
    )

    # ---- Model 4: adjusted + weather x speed environment ------------
    m4 = fit_logit(
        frame,
        "dsi ~ "
        + " + ".join(ADJUSTMENT_TERMS)
        + " + C(light_tok, Treatment('brightsun'))"
        + " + C(weather_tok, Treatment('fine'))*C(speed_tok, Treatment('spd50'))",
        "M4 weather x speed",
    )

    fits = [m1, m2, m3, m4]
    all_or = pd.concat([odds_ratios(f) for f in fits], ignore_index=True)
    all_or["label"] = all_or["term"].map(_pretty)
    all_or.to_csv(config.OUTPUTS / "table_2_odds_ratios.csv", index=False)

    fit_stats = pd.DataFrame(
        [
            {
                "model": f.name,
                "n": f.n_obs,
                "events": f.n_events,
                "auc": f.auc,
                "brier": f.brier,
                "pseudo_r2": getattr(f.result, "prsquared", np.nan),
                "aic": f.result.aic,
                "bic": f.result.bic,
                "df_model": f.result.df_model,
            }
            for f in fits
        ]
    )
    fit_stats.to_csv(config.OUTPUTS / "table_3_fit_statistics.csv", index=False)

    calibration(frame, m2).to_csv(
        config.OUTPUTS / "table_4_calibration_m2.csv", index=False
    )

    # ---- Likelihood-ratio tests for the interaction terms ------------
    lr_rows = []
    for interaction_fit in (m3, m4):
        stat = 2 * (interaction_fit.result.llf - m2.result.llf)
        df = int(interaction_fit.result.df_model - m2.result.df_model)
        lr_rows.append(
            {
                "comparison": f"{interaction_fit.name} vs {m2.name}",
                "lr_chi2": stat,
                "df": df,
                "p": float(stats.chi2.sf(stat, df)) if df > 0 else np.nan,
            }
        )
    pd.DataFrame(lr_rows).to_csv(
        config.OUTPUTS / "table_5_lr_tests.csv", index=False
    )

    return {"frame": frame, "fits": {f.name: f for f in fits}, "crude": crude}


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    artefacts = run()
    for fit in artefacts["fits"].values():
        print(fit.summary_line())


if __name__ == "__main__":
    main()
