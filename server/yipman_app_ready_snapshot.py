from __future__ import annotations

"""Atomic App Ready snapshot store with durable shared generations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable
import time
import uuid

APP_READY_STAGES = ("PUBLISH", "PRECALCULATE", "PREANALYZE", "BUILD_SNAPSHOT", "APP_READY")
SNAPSHOT_SECTIONS = (
    "stock_flow", "quick_check", "ordering_regular", "ordering_promotion",
    "price_reg", "price_tpr_suggestions", "price_tpr_progress", "price_clearance",
    "inventory", "performance", "decision_intelligence",
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
    section_ms: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    build_ms: float | None = None


class AppReadySnapshotStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._active: SnapshotBuild | None = None
        self._building: SnapshotBuild | None = None

    def begin(self, *, source_batch_id=None, data_through=None) -> SnapshotBuild:
        with self._lock:
            self._building = SnapshotBuild(
                str(uuid.uuid4()), source_batch_id, data_through,
                section_status={n: "PENDING" for n in SNAPSHOT_SECTIONS},
            )
            return self._building

    def set_stage(self, stage: str) -> None:
        if stage not in APP_READY_STAGES:
            raise ValueError(f"Unknown App Ready stage: {stage}")
        with self._lock:
            if not self._building:
                raise RuntimeError("No App Ready build in progress")
            self._building.stage = stage

    def put_section(self, name: str, payload: Any, elapsed_ms: float | None = None) -> None:
        if name not in SNAPSHOT_SECTIONS:
            raise ValueError(f"Unknown App Ready section: {name}")
        with self._lock:
            if not self._building:
                raise RuntimeError("No App Ready build in progress")
            self._building.sections[name] = payload
            self._building.section_status[name] = "READY"
            if elapsed_ms is not None:
                self._building.section_ms[name] = round(float(elapsed_ms), 1)

    def fail_section(self, name: str, error: str, elapsed_ms: float | None = None) -> None:
        with self._lock:
            if not self._building:
                raise RuntimeError("No App Ready build in progress")
            self._building.section_status[name] = "FAILED"
            self._building.error = error
            if elapsed_ms is not None:
                self._building.section_ms[name] = round(float(elapsed_ms), 1)

    def candidate_for_promotion(self) -> SnapshotBuild:
        """Finalize metadata but do not expose the generation to readers yet."""
        with self._lock:
            if not self._building:
                raise RuntimeError("No App Ready build in progress")
            missing = [n for n in SNAPSHOT_SECTIONS if self._building.section_status.get(n) != "READY"]
            if missing:
                raise RuntimeError("Snapshot is not complete: " + ", ".join(missing))
            self._building.stage = "APP_READY"
            self._building.completed_at = datetime.now(timezone.utc).isoformat()
            try:
                a = datetime.fromisoformat(self._building.started_at)
                b = datetime.fromisoformat(self._building.completed_at)
                self._building.build_ms = round((b - a).total_seconds() * 1000, 1)
            except Exception:
                pass
            return self._building

    def activate(self, expected_build_id: str) -> SnapshotBuild:
        """Flip the hot-cache pointer only after durable activation succeeds."""
        with self._lock:
            if not self._building or self._building.build_id != expected_build_id:
                raise RuntimeError("App Ready build changed before activation")
            self._active = self._building
            self._building = None
            return self._active

    def hydrate(self, snapshot: SnapshotBuild) -> SnapshotBuild:
        """Install an already-complete durable generation as the hot cache."""
        missing = [n for n in SNAPSHOT_SECTIONS if snapshot.section_status.get(n) != "READY"]
        if snapshot.stage != "APP_READY" or missing:
            raise RuntimeError("Refusing to hydrate incomplete App Ready snapshot")
        with self._lock:
            self._active = snapshot
            return snapshot

    def active(self):
        with self._lock:
            return self._active

    def status(self) -> dict[str, Any]:
        with self._lock:
            current = self._building or self._active
            if current is None:
                return {"status": "NO_SNAPSHOT", "stage": None, "app_ready": False, "active_build_id": None}
            ready = sum(v == "READY" for v in current.section_status.values())
            active = self._active
            return {
                "status": "APP_READY" if current is active else "BUILDING",
                "stage": current.stage,
                "app_ready": current is active,
                "build_id": current.build_id,
                "active_build_id": active.build_id if active else None,
                "active_data_through": active.data_through if active else None,
                "source_batch_id": current.source_batch_id,
                "data_through": current.data_through,
                "sections_ready": ready,
                "sections_total": len(SNAPSHOT_SECTIONS),
                "progress_pct": round(100 * ready / len(SNAPSHOT_SECTIONS), 1),
                "sections": dict(current.section_status),
                "section_ms": dict(current.section_ms),
                "started_at": current.started_at,
                "completed_at": current.completed_at,
                "build_ms": current.build_ms,
                "error": current.error,
            }


APP_READY_SNAPSHOTS = AppReadySnapshotStore()


def build_app_ready_snapshot(builders: dict[str, Callable[[], Any]], *, source_batch_id=None, data_through=None) -> SnapshotBuild:
    APP_READY_SNAPSHOTS.begin(source_batch_id=source_batch_id, data_through=data_through)
    APP_READY_SNAPSHOTS.set_stage("PRECALCULATE")
    for name in SNAPSHOT_SECTIONS:
        builder = builders.get(name)
        if builder is None:
            APP_READY_SNAPSHOTS.fail_section(name, "BUILDER_NOT_REGISTERED")
            raise RuntimeError(f"App Ready builder not registered: {name}")
        started = time.perf_counter()
        try:
            APP_READY_SNAPSHOTS.put_section(name, builder(), (time.perf_counter() - started) * 1000)
        except Exception as exc:
            APP_READY_SNAPSHOTS.fail_section(name, f"{type(exc).__name__}: {exc}", (time.perf_counter() - started) * 1000)
            raise
    APP_READY_SNAPSHOTS.set_stage("PREANALYZE")
    APP_READY_SNAPSHOTS.set_stage("BUILD_SNAPSHOT")

    candidate = APP_READY_SNAPSHOTS.candidate_for_promotion()
    # Critical ordering: durable generation + ACTIVE pointer commit first, then
    # expose it through this process's hot cache. A persistence failure leaves
    # the previous complete generation active everywhere.
    from yipman_app_ready_persistence import persist_complete_snapshot
    persist_complete_snapshot(candidate)
    return APP_READY_SNAPSHOTS.activate(candidate.build_id)
