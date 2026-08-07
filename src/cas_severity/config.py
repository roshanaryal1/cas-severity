"""Configuration constants for the CAS injury-severity analysis.

All tunable analysis parameters live here so that the extraction, cleaning and
modelling stages share a single source of truth. Nothing in this module reads
from the network or the filesystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

# --------------------------------------------------------------------------
# Data source
# --------------------------------------------------------------------------

#: NZTA public Crash Analysis System ArcGIS FeatureServer layer.
#: Licensed CC-BY 4.0. Attribution: NZ Transport Agency Waka Kotahi.
CAS_LAYER_URL: Final[str] = (
    "https://services.arcgis.com/CXBb7LAjgIIdcsPt/ArcGIS/rest/services"
    "/CAS_Data_Public/FeatureServer/0"
)

#: Server-side cap on records per query response. Confirmed from layer metadata.
PAGE_SIZE: Final[int] = 2000

#: Coordinate reference system of the source geometry (NZGD2000 / NZTM 2000).
SOURCE_EPSG: Final[int] = 2193

#: Analysis window. 2010 chosen as the start to avoid the pre-2010 speed-limit
#: and reporting-practice regime; 2024 is the last year with substantially
#: complete processing (non-injury crashes lag by up to seven months).
YEAR_MIN: Final[int] = 2010
YEAR_MAX: Final[int] = 2024

#: Fields pulled from the service. Kept explicit rather than "*" so that a
#: schema change upstream surfaces as a hard failure instead of silent drift.
FIELDS: Final[tuple[str, ...]] = (
    "OBJECTID",
    # Outcome
    "crashSeverity",
    "fatalCount",
    "seriousInjuryCount",
    "minorInjuryCount",
    # Exposure variables of interest
    "light",
    "weatherA",
    "weatherB",
    # Road and speed environment
    "speedLimit",
    "temporarySpeedLimit",
    "advisorySpeed",
    "urban",
    "intersection",
    "trafficControl",
    "streetLight",
    "roadCharacter",
    "roadLane",
    "roadSurface",
    "flatHill",
    "NumberOfLanes",
    "crashSHDescription",
    "roadworks",
    # Road user mix
    "motorcycle",
    "moped",
    "bicycle",
    "pedestrian",
    "truck",
    "bus",
    "schoolBus",
    "carStationWagon",
    "suv",
    "vanOrUtility",
    "parkedVehicle",
    # Context
    "crashYear",
    "holiday",
    "region",
    "tlaName",
)

# --------------------------------------------------------------------------
# Outcome definition
# --------------------------------------------------------------------------

#: Severity levels treated as "death or serious injury".
DSI_LEVELS: Final[frozenset[str]] = frozenset({"Fatal Crash", "Serious Crash"})

#: Severity levels retained in the PRIMARY analysis sample.
#:
#: Non-injury crashes are excluded. They are the most severely and most
#: differentially under-reported category in CAS, and their reporting
#: propensity plausibly varies with the very conditions under study (a driver
#: is more likely to report a wet-weather nose-to-tail than a dry-weather one
#: because of insurance liability). Including them lets reporting bias drive
#: the headline estimate. Restricting to injury crashes trades sample size for
#: a denominator that is defensible.
INJURY_LEVELS: Final[frozenset[str]] = frozenset(
    {"Fatal Crash", "Serious Crash", "Minor Crash"}
)

# --------------------------------------------------------------------------
# Categorical recoding
# --------------------------------------------------------------------------

#: Values in `light`. "Unknown" is dropped (roughly 1.8% of records).
LIGHT_LEVELS: Final[tuple[str, ...]] = ("Bright sun", "Overcast", "Twilight", "Dark")
LIGHT_REFERENCE: Final[str] = "Bright sun"

#: Collapsed `weatherA`. Snow and Hail or Sleet are pooled into a single
#: frozen-precipitation category: together they are under 0.25% of records and
#: separate estimation is not supportable.
WEATHER_MAP: Final[dict[str, str]] = {
    "Fine": "Fine",
    "Light rain": "Light rain",
    "Heavy rain": "Heavy rain",
    "Mist or Fog": "Mist or fog",
    "Snow": "Snow or hail",
    "Hail or Sleet": "Snow or hail",
}
WEATHER_LEVELS: Final[tuple[str, ...]] = (
    "Fine",
    "Light rain",
    "Heavy rain",
    "Mist or fog",
    "Snow or hail",
)
WEATHER_REFERENCE: Final[str] = "Fine"

#: Posted speed limit collapsed into a speed *environment*. The 2010-2024
#: window spans several speed-management regimes, so exact limits are noisy;
#: bands are stable and map onto the physics of injury tolerance.
SPEED_BANDS: Final[tuple[tuple[int, int, str], ...]] = (
    (0, 50, "<=50 km/h"),
    (51, 80, "60-80 km/h"),
    (81, 200, ">=90 km/h"),
)
SPEED_REFERENCE: Final[str] = "<=50 km/h"

#: Traffic control collapsed. Raw CAS has many sparse levels.
TRAFFIC_CONTROL_MAP: Final[dict[str, str]] = {
    "Nil": "None",
    "Give way": "Give way or stop",
    "Stop": "Give way or stop",
    "Traffic Signals": "Signals",
    "Pedestrian crossing": "Other control",
    "School patrol": "Other control",
    "Traffic Officer": "Other control",
    "Unknown": "None",
}
TRAFFIC_CONTROL_REFERENCE: Final[str] = "None"

#: Road alignment / terrain.
FLAT_HILL_REFERENCE: Final[str] = "Flat"

# --------------------------------------------------------------------------
# Modelling
# --------------------------------------------------------------------------

#: Standard errors are clustered on Territorial Authority. Crashes within the
#: same TLA share road design standards, enforcement intensity and reporting
#: practice, so the independence assumption fails at that level.
CLUSTER_VAR: Final[str] = "tlaName"

#: Confidence level for reported intervals.
ALPHA: Final[float] = 0.05

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DATA_RAW: Final[Path] = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM: Final[Path] = PROJECT_ROOT / "data" / "interim"
OUTPUTS: Final[Path] = PROJECT_ROOT / "outputs"

RAW_PARQUET: Final[Path] = DATA_RAW / "cas_raw.parquet"
ANALYSIS_PARQUET: Final[Path] = DATA_INTERIM / "analysis_sample.parquet"


def ensure_dirs() -> None:
    """Create the project's data and output directories if absent."""
    for path in (DATA_RAW, DATA_INTERIM, OUTPUTS):
        path.mkdir(parents=True, exist_ok=True)
