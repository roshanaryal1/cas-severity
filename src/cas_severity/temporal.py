"""Temporal instability of exposure effects across the study window.

Mannering (2018) documents that parameters estimated from long crash time
series can be unstable, and that pooling across periods without testing for
instability risks reporting an average of effects that differ materially by
era. The present analysis pools fifteen years with year fixed effects, which
absorbs level shifts but not changes in the exposure coefficients themselves.

Two tests are implemented:

1. **Interaction test (primary).** Period-by-exposure interactions are added to
   the adjusted specification and the block is tested jointly. A cluster-robust
   Wald test is used as the primary test because the likelihood ratio test
   assumes independent observations, which the clustered design violates. The
   LR statistic is reported alongside it for reference.

2. **Full transferability test.** The adjusted model is refitted separately
   within each period and compared against the pooled fit. This tests whether
   *any* coefficient differs by period, not only the exposure coefficients.

Period-specific odds ratios are recovered from the interaction model by the
delta method using the cluster-robust covariance matrix.

Note on 2020-2021: New Zealand's COVID-19 restrictions produced large
transient changes in traffic volume and composition. Period 3 contains those
years, so a period effect there is not necessarily evidence of secular drift.
A supplementary specification excluding 2020 and 2021 is therefore reported.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

from . import config, model

logger = logging.getLogger(__name__)

PERIODS: tuple[tuple[int, int, str], ...] = (
    (2010, 2014, "P1_2010_2014"),
    (2015, 2019, "P2_2015_2019"),
    (2020, 2024, "P3_2020_2024"),
)
PERIOD_REFERENCE = "P1_2010_2014"

LIGHT_TERM = "C(light_tok, Treatment('brightsun'))"
WEATHER_TERM = "C(weather_tok, Treatment('fine'))"
PERIOD_TERM = f"C(period, Treatment('{PERIOD_REFERENCE}'))"


def _assign_period(year: int) -> str:
    for lo, hi, label in PERIODS:
        if lo <= year <= hi:
            return label
    raise ValueError(f"year {year} outside defined periods")


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    out = model.prepare(frame)
    out["period"] = out["year"].map(_assign_period)
    return out


def _adjustment_without_year() -> tuple[str, ...]:
    """Adjustment set with the year factor removed.

    Year fixed effects are collinear with period, so the period main effect
    replaces them in the interaction models.
    """
    return tuple(t for t in model.ADJUSTMENT_TERMS if t != "C(year)")


def wald_block_test(fit: model.FitResult, prefix: str) -> tuple[float, int, float]:
    """Cluster-robust Wald test that all terms containing ``prefix`` are zero."""
    params = fit.result.params
    idx = [i for i, name in enumerate(params.index) if prefix in name and ":" in name]
    if not idx:
        raise ValueError(f"no interaction terms matched prefix {prefix!r}")
    beta = params.to_numpy()[idx]
    cov = fit.result.cov_params().to_numpy()[np.ix_(idx, idx)]
    stat = float(beta @ np.linalg.solve(cov, beta))
    df = len(idx)
    return stat, df, float(stats.chi2.sf(stat, df))


def period_specific_ors(fit: model.FitResult) -> pd.DataFrame:
    """Exposure odds ratios within each period, delta method."""
    params = fit.result.params
    cov = fit.result.cov_params().to_numpy()
    z = stats.norm.ppf(1 - config.ALPHA / 2)
    rows: list[dict[str, object]] = []

    exposures = [
        (LIGHT_TERM, "dark", "Dark"),
        (WEATHER_TERM, "lightrain", "Light rain"),
        (WEATHER_TERM, "heavyrain", "Heavy rain"),
    ]
    for term, token, label in exposures:
        main = f"{term}[T.{token}]"
        if main not in params.index:
            continue
        for _, _, period in PERIODS:
            contrast = np.zeros(len(params))
            contrast[params.index.get_loc(main)] = 1.0
            if period != PERIOD_REFERENCE:
                for cand in (
                    f"{main}:{PERIOD_TERM}[T.{period}]",
                    f"{PERIOD_TERM}[T.{period}]:{main}",
                ):
                    if cand in params.index:
                        contrast[params.index.get_loc(cand)] = 1.0
                        break
            log_or = float(contrast @ params.to_numpy())
            se = float(np.sqrt(contrast @ cov @ contrast))
            rows.append(
                {
                    "exposure": label,
                    "period": period,
                    "or": float(np.exp(log_or)),
                    "or_lo": float(np.exp(log_or - z * se)),
                    "or_hi": float(np.exp(log_or + z * se)),
                }
            )
    return pd.DataFrame(rows)


def transferability_test(frame: pd.DataFrame) -> dict[str, float]:
    """Likelihood-ratio test of full parameter transferability across periods."""
    formula = "dsi ~ " + " + ".join(
        (LIGHT_TERM, WEATHER_TERM) + _adjustment_without_year()
    )
    pooled = model.fit_logit(frame, formula, "pooled (no year FE)")
    total_ll = 0.0
    total_params = 0
    for _, _, period in PERIODS:
        sub = frame[frame["period"] == period]
        fit = model.fit_logit(sub, formula, f"period {period}")
        total_ll += fit.result.llf
        total_params += int(fit.result.df_model)
        logger.info("  %s: n=%d, llf=%.1f", period, len(sub), fit.result.llf)
    stat = 2 * (total_ll - pooled.result.llf)
    df = total_params - int(pooled.result.df_model)
    return {
        "lr_chi2": float(stat),
        "df": float(df),
        "p": float(stats.chi2.sf(stat, df)) if df > 0 else float("nan"),
    }


def run() -> None:
    config.ensure_dirs()
    frame = prepare(pd.read_parquet(config.ANALYSIS_PARQUET))

    print("=" * 84)
    print("SAMPLE BY PERIOD")
    print("=" * 84)
    tab = frame.groupby("period")["dsi"].agg(n="size", dsi="sum")
    tab["dsi_pct"] = 100 * tab["dsi"] / tab["n"]
    for period, row in tab.iterrows():
        print(
            f"  {period:<16} n={int(row['n']):>7}  DSI={int(row['dsi']):>6} "
            f"({row['dsi_pct']:5.2f}%)"
        )

    base = _adjustment_without_year()

    m_main = model.fit_logit(
        frame,
        "dsi ~ " + " + ".join((LIGHT_TERM, WEATHER_TERM, PERIOD_TERM) + base),
        "M6a period main effect",
    )
    m_int = model.fit_logit(
        frame,
        "dsi ~ "
        + " + ".join(base)
        + f" + {LIGHT_TERM}*{PERIOD_TERM} + {WEATHER_TERM}*{PERIOD_TERM}",
        "M6b period x exposure",
    )

    wald_stat, wald_df, wald_p = wald_block_test(m_int, "period")
    lr_stat = 2 * (m_int.result.llf - m_main.result.llf)
    lr_df = int(m_int.result.df_model - m_main.result.df_model)
    lr_p = float(stats.chi2.sf(lr_stat, lr_df))

    print()
    print("=" * 84)
    print("TEST 1: PERIOD x EXPOSURE INTERACTIONS")
    print("=" * 84)
    print(f"  Cluster-robust Wald  chi2={wald_stat:7.2f}  df={wald_df:2d}  p={wald_p:.4f}")
    print(f"  Likelihood ratio     chi2={lr_stat:7.2f}  df={lr_df:2d}  p={lr_p:.4f}")
    print("  (Wald is primary: LR assumes independence, violated by TLA clustering)")

    ors = period_specific_ors(m_int)
    ors.to_csv(config.OUTPUTS / "table_11_period_specific_ors.csv", index=False)
    print()
    print("  Period-specific odds ratios (delta method, TLA-clustered):")
    for exposure, block in ors.groupby("exposure", sort=False):
        print(f"    {exposure}")
        for _, r in block.iterrows():
            print(
                f"      {r['period']:<16} OR={r['or']:.3f} "
                f"[{r['or_lo']:.3f}, {r['or_hi']:.3f}]"
            )

    print()
    print("=" * 84)
    print("TEST 2: FULL PARAMETER TRANSFERABILITY")
    print("=" * 84)
    trans = transferability_test(frame)
    print(
        f"  LR chi2={trans['lr_chi2']:.2f}  df={int(trans['df'])}  p={trans['p']:.4g}"
    )

    print()
    print("=" * 84)
    print("SUPPLEMENTARY: EXCLUDING 2020-2021 (COVID-19 RESTRICTIONS)")
    print("=" * 84)
    sub = frame[~frame["year"].isin([2020, 2021])]
    m_main_x = model.fit_logit(
        sub,
        "dsi ~ " + " + ".join((LIGHT_TERM, WEATHER_TERM, PERIOD_TERM) + base),
        "M6a excl COVID",
    )
    m_int_x = model.fit_logit(
        sub,
        "dsi ~ "
        + " + ".join(base)
        + f" + {LIGHT_TERM}*{PERIOD_TERM} + {WEATHER_TERM}*{PERIOD_TERM}",
        "M6b excl COVID",
    )
    ws, wd, wp = wald_block_test(m_int_x, "period")
    print(f"  n={len(sub):,} (dropped {len(frame) - len(sub):,})")
    print(f"  Cluster-robust Wald  chi2={ws:7.2f}  df={wd:2d}  p={wp:.4f}")

    pd.DataFrame(
        [
            {
                "test": "period x exposure, Wald (cluster-robust)",
                "stat": wald_stat, "df": wald_df, "p": wald_p,
            },
            {
                "test": "period x exposure, LR", "stat": lr_stat, "df": lr_df, "p": lr_p,
            },
            {
                "test": "full transferability, LR",
                "stat": trans["lr_chi2"], "df": trans["df"], "p": trans["p"],
            },
            {
                "test": "period x exposure, Wald, excl 2020-21",
                "stat": ws, "df": wd, "p": wp,
            },
        ]
    ).to_csv(config.OUTPUTS / "table_12_temporal_instability.csv", index=False)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    run()


if __name__ == "__main__":
    main()
