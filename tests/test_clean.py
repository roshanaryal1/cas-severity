"""Smoke tests for sample construction invariants."""
from __future__ import annotations

import pandas as pd
import pytest

from cas_severity import clean, config


@pytest.fixture(scope="module")
def sample() -> pd.DataFrame:
    raw = pd.read_parquet(config.RAW_PARQUET)
    frame, _ = clean.build_analysis_sample(raw)
    return frame


def test_outcome_is_binary(sample: pd.DataFrame) -> None:
    assert set(sample["dsi"].unique()) <= {0, 1}


def test_no_non_injury_in_primary_sample(sample: pd.DataFrame) -> None:
    assert "Non-Injury Crash" not in set(sample["crashSeverity"])


def test_dsi_matches_severity_labels(sample: pd.DataFrame) -> None:
    derived = sample["crashSeverity"].isin(config.DSI_LEVELS).astype(int)
    assert (derived == sample["dsi"]).all()


def test_no_missing_in_model_covariates(sample: pd.DataFrame) -> None:
    covariates = [
        "light", "weather", "speed_band", "urban", "flat_hill",
        "road_lane", "lane_count", "traffic_control", "region",
    ]
    assert not sample[covariates].isna().any().any()


def test_unknown_light_excluded(sample: pd.DataFrame) -> None:
    assert "Unknown" not in set(sample["light"].astype(str))


def test_cluster_variable_populated(sample: pd.DataFrame) -> None:
    assert sample[config.CLUSTER_VAR].notna().all()
    assert sample[config.CLUSTER_VAR].nunique() > 50
