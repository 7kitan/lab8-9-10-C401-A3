"""
Kiểm tra freshness từ manifest pipeline (SLA đơn giản theo giờ).

TODO Sinh viên mở rộng: đọc watermark DB, so sánh với clock batch, v.v.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Cho phép "2026-04-10T08:00:00" không có timezone
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def check_manifest_freshness(
    manifest_path: Path,
    *,
    sla_hours: float = 24.0,
    now: datetime | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Trả về ("PASS" | "WARN" | "FAIL", detail dict).

    Đọc trường `latest_exported_at` hoặc max exported_at trong cleaned summary.
    """
    now = now or datetime.now(timezone.utc)
    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    ts_raw = data.get("latest_exported_at") or data.get("run_timestamp")
    dt = parse_iso(str(ts_raw)) if ts_raw else None
    if dt is None:
        return "WARN", {"reason": "no_timestamp_in_manifest", "manifest": data}

    age_hours = (now - dt).total_seconds() / 3600.0
    detail = {
        "latest_exported_at": ts_raw,
        "age_hours": round(age_hours, 3),
        "sla_hours": sla_hours,
    }
    if age_hours <= sla_hours:
        return "PASS", detail
    return "FAIL", {**detail, "reason": "freshness_sla_exceeded"}


def check_ingest_publish_lag(
    manifest_path: Path,
    *,
    lag_warn_hours: float = 12.0,
) -> Tuple[str, Dict[str, Any]]:
    """
    TODO Sinh viên mở rộng: đọc watermark DB, so sánh với clock batch, v.v.

    Đo lag giữa thời điểm data được export (ingest boundary)
    và thời điểm pipeline chạy (publish boundary).
    Trả về ("OK" | "WARN", detail).
    """
    if not manifest_path.is_file():
        return "FAIL", {"reason": "manifest_missing", "path": str(manifest_path)}

    data: Dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    exported = parse_iso(str(data.get("latest_exported_at", "")))
    run_ts = parse_iso(str(data.get("run_timestamp", "")))

    if not exported or not run_ts:
        return "WARN", {
            "reason": "missing_timestamps_for_lag",
            "latest_exported_at": data.get("latest_exported_at"),
            "run_timestamp": data.get("run_timestamp"),
        }

    lag_hours = (run_ts - exported).total_seconds() / 3600.0
    detail: Dict[str, Any] = {
        "latest_exported_at": data.get("latest_exported_at"),
        "run_timestamp": data.get("run_timestamp"),
        "ingest_publish_lag_hours": round(lag_hours, 3),
        "lag_warn_hours": lag_warn_hours,
    }
    if lag_hours < 0:
        return "WARN", {**detail, "reason": "exported_at_after_run_timestamp"}
    if lag_hours > lag_warn_hours:
        return "WARN", {**detail, "reason": "high_ingest_publish_lag"}
    return "OK", detail
