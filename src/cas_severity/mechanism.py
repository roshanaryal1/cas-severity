"""Mechanism test for the mist-or-fog reversal.

Section 6.2 of the manuscript proposes that the elevated severity odds under
mist or fog in low-speed environments arise through degraded detection of
vulnerable road users. This module tests that proposal directly rather than
leaving it as an untested narrative.

The fully saturated three-way interaction (weather x speed environment x
vulnerable road user) is NOT estimable: only 23 and 24 fog crashes involving a
pedestrian or cyclist occur in the 60-80 and >=90 km/h bands respectively. The
two-way weather x vulnerable-road-user interaction is estimable and is what is
reported, with the power limitation stated explicitly.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

from . import config, model

logger = logging.getLogger(__name__)

VRU_TERM = "vulnerable_road_user"


def _add_vru(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out[VRU_TERM] = (
        (out["pedestrian_involved"] + out["cyclist_involved"]) > 0
    ).astype(int)
    return out


def _base_terms() -> tuple[str, ...]:
    """Adjustment set with the separate pedestrian and cyclist flags removed.

    Those two indicators are replaced by the combined vulnerable-road-user
    term so that the interaction is identified rather than collinear.
    """
    return tuple(
        term
        for term in model.ADJUSTMENT_TERMS
        if term not in {"pedestrian_involved", "cyclist_involved"}
    ) + (VRU_TERM,)


def power_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Cell counts underpinning the estimability judgement."""
    fog = frame[frame["weather"] == "Mist or fog"]
    table = (
        fog.groupby(["speed_band", VRU_TERM], observed=True)["dsi"]
        .agg(n="size", dsi="sum")
        .reset_index()
    )
    table["dsi_pct"] = 100 * table["dsi"] / table["n"]
    table["estimable"] = table["n"] >= 100
    return table


def run() -> None:
    config.ensure_dirs()
    frame = _add_vru(model.prepare(pd.read_parquet(config.ANALYSIS_PARQUET)))

    power = power_table(frame)
    power.to_csv(config.OUTPUTS / "table_8_fog_power.csv", index=False)

    base = _base_terms()
    weather_term = "C(weather_tok, Treatment('fine'))"
    light_term = "C(light_tok, Treatment('brightsun'))"

    m2v = model.fit_logit(
        frame,
        "dsi ~ " + " + ".join((light_term, weather_term) + base),
        "M2v adjusted (VRU combined)",
    )
    m5 = model.fit_logit(
        frame,
        "dsi ~ "
        + " + ".join((light_term,) + base)
        + f" + {weather_term}*{VRU_TERM}",
        "M5 weather x VRU",
    )

    stat = 2 * (m5.result.llf - m2v.result.llf)
    df = int(m5.result.df_model - m2v.result.df_model)
    p_value = float(stats.chi2.sf(stat, df))

    # The VRU modifier enters as a plain binary rather than a patsy factor, so
    # the contrast vectors are constructed directly against the coefficient
    # index. Variance follows from the cluster-robust covariance matrix.
    params = m5.result.params
    cov = m5.result.cov_params()
    z_crit = stats.norm.ppf(1 - config.ALPHA / 2)
    rows: list[dict[str, object]] = []
    for token, label in (
        ("lightrain", "Light rain"),
        ("heavyrain", "Heavy rain"),
        ("mistfog", "Mist or fog"),
    ):
        main = f"{weather_term}[T.{token}]"
        inter = f"{main}:{VRU_TERM}"
        for vru_value, vru_label in ((0, "No pedestrian or cyclist"), (1, "Pedestrian or cyclist")):
            contrast = np.zeros(len(params))
            contrast[params.index.get_loc(main)] = 1.0
            if vru_value == 1 and inter in params.index:
                contrast[params.index.get_loc(inter)] = 1.0
            log_or = float(contrast @ params.to_numpy())
            se = float(np.sqrt(contrast @ cov.to_numpy() @ contrast))
            rows.append(
                {
                    "weather": label,
                    "road_user": vru_label,
                    "or": float(np.exp(log_or)),
                    "or_lo": float(np.exp(log_or - z_crit * se)),
                    "or_hi": float(np.exp(log_or + z_crit * se)),
                    "p": float(2 * stats.norm.sf(abs(log_or / se))),
                }
            )
    contrasts = pd.DataFrame(rows)
    contrasts.to_csv(config.OUTPUTS / "table_9_weather_by_vru.csv", index=False)

    pd.DataFrame(
        [
            {
                "comparison": "M5 weather x VRU vs M2v adjusted",
                "lr_chi2": stat,
                "df": df,
                "p": p_value,
            }
        ]
    ).to_csv(config.OUTPUTS / "table_10_vru_lr_test.csv", index=False)

    print("=" * 88)
    print("POWER: fog crashes by speed environment and road-user type")
    print("=" * 88)
    for _, row in power.iterrows():
        flag = "" if row["estimable"] else "  <- too sparse"
        vru = "with VRU " if row[VRU_TERM] == 1 else "no VRU   "
        print(
            f"  {str(row['speed_band']):<12}{vru} n={int(row['n']):>5} "
            f"DSI={row['dsi_pct']:5.1f}%{flag}"
        )

    print()
    print("=" * 88)
    print("WEATHER x VULNERABLE ROAD USER INTERACTION")
    print("=" * 88)
    print(f"  LR chi2 = {stat:.2f}, df = {df}, p = {p_value:.4f}")
    print()
    for weather, block in contrasts.groupby("weather", sort=False):
        print(f"  {weather}")
        for _, row in block.iterrows():
            flag = "*" if row["p"] < 0.05 else " "
            print(
                f"    {row['road_user']:<26} OR={row['or']:.3f} "
                f"[{row['or_lo']:.3f}, {row['or_hi']:.3f}] p={row['p']:.3f} {flag}"
            )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    run()


if __name__ == "__main__":
    main()
