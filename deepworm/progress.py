"""Research progress tracking.

Provides real-time progress tracking for research operations with
stage-based progress, ETA estimation, and callback support.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ResearchStage(str, Enum):
    """Stages of a research operation."""

    INITIALIZING = "initializing"
    PLANNING = "planning"
    SEARCHING = "searching"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    WRITING = "writing"
    FORMATTING = "formatting"
    COMPLETE = "complete"
    FAILED = "failed"

    @property
    def label(self) -> str:
        """Human-readable label."""
        labels = {
            "initializing": "Initializing",
            "planning": "Planning Research",
            "searching": "Searching Sources",
            "fetching": "Fetching Content",
            "analyzing": "Analyzing Data",
            "synthesizing": "Synthesizing Findings",
            "writing": "Writing Report",
            "formatting": "Formatting Output",
            "complete": "Complete",
            "failed": "Failed",
        }
        return labels.get(self.value, self.value.title())


# Default stage weights for progress percentage
_STAGE_WEIGHTS: dict[ResearchStage, float] = {
    ResearchStage.INITIALIZING: 0.02,
    ResearchStage.PLANNING: 0.08,
    ResearchStage.SEARCHING: 0.20,
    ResearchStage.FETCHING: 0.20,
    ResearchStage.ANALYZING: 0.20,
    ResearchStage.SYNTHESIZING: 0.15,
    ResearchStage.WRITING: 0.10,
    ResearchStage.FORMATTING: 0.05,
}


@dataclass
class StageInfo:
    """Information about a completed or in-progress stage."""

    stage: ResearchStage
    started_at: float
    completed_at: Optional[float] = None
    items_total: int = 0
    items_done: int = 0
    message: str = ""

    @property
    def duration(self) -> float:
        """Duration of this stage in seconds."""
        end = self.completed_at or time.time()
        return end - self.started_at

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def progress(self) -> float:
        """Progress within this stage (0.0-1.0)."""
        if self.is_complete:
            return 1.0
        if self.items_total <= 0:
            return 0.0
        return min(1.0, self.items_done / self.items_total)


@dataclass
class ProgressSnapshot:
    """A snapshot of research progress at a point in time."""

    stage: ResearchStage
    overall_percent: float  # 0.0 - 100.0
    stage_percent: float  # 0.0 - 100.0
    elapsed_seconds: float
    eta_seconds: Optional[float]
    message: str
    sources_found: int
    sources_analyzed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "stage_label": self.stage.label,
            "overall_percent": round(self.overall_percent, 1),
            "stage_percent": round(self.stage_percent, 1),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "eta_seconds": round(self.eta_seconds, 1) if self.eta_seconds else None,
            "message": self.message,
            "sources_found": self.sources_found,
            "sources_analyzed": self.sources_analyzed,
        }


ProgressCallback = Callable[[ProgressSnapshot], None]


class ProgressTracker:
    """Track progress of a research operation.

    Usage:
        tracker = ProgressTracker()
        tracker.on_progress(my_callback)
        tracker.start()
        tracker.enter_stage(ResearchStage.SEARCHING, total_items=10)
        for url in urls:
            tracker.advance("Searching: {url}")
        tracker.enter_stage(ResearchStage.ANALYZING)
        tracker.complete()
    """

    def __init__(self) -> None:
        self._started_at: float = 0.0
        self._current_stage: Optional[ResearchStage] = None
        self._stages: dict[ResearchStage, StageInfo] = {}
        self._callbacks: list[ProgressCallback] = []
        self._sources_found: int = 0
        self._sources_analyzed: int = 0
        self._is_complete: bool = False
        self._error: Optional[str] = None

    def on_progress(self, callback: ProgressCallback) -> None:
        """Register a progress callback."""
        self._callbacks.append(callback)

    def start(self) -> None:
        """Start tracking."""
        self._started_at = time.time()
        self.enter_stage(ResearchStage.INITIALIZING)

    def enter_stage(
        self,
        stage: ResearchStage,
        total_items: int = 0,
        message: str = "",
    ) -> None:
        """Enter a new research stage."""
        now = time.time()

        # Complete previous stage
        if self._current_stage and self._current_stage in self._stages:
            self._stages[self._current_stage].completed_at = now

        self._current_stage = stage
        self._stages[stage] = StageInfo(
            stage=stage,
            started_at=now,
            items_total=total_items,
            message=message or stage.label,
        )
        self._notify()

    def advance(self, message: str = "", items: int = 1) -> None:
        """Advance progress within the current stage."""
        if self._current_stage and self._current_stage in self._stages:
            info = self._stages[self._current_stage]
            info.items_done += items
            if message:
                info.message = message
            self._notify()

    def add_sources(self, found: int = 0, analyzed: int = 0) -> None:
        """Update source counts."""
        self._sources_found += found
        self._sources_analyzed += analyzed

    def complete(self, message: str = "Research complete") -> None:
        """Mark research as complete."""
        now = time.time()
        if self._current_stage and self._current_stage in self._stages:
            self._stages[self._current_stage].completed_at = now
        self._current_stage = ResearchStage.COMPLETE
        self._stages[ResearchStage.COMPLETE] = StageInfo(
            stage=ResearchStage.COMPLETE,
            started_at=now,
            completed_at=now,
            message=message,
        )
        self._is_complete = True
        self._notify()

    def fail(self, error: str) -> None:
        """Mark research as failed."""
        now = time.time()
        if self._current_stage and self._current_stage in self._stages:
            self._stages[self._current_stage].completed_at = now
        self._current_stage = ResearchStage.FAILED
        self._stages[ResearchStage.FAILED] = StageInfo(
            stage=ResearchStage.FAILED,
            started_at=now,
            completed_at=now,
            message=error,
        )
        self._error = error
        self._notify()

    @property
    def snapshot(self) -> ProgressSnapshot:
        """Get current progress snapshot."""
        elapsed = time.time() - self._started_at if self._started_at else 0.0
        stage = self._current_stage or ResearchStage.INITIALIZING

        overall = self._calculate_overall_percent()
        stage_pct = 0.0
        message = stage.label

        if stage in self._stages:
            stage_pct = self._stages[stage].progress * 100
            message = self._stages[stage].message

        eta = self._estimate_eta(elapsed, overall)

        return ProgressSnapshot(
            stage=stage,
            overall_percent=overall,
            stage_percent=stage_pct,
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            message=message,
            sources_found=self._sources_found,
            sources_analyzed=self._sources_analyzed,
        )

    @property
    def elapsed(self) -> float:
        """Total elapsed time in seconds."""
        if not self._started_at:
            return 0.0
        return time.time() - self._started_at

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def stage_durations(self) -> dict[str, float]:
        """Get duration of each completed stage."""
        return {
            stage.value: info.duration
            for stage, info in self._stages.items()
            if info.is_complete
        }

    def _calculate_overall_percent(self) -> float:
        """Calculate overall progress percentage."""
        if self._is_complete:
            return 100.0

        total = 0.0
        stage_order = list(_STAGE_WEIGHTS.keys())

        for stage in stage_order:
            weight = _STAGE_WEIGHTS.get(stage, 0.0)
            if stage in self._stages:
                info = self._stages[stage]
                if info.is_complete:
                    total += weight * 100
                elif stage == self._current_stage:
                    total += weight * info.progress * 100

        return min(99.9, total)

    def _estimate_eta(self, elapsed: float, percent: float) -> Optional[float]:
        """Estimate time remaining."""
        if percent <= 0 or elapsed <= 0:
            return None
        if percent >= 100:
            return 0.0
        rate = percent / elapsed
        remaining = (100 - percent) / rate
        return remaining

    def _notify(self) -> None:
        """Notify all callbacks with current snapshot."""
        snap = self.snapshot
        for callback in self._callbacks:
            try:
                callback(snap)
            except Exception:
                pass  # Don't let callback errors break tracking


def format_progress_bar(percent: float, width: int = 30) -> str:
    """Format a text-based progress bar.

    Args:
        percent: Completion percentage (0-100).
        width: Bar width in characters.

    Returns:
        Formatted progress bar string, e.g. "[████████░░░░░░░] 53%"
    """
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {percent:.0f}%"


def format_eta(seconds: Optional[float]) -> str:
    """Format ETA seconds to human-readable string."""
    if seconds is None:
        return "unknown"
    if seconds < 0:
        return "any moment"
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.0f}m {seconds % 60:.0f}s"
    hours = minutes / 60
    return f"{hours:.0f}h {minutes % 60:.0f}m"
