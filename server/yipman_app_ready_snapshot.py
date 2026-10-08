from __future__ import annotations

"""App Ready snapshot contract for Yipman.

Heavy operational intelligence is computed after data changes, not while a
manager is opening a page.  This module owns the atomic snapshot envelope and
status contract; concrete builders may fill the sections incrementally before
promotion to READY.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable
import uuid


APP_READY_STAGES = (
    "PUBLISH",
    "PRECALCULATE",
    "PREANALYZE",
    "BUILD_SNAPSHOT",
    "APP_READY",
)

SNAPSHOT_SECTIONS = (
    "stock_flow",
    "quick_check",
    "ordering_regular",
    "ordering_promotion",
    "price_reg",
    "price_tpr_suggestions",
    "price_tpr_progress",
    "price_clearance",
    "inventory",
    "performance",
    "decision_intelligence",
)


@dataclass
class SnapshotBuild:
    build_id: str
    source_batch_id: str | None
    data_through: str | None
    stage: str = "PUBLISH"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    sections: dict[str, Any] = field(default_factory=dict)
    section_status: dict[str, str] = field(default_factory=dict)
    error: str | None = None


class AppReadySnapshotStore:
    """In-process atomic snapshot registry.

    A build is invisible to app readers until every required section is READY.
    Readers therefore continue using the previous complete snapshot while a
    new upload is being recalculated/analyzed.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._active: SnapshotBuild | None = None
        self._building: SnapshotBuild | None = None

    def begin(self, *, source_batch_id: str | None = None, data_through: str | None = None) -> SnapshotBuild:
        with self._lock:
            self._building = SnapshotBuild(
                build_id=str(uuid.uuid4()),
                source_batch_id=source_batch_id,
                data_through=data_through,
                section_status={name: "PENDING" for name in SNAPSHOT_SECTIONS},
            )
            return self._building

    def set_stage(self, stage: str) -> None:
        if stage not in APP_READY_STAGES:
            raise ValueError(f"Unknown App Ready stage: {stage}")
        with self._lock:
            if not self._building:
                raise RuntimeError("No App Ready build in progress")
            self._building.stage = stage

    def put_section(self, name: str, payload: Any) -> None:
        if name not in SNAPSHOT_SECTIONS:
            raise ValueError(f"Unknown App Ready section: {name}")
        with self._lock:
            if not self._building:
                raise RuntimeError("No App Ready build in progress")
            self._building.sections[name] = payload
            self._building.section_status[name] = "READY"

    def fail_section(self, name: str, error: str) -> None:
        with self._lock:
            if not self._building:
                raise RuntimeError("No App Ready build in progress")
            self._building.section_status[name] = "FAILED"
            self._building.error = error

    def promote(self) -> SnapshotBuild:
        with self._lock:
            if not self._building:
                raise RuntimeError("No App Ready build in progress")
            missing = [n for n in SNAPSHOT_SECTIONS if self._building.section_status.get(n) != "READY"]
            if missing:
                raise RuntimeError("Snapshot is not complete: " + ", ".join(missing))
            self._building.stage = "APP_READY"
            self._building.completed_at = datetime.now(timezone.utc).isoformat()
            self._active = self._building
            self._building = None
            return self._active

    def active(self) -> SnapshotBuild | None:
        with self._lock:
            return self._active

    def status(self) -> dict[str, Any]:
        with self._lock:
            current = self._building or self._active
            if current is None:
                return {"status": "NO_SNAPSHOT", "stage": None, "app_ready": False}
            ready = sum(1 for v in current.section_status.values() if v == "READY")
            return {
                "status": "APP_READY" if current is self._active else "BUILDING",
                "stage": current.stage,
                "app_ready": current is self._active,
                "build_id": current.build_id,
                "source_batch_id": current.source_batch_id,
                "data_through": current.data_through,
                "sections_ready": ready,
                "sections_total": len(SNAPSHOT_SECTIONS),
                "sections": dict(current.section_status),
                "started_at": current.started_at,
                "completed_at": current.completed_at,
                "error": current.error,
            }


APP_READY_SNAPSHOTS = AppReadySnapshotStore()


def build_app_ready_snapshot(
    builders: dict[str, Callable[[], Any]],
    *,
    source_batch_id: str | None = None,
    data_through: str | None = None,
) -> SnapshotBuild:
    """Run all registered builders and atomically promote only a complete build."""
    APP_READY_SNAPSHOTS.begin(source_batch_id=source_batch_id, data_through=data_through)
    APP_READY_SNAPSHOTS.set_stage("PRECALCULATE")
    for name in SNAPSHOT_SECTIONS:
        builder = builders.get(name)
        if builder is None:
            APP_READY_SNAPSHOTS.fail_section(name, "BUILDER_NOT_REGISTERED")
            raise RuntimeError(f"App Ready builder not registered: {name}")
        try:
            payload = builder()
            APP_READY_SNAPSHOTS.put_section(name, payload)
        except Exception as exc:
            APP_READY_SNAPSHOTS.fail_section(name, f"{type(exc).__name__}: {exc}")
            raise
    APP_READY_SNAPSHOTS.set_stage("BUILD_SNAPSHOT")
    return APP_READY_SNAPSHOTS.promote()
