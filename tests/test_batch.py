"""Tests for batch research module."""

import os
import tempfile

from deepworm.batch import (
    BatchConfig,
    BatchResult,
    BatchStatus,
    BatchTask,
    batch_from_file,
    create_batch,
    run_batch,
)


class TestBatchStatus:
    def test_values(self):
        assert BatchStatus.PENDING == "pending"
        assert BatchStatus.RUNNING == "running"
        assert BatchStatus.COMPLETED == "completed"
        assert BatchStatus.FAILED == "failed"
        assert BatchStatus.SKIPPED == "skipped"


class TestBatchTask:
    def test_to_dict(self):
        task = BatchTask(topic="AI research", id=1, status=BatchStatus.COMPLETED, duration=5.5)
        d = task.to_dict()
        assert d["id"] == 1
        assert d["topic"] == "AI research"
        assert d["status"] == "completed"
        assert d["duration"] == 5.5

    def test_to_dict_with_error(self):
        task = BatchTask(topic="test", id=1, error="Failed")
        d = task.to_dict()
        assert d["error"] == "Failed"

    def test_to_dict_with_result(self):
        task = BatchTask(topic="test", id=1, result="Report content")
        d = task.to_dict()
        assert d["result_length"] == len("Report content")

    def test_defaults(self):
        task = BatchTask(topic="test")
        assert task.status == BatchStatus.PENDING
        assert task.result == ""
        assert task.error == ""


class TestBatchResult:
    def test_completed(self):
        tasks = [
            BatchTask("a", 1, BatchStatus.COMPLETED),
            BatchTask("b", 2, BatchStatus.FAILED),
            BatchTask("c", 3, BatchStatus.COMPLETED),
        ]
        result = BatchResult(tasks=tasks)
        assert len(result.completed) == 2

    def test_failed(self):
        tasks = [
            BatchTask("a", 1, BatchStatus.COMPLETED),
            BatchTask("b", 2, BatchStatus.FAILED),
        ]
        result = BatchResult(tasks=tasks)
        assert len(result.failed) == 1

    def test_success_rate(self):
        tasks = [
            BatchTask("a", 1, BatchStatus.COMPLETED),
            BatchTask("b", 2, BatchStatus.COMPLETED),
            BatchTask("c", 3, BatchStatus.FAILED),
        ]
        result = BatchResult(tasks=tasks)
        assert abs(result.success_rate - 0.6667) < 0.01

    def test_success_rate_empty(self):
        result = BatchResult()
        assert result.success_rate == 0.0

    def test_to_dict(self):
        tasks = [BatchTask("test", 1, BatchStatus.COMPLETED)]
        result = BatchResult(tasks=tasks, total_duration=3.5)
        d = result.to_dict()
        assert d["total_tasks"] == 1
        assert d["completed"] == 1
        assert d["total_duration"] == 3.5

    def test_to_markdown(self):
        tasks = [
            BatchTask("AI", 1, BatchStatus.COMPLETED, duration=2.0),
            BatchTask("ML", 2, BatchStatus.FAILED, duration=1.0),
        ]
        result = BatchResult(tasks=tasks, total_duration=3.0)
        md = result.to_markdown()
        assert "## Batch Research Results" in md
        assert "AI" in md
        assert "ML" in md

    def test_combine_reports(self):
        tasks = [
            BatchTask("A", 1, BatchStatus.COMPLETED, result="Report A"),
            BatchTask("B", 2, BatchStatus.FAILED, result=""),
            BatchTask("C", 3, BatchStatus.COMPLETED, result="Report C"),
        ]
        result = BatchResult(tasks=tasks)
        combined = result.combine_reports()
        assert "Report A" in combined
        assert "Report C" in combined


class TestCreateBatch:
    def test_basic(self):
        tasks = create_batch(["Topic 1", "Topic 2", "Topic 3"])
        assert len(tasks) == 3
        assert tasks[0].id == 1
        assert tasks[0].topic == "Topic 1"
        assert tasks[2].id == 3

    def test_strips_whitespace(self):
        tasks = create_batch(["  padded topic  "])
        assert tasks[0].topic == "padded topic"

    def test_config_overrides(self):
        tasks = create_batch(["topic"], config_overrides={"depth": 3})
        assert tasks[0].config_overrides == {"depth": 3}

    def test_empty(self):
        tasks = create_batch([])
        assert tasks == []


class TestRunBatch:
    def test_basic_run(self):
        tasks = create_batch(["topic1", "topic2"])
        result = run_batch(tasks, config=BatchConfig(delay_between=0))
        assert len(result.completed) == 2
        assert all(t.status == BatchStatus.COMPLETED for t in result.tasks)
        assert result.total_duration > 0

    def test_custom_researcher(self):
        def my_fn(topic: str) -> str:
            return f"Custom: {topic}"

        tasks = create_batch(["test"])
        result = run_batch(tasks, researcher_fn=my_fn, config=BatchConfig(delay_between=0))
        assert result.tasks[0].result == "Custom: test"

    def test_error_handling(self):
        def failing_fn(topic: str) -> str:
            raise ValueError("API error")

        tasks = create_batch(["test"])
        result = run_batch(tasks, researcher_fn=failing_fn, config=BatchConfig(delay_between=0))
        assert result.tasks[0].status == BatchStatus.FAILED
        assert "API error" in result.tasks[0].error

    def test_stop_on_error(self):
        call_count = [0]

        def failing_fn(topic: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("First fails")
            return "OK"

        tasks = create_batch(["a", "b", "c"])
        result = run_batch(
            tasks,
            researcher_fn=failing_fn,
            config=BatchConfig(stop_on_error=True, delay_between=0),
        )
        assert result.tasks[0].status == BatchStatus.FAILED
        assert result.tasks[1].status == BatchStatus.SKIPPED
        assert result.tasks[2].status == BatchStatus.SKIPPED

    def test_callback_on_complete(self):
        completed_tasks: list[str] = []

        def on_complete(task: BatchTask) -> None:
            completed_tasks.append(task.topic)

        tasks = create_batch(["a", "b"])
        run_batch(
            tasks,
            config=BatchConfig(on_task_complete=on_complete, delay_between=0),
        )
        assert len(completed_tasks) == 2

    def test_callback_on_error(self):
        error_tasks: list[str] = []

        def on_error(task: BatchTask) -> None:
            error_tasks.append(task.topic)

        def failing_fn(topic: str) -> str:
            raise RuntimeError("fail")

        tasks = create_batch(["a"])
        run_batch(
            tasks,
            researcher_fn=failing_fn,
            config=BatchConfig(on_task_error=on_error, delay_between=0),
        )
        assert len(error_tasks) == 1

    def test_retry_failed(self):
        attempt_count = [0]

        def flaky_fn(topic: str) -> str:
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ValueError("Transient error")
            return "Success"

        tasks = create_batch(["test"])
        result = run_batch(
            tasks,
            researcher_fn=flaky_fn,
            config=BatchConfig(retry_failed=True, max_retries=3, delay_between=0),
        )
        assert result.tasks[0].status == BatchStatus.COMPLETED


class TestBatchFromFile:
    def test_load_topics(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Topic A\nTopic B\n# Comment line\n\nTopic C\n")
            f.flush()
            path = f.name

        try:
            tasks = batch_from_file(path)
            assert len(tasks) == 3
            assert tasks[0].topic == "Topic A"
            assert tasks[2].topic == "Topic C"
        finally:
            os.unlink(path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("\n\n# Only comments\n\n")
            f.flush()
            path = f.name

        try:
            tasks = batch_from_file(path)
            assert tasks == []
        finally:
            os.unlink(path)
