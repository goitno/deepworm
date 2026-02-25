"""Tests for deepworm.progress."""

import time

import pytest

from deepworm.progress import (
    ProgressSnapshot,
    ProgressTracker,
    ResearchStage,
    StageInfo,
    format_eta,
    format_progress_bar,
)


class TestResearchStage:
    def test_all_stages_have_labels(self):
        for stage in ResearchStage:
            assert stage.label  # Non-empty label

    def test_label_values(self):
        assert ResearchStage.SEARCHING.label == "Searching Sources"
        assert ResearchStage.COMPLETE.label == "Complete"
        assert ResearchStage.FAILED.label == "Failed"


class TestStageInfo:
    def test_duration(self):
        info = StageInfo(stage=ResearchStage.SEARCHING, started_at=time.time() - 5)
        assert info.duration >= 4.9

    def test_completed_duration(self):
        now = time.time()
        info = StageInfo(
            stage=ResearchStage.SEARCHING,
            started_at=now - 10,
            completed_at=now - 5,
        )
        assert abs(info.duration - 5.0) < 0.1

    def test_progress_no_items(self):
        info = StageInfo(stage=ResearchStage.SEARCHING, started_at=time.time())
        assert info.progress == 0.0

    def test_progress_with_items(self):
        info = StageInfo(
            stage=ResearchStage.SEARCHING,
            started_at=time.time(),
            items_total=10,
            items_done=5,
        )
        assert info.progress == 0.5

    def test_progress_complete(self):
        info = StageInfo(
            stage=ResearchStage.SEARCHING,
            started_at=time.time(),
            completed_at=time.time(),
        )
        assert info.progress == 1.0


class TestProgressTracker:
    def test_start(self):
        tracker = ProgressTracker()
        tracker.start()
        assert tracker.elapsed > 0
        snap = tracker.snapshot
        assert snap.stage == ResearchStage.INITIALIZING

    def test_enter_stage(self):
        tracker = ProgressTracker()
        tracker.start()
        tracker.enter_stage(ResearchStage.SEARCHING, total_items=5)
        snap = tracker.snapshot
        assert snap.stage == ResearchStage.SEARCHING

    def test_advance(self):
        tracker = ProgressTracker()
        tracker.start()
        tracker.enter_stage(ResearchStage.SEARCHING, total_items=10)
        tracker.advance("Processing item 1")
        tracker.advance("Processing item 2")
        snap = tracker.snapshot
        assert snap.stage_percent == 20.0  # 2/10

    def test_complete(self):
        tracker = ProgressTracker()
        tracker.start()
        tracker.complete()
        assert tracker.is_complete
        snap = tracker.snapshot
        assert snap.overall_percent == 100.0
        assert snap.stage == ResearchStage.COMPLETE

    def test_fail(self):
        tracker = ProgressTracker()
        tracker.start()
        tracker.fail("Something went wrong")
        assert tracker.error == "Something went wrong"
        snap = tracker.snapshot
        assert snap.stage == ResearchStage.FAILED

    def test_callback(self):
        received = []
        tracker = ProgressTracker()
        tracker.on_progress(lambda snap: received.append(snap))
        tracker.start()
        tracker.enter_stage(ResearchStage.SEARCHING)
        assert len(received) >= 2  # start + enter_stage

    def test_add_sources(self):
        tracker = ProgressTracker()
        tracker.start()
        tracker.add_sources(found=5, analyzed=3)
        snap = tracker.snapshot
        assert snap.sources_found == 5
        assert snap.sources_analyzed == 3

    def test_stage_durations(self):
        tracker = ProgressTracker()
        tracker.start()
        tracker.enter_stage(ResearchStage.SEARCHING)
        tracker.enter_stage(ResearchStage.ANALYZING)
        durations = tracker.stage_durations
        assert "initializing" in durations
        assert "searching" in durations

    def test_callback_error_handled(self):
        """Callback errors should not break tracking."""
        def bad_callback(snap):
            raise RuntimeError("oops")

        tracker = ProgressTracker()
        tracker.on_progress(bad_callback)
        tracker.start()  # Should not raise
        tracker.enter_stage(ResearchStage.SEARCHING)

    def test_overall_progress_increases(self):
        tracker = ProgressTracker()
        tracker.start()
        p1 = tracker.snapshot.overall_percent
        tracker.enter_stage(ResearchStage.PLANNING)
        tracker.enter_stage(ResearchStage.SEARCHING, total_items=2)
        tracker.advance()
        p2 = tracker.snapshot.overall_percent
        assert p2 > p1


class TestProgressSnapshot:
    def test_to_dict(self):
        snap = ProgressSnapshot(
            stage=ResearchStage.SEARCHING,
            overall_percent=45.3,
            stage_percent=60.0,
            elapsed_seconds=12.5,
            eta_seconds=15.0,
            message="Searching...",
            sources_found=5,
            sources_analyzed=2,
        )
        d = snap.to_dict()
        assert d["stage"] == "searching"
        assert d["stage_label"] == "Searching Sources"
        assert d["overall_percent"] == 45.3
        assert d["eta_seconds"] == 15.0

    def test_to_dict_no_eta(self):
        snap = ProgressSnapshot(
            stage=ResearchStage.INITIALIZING,
            overall_percent=0.0,
            stage_percent=0.0,
            elapsed_seconds=0.0,
            eta_seconds=None,
            message="Starting",
            sources_found=0,
            sources_analyzed=0,
        )
        d = snap.to_dict()
        assert d["eta_seconds"] is None


class TestFormatProgressBar:
    def test_zero(self):
        bar = format_progress_bar(0)
        assert "0%" in bar
        assert "█" not in bar

    def test_full(self):
        bar = format_progress_bar(100)
        assert "100%" in bar
        assert "░" not in bar

    def test_half(self):
        bar = format_progress_bar(50, width=20)
        assert "50%" in bar

    def test_custom_width(self):
        bar = format_progress_bar(50, width=10)
        # 5 filled + 5 empty
        assert bar.count("█") == 5
        assert bar.count("░") == 5


class TestFormatEta:
    def test_none(self):
        assert format_eta(None) == "unknown"

    def test_negative(self):
        assert format_eta(-1) == "any moment"

    def test_seconds(self):
        assert format_eta(30) == "30s"

    def test_minutes(self):
        result = format_eta(90)
        assert "m" in result

    def test_hours(self):
        result = format_eta(3700)
        assert "1h" in result
