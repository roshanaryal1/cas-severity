"""Construction of the analysis sample from the raw CAS extract.

Every exclusion is counted and reported so that the paper can carry an
auditable sample-derivation table. Silent row loss is treated as a defect.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config

logger = logging.getLogger(__name__)

#: CAS uses the literal strings "Null" / "Unknown" for missing categoricals.
_MISSING_TOKENS = {"Null", "Unknown", "", None}


@dataclass
class ExclusionLog:
    """Running record of rows dropped at each stage of sample construction."""

    steps: list[tuple[str, int, int]] = field(default_factory=list)

    def record(self, label: str, before: int, after: int) -> None:
        self.steps.append((label, before - after, after))
        logger.info("%-46s dropped %6d, remaining %7d", label, before - after, after)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            self.steps, columns=["exclusion", "n_dropped", "n_remaining"]
        )


def _clean_categorical(series: pd.Series) -> pd.Series:
    """Replace CAS missing tokens with NaN and strip whitespace."""
    out = series.astype("string").str.strip()
    return out.where(~out.isin([t for t in _MISSING_TOKENS if t is not None]))


def _speed_band(limit: float) -> str | None:
    if pd.isna(limit):
        return None
    for low, high, label in config.SPEED_BANDS:
        if low <= limit <= high:
            return label
    return None


def _traffic_control(value: str | None) -> str | None:
    """Collapse traffic control.

    'Unknown' is retained as an explicit level rather than recoded to 'None'.
    It covers 27% of records, and treating that mass as "no control present"
    would bias the control coefficients toward the null.
    """
    if value is None or pd.isna(value):
        return "Unknown"
    if value == "Nil":
        return "None"
    if value in {"Give way", "Stop"}:
        return "Give way or stop"
    if value == "Traffic Signals":
        return "Signals"
    return "Other control"


def _road_character(value: str | None) -> str:
    if value is None or pd.isna(value) or value == "Nil":
        return "Nil"
    if value in {"Bridge", "Motorway ramp"}:
        return str(value)
    return "Other structure"


def _lane_category(lanes: float) -> str | None:
    if pd.isna(lanes) or lanes <= 0:
        return None
    if lanes <= 2:
        return "1-2 lanes"
    if lanes <= 4:
        return "3-4 lanes"
    return "5+ lanes"


def build_analysis_sample(
    raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (analysis_sample, exclusion_table).

    The primary sample is injury crashes only. See ``config.INJURY_LEVELS``
    for the rationale.
    """
    log = ExclusionLog()
    frame = raw.copy()
    n = len(frame)
    log.record(f"Starting extract {config.YEAR_MIN}-{config.YEAR_MAX}", n, n)

    # --- Outcome ------------------------------------------------------
    before = len(frame)
    frame = frame[frame["crashSeverity"].isin(config.INJURY_LEVELS)]
    log.record("Not an injury crash (non-injury excluded)", before, len(frame))

    frame["dsi"] = frame["crashSeverity"].isin(config.DSI_LEVELS).astype(int)

    # --- Exposures of interest ---------------------------------------
    frame["light"] = _clean_categorical(frame["light"])
    before = len(frame)
    frame = frame[frame["light"].notna()]
    log.record("Light condition unknown", before, len(frame))

    weather = _clean_categorical(frame["weatherA"])
    frame["weather"] = weather.map(config.WEATHER_MAP).astype("string")
    before = len(frame)
    frame = frame[frame["weather"].notna()]
    log.record("Weather unrecorded", before, len(frame))

    # --- Speed environment -------------------------------------------
    frame["speed_band"] = frame["speedLimit"].map(_speed_band).astype("string")
    before = len(frame)
    frame = frame[frame["speed_band"].notna()]
    log.record("Speed limit missing or out of range", before, len(frame))

    # --- Road environment covariates ---------------------------------
    frame["flat_hill"] = _clean_categorical(frame["flatHill"])
    before = len(frame)
    frame = frame[frame["flat_hill"].notna()]
    log.record("Terrain unrecorded", before, len(frame))

    frame["road_lane"] = _clean_categorical(frame["roadLane"])
    before = len(frame)
    frame = frame[frame["road_lane"].notna()]
    log.record("Road lane configuration unrecorded", before, len(frame))

    frame["lane_count"] = frame["NumberOfLanes"].map(_lane_category).astype("string")
    before = len(frame)
    frame = frame[frame["lane_count"].notna()]
    log.record("Lane count missing", before, len(frame))

    frame["traffic_control"] = (
        _clean_categorical(frame["trafficControl"]).map(_traffic_control).astype("string")
    )
    frame["road_character"] = (
        _clean_categorical(frame["roadCharacter"]).map(_road_character).astype("string")
    )

    street_light = _clean_categorical(frame["streetLight"])
    frame["street_light"] = street_light.fillna("Unrecorded").astype("string")

    frame["urban"] = _clean_categorical(frame["urban"])
    before = len(frame)
    frame = frame[frame["urban"].notna()]
    log.record("Urban/open classification missing", before, len(frame))

    frame["state_highway"] = np.where(
        frame["crashSHDescription"].eq("Yes"), "State highway", "Local road"
    )

    # holiday is NaN when the crash did not fall in a designated holiday
    # period, so NaN is informative rather than missing.
    frame["holiday_period"] = (
        frame["holiday"].fillna("Not holiday").astype("string")
    )

    # --- Road user mix -------------------------------------------------
    # These are strong severity determinants. Omitting them would load their
    # effect onto the environmental terms, since vulnerable road user crashes
    # are not evenly distributed across light and weather conditions.
    for name, columns in {
        "motorcycle_involved": ["motorcycle", "moped"],
        "pedestrian_involved": ["pedestrian"],
        "cyclist_involved": ["bicycle"],
        "heavy_vehicle_involved": ["truck", "bus", "schoolBus"],
    }.items():
        counts = frame[columns].fillna(0).sum(axis=1)
        frame[name] = (counts > 0).astype(int)

    # --- Context -------------------------------------------------------
    frame["region"] = _clean_categorical(frame["region"]).fillna("Unknown region")
    frame["year"] = frame["crashYear"].astype(int)
    before = len(frame)
    frame = frame[frame[config.CLUSTER_VAR].notna()]
    log.record("Territorial authority missing (clustering unit)", before, len(frame))

    keep = [
        "OBJECTID",
        "dsi",
        "crashSeverity",
        "fatalCount",
        "seriousInjuryCount",
        "minorInjuryCount",
        "light",
        "weather",
        "speed_band",
        "urban",
        "state_highway",
        "traffic_control",
        "road_character",
        "street_light",
        "flat_hill",
        "road_lane",
        "lane_count",
        "holiday_period",
        "motorcycle_involved",
        "pedestrian_involved",
        "cyclist_involved",
        "heavy_vehicle_involved",
        "year",
        "region",
        "tlaName",
        "x_nztm",
        "y_nztm",
    ]
    frame = frame[keep].reset_index(drop=True)

    # Order categoricals so the reference level is first.
    frame["light"] = pd.Categorical(
        frame["light"], categories=list(config.LIGHT_LEVELS), ordered=False
    )
    frame["weather"] = pd.Categorical(
        frame["weather"], categories=list(config.WEATHER_LEVELS), ordered=False
    )
    frame["speed_band"] = pd.Categorical(
        frame["speed_band"],
        categories=[label for _, _, label in config.SPEED_BANDS],
        ordered=False,
    )

    return frame, log.to_frame()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    config.ensure_dirs()
    raw = pd.read_parquet(config.RAW_PARQUET)
    sample, exclusions = build_analysis_sample(raw)
    sample.to_parquet(config.ANALYSIS_PARQUET, index=False)
    exclusions.to_csv(config.OUTPUTS / "table_s1_sample_derivation.csv", index=False)

    print(f"\nAnalysis sample: {len(sample):,} injury crashes")
    print(f"  DSI: {sample.dsi.sum():,} ({100 * sample.dsi.mean():.2f}%)")
    print(f"  Clusters (TLA): {sample[config.CLUSTER_VAR].nunique()}")


if __name__ == "__main__":
    main()
