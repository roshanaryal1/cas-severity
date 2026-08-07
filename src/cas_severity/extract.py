"""Extraction of NZTA Crash Analysis System records from the ArcGIS FeatureServer.

The service caps responses at 2000 features, so a full national pull for the
analysis window requires several hundred paged requests. This module handles
pagination, transient failure, and caching to Parquet so that the download is
performed once.

Data source: NZ Transport Agency Waka Kotahi, Crash Analysis System (CAS),
licensed CC-BY 4.0.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterator

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

logger = logging.getLogger(__name__)

_TRANSIENT_STATUS = (429, 500, 502, 503, 504)


def _build_session(pool_size: int) -> requests.Session:
    """Return a session with connection pooling and transport-level retries."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=_TRANSIENT_STATUS,
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry, pool_connections=pool_size, pool_maxsize=pool_size
    )
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "cas-severity-research/1.0"})
    return session


def _where_clause() -> str:
    return (
        f"crashYear >= {config.YEAR_MIN} AND crashYear <= {config.YEAR_MAX}"
    )


def get_total_count(session: requests.Session, timeout: int = 120) -> int:
    """Return the number of features matching the analysis window.

    Raises:
        RuntimeError: if the service returns an error payload.
    """
    response = session.get(
        f"{config.CAS_LAYER_URL}/query",
        params={
            "where": _where_clause(),
            "returnCountOnly": "true",
            "f": "json",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"ArcGIS error on count query: {payload['error']}")
    return int(payload["count"])


def _fetch_page(
    session: requests.Session, offset: int, timeout: int
) -> list[dict[str, Any]]:
    """Fetch a single page of features starting at ``offset``.

    Returns a list of flat attribute dicts with ``x``/``y`` geometry appended.
    Ordering by OBJECTID is required: ArcGIS pagination is undefined without a
    stable sort, and omitting it silently yields duplicate and missing rows.
    """
    params = {
        "where": _where_clause(),
        "outFields": ",".join(config.FIELDS),
        "orderByFields": "OBJECTID ASC",
        "resultOffset": offset,
        "resultRecordCount": config.PAGE_SIZE,
        "returnGeometry": "true",
        "outSR": config.SOURCE_EPSG,
        "f": "json",
    }
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = session.get(
                f"{config.CAS_LAYER_URL}/query", params=params, timeout=timeout
            )
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise RuntimeError(payload["error"])
            rows: list[dict[str, Any]] = []
            for feature in payload.get("features", []):
                record = dict(feature["attributes"])
                geometry = feature.get("geometry") or {}
                record["x_nztm"] = geometry.get("x")
                record["y_nztm"] = geometry.get("y")
                rows.append(record)
            return rows
        except Exception as exc:  # noqa: BLE001 - deliberately broad, retried
            last_error = exc
            sleep_for = 2.0 * (attempt + 1)
            logger.warning(
                "offset=%d attempt=%d failed (%s); retrying in %.1fs",
                offset,
                attempt + 1,
                exc,
                sleep_for,
            )
            time.sleep(sleep_for)
    raise RuntimeError(f"offset={offset} failed after retries") from last_error


def _offsets(total: int) -> Iterator[int]:
    yield from range(0, total, config.PAGE_SIZE)


def download(
    *,
    force: bool = False,
    max_workers: int = 6,
    timeout: int = 180,
) -> pd.DataFrame:
    """Download the CAS analysis window, caching to Parquet.

    Args:
        force: re-download even if the cache file exists.
        max_workers: concurrent requests. Kept modest to stay well inside
            the public service's fair-use envelope.
        timeout: per-request timeout in seconds.

    Returns:
        DataFrame of raw CAS attributes plus ``x_nztm`` / ``y_nztm``.

    Raises:
        RuntimeError: if the row count returned does not match the count the
            service reports, which indicates dropped or duplicated pages.
    """
    config.ensure_dirs()

    if config.RAW_PARQUET.exists() and not force:
        logger.info("Using cached extract at %s", config.RAW_PARQUET)
        return pd.read_parquet(config.RAW_PARQUET)

    session = _build_session(pool_size=max_workers)
    total = get_total_count(session, timeout=timeout)
    logger.info(
        "Service reports %d crashes for %d-%d; fetching in %d pages",
        total,
        config.YEAR_MIN,
        config.YEAR_MAX,
        -(-total // config.PAGE_SIZE),
    )

    frames: list[dict[str, Any]] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_page, session, offset, timeout): offset
            for offset in _offsets(total)
        }
        for future in as_completed(futures):
            frames.extend(future.result())
            completed += 1
            if completed % 25 == 0:
                logger.info("  %d pages done (%d rows)", completed, len(frames))

    frame = pd.DataFrame.from_records(frames)

    if len(frame) != total:
        raise RuntimeError(
            f"Row count mismatch: fetched {len(frame)}, service reported {total}. "
            "Pagination is unreliable; re-run with fewer workers."
        )
    duplicates = int(frame["OBJECTID"].duplicated().sum())
    if duplicates:
        raise RuntimeError(f"{duplicates} duplicate OBJECTIDs in extract")

    frame = frame.sort_values("OBJECTID").reset_index(drop=True)
    frame.to_parquet(config.RAW_PARQUET, index=False)
    logger.info("Wrote %d rows to %s", len(frame), config.RAW_PARQUET)
    return frame


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    frame = download()
    print(f"Extracted {len(frame):,} crashes, {frame.shape[1]} columns")


if __name__ == "__main__":
    main()
