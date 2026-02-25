"""Tests for deepworm.data_pipeline module."""

import pytest

from deepworm.data_pipeline import (
    BatchResult,
    DataPipeline,
    ErrorStrategy,
    PipelineResult,
    PipelineStatus,
    Stage,
    StageResult,
    StageStatus,
    ValidationResult,
    ValidationRule,
    batch_process,
    chunk,
    create_pipeline,
    create_validation_rule,
    distinct,
    fan_in,
    fan_out,
    filter_data,
    flatten,
    group_by,
    map_data,
    reduce_data,
    validate_data,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_stage_status_values(self):
        assert StageStatus.PENDING.value == "pending"
        assert StageStatus.COMPLETED.value == "completed"
        assert StageStatus.FAILED.value == "failed"
        assert StageStatus.SKIPPED.value == "skipped"

    def test_pipeline_status_values(self):
        assert PipelineStatus.IDLE.value == "idle"
        assert PipelineStatus.COMPLETED.value == "completed"
        assert PipelineStatus.PARTIAL.value == "partial"

    def test_error_strategy_values(self):
        assert ErrorStrategy.STOP.value == "stop"
        assert ErrorStrategy.SKIP.value == "skip"
        assert ErrorStrategy.RETRY.value == "retry"
        assert ErrorStrategy.DEFAULT.value == "default"


# ---------------------------------------------------------------------------
# StageResult
# ---------------------------------------------------------------------------


class TestStageResult:
    def test_success(self):
        r = StageResult(name="test", status=StageStatus.COMPLETED, output_data=42)
        assert r.is_success is True
        assert r.is_failure is False

    def test_failure(self):
        r = StageResult(name="test", status=StageStatus.FAILED, error="boom")
        assert r.is_success is False
        assert r.is_failure is True

    def test_to_dict(self):
        r = StageResult(name="s1", status=StageStatus.COMPLETED, elapsed_ms=5.123)
        d = r.to_dict()
        assert d["name"] == "s1"
        assert d["status"] == "completed"
        assert d["elapsed_ms"] == 5.12


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_success_rate(self):
        stages = [
            StageResult(name="a", status=StageStatus.COMPLETED),
            StageResult(name="b", status=StageStatus.COMPLETED),
            StageResult(name="c", status=StageStatus.FAILED, error="err"),
        ]
        r = PipelineResult(status=PipelineStatus.PARTIAL, stages=stages)
        assert r.success_rate == pytest.approx(2 / 3, abs=0.01)
        assert r.stage_count == 3
        assert len(r.failed_stages) == 1
        assert len(r.completed_stages) == 2

    def test_empty(self):
        r = PipelineResult(status=PipelineStatus.COMPLETED)
        assert r.success_rate == 0.0
        assert r.stage_count == 0

    def test_to_dict(self):
        r = PipelineResult(status=PipelineStatus.COMPLETED, total_elapsed_ms=10.5)
        d = r.to_dict()
        assert d["status"] == "completed"
        assert d["total_elapsed_ms"] == 10.5

    def test_summary(self):
        stages = [
            StageResult(name="a", status=StageStatus.COMPLETED),
            StageResult(name="b", status=StageStatus.FAILED, error="oops"),
        ]
        r = PipelineResult(status=PipelineStatus.PARTIAL, stages=stages, total_elapsed_ms=5.0)
        s = r.summary()
        assert "1/2 completed" in s
        assert "oops" in s


# ---------------------------------------------------------------------------
# DataPipeline
# ---------------------------------------------------------------------------


class TestDataPipeline:
    def test_simple_pipeline(self):
        pipe = create_pipeline("test")
        pipe.add("double", lambda x: x * 2)
        pipe.add("add_one", lambda x: x + 1)
        result = pipe.execute(5)
        assert result.is_success
        assert result.final_output == 11

    def test_chaining(self):
        pipe = create_pipeline("test")
        pipe.add("a", lambda x: x + 1).add("b", lambda x: x * 3)
        result = pipe.execute(2)
        assert result.final_output == 9

    def test_stage_names(self):
        pipe = create_pipeline()
        pipe.add("extract", lambda x: x)
        pipe.add("transform", lambda x: x)
        pipe.add("load", lambda x: x)
        assert pipe.stage_names == ["extract", "transform", "load"]

    def test_remove_stage(self):
        pipe = create_pipeline()
        pipe.add("a", lambda x: x)
        pipe.add("b", lambda x: x)
        assert pipe.remove("a") is True
        assert pipe.stage_names == ["b"]
        assert pipe.remove("nonexistent") is False

    def test_disable_enable(self):
        pipe = create_pipeline()
        pipe.add("a", lambda x: x * 2)
        pipe.add("b", lambda x: x + 10)
        pipe.disable("a")
        result = pipe.execute(5)
        # "a" skipped, "b" runs on original input
        assert result.final_output == 15
        assert result.stages[0].status == StageStatus.SKIPPED

        pipe.enable("a")
        result = pipe.execute(5)
        assert result.final_output == 20

    def test_error_stop(self):
        pipe = create_pipeline(error_strategy=ErrorStrategy.STOP)
        pipe.add("ok", lambda x: x + 1)
        pipe.add("fail", lambda x: 1 / 0)
        pipe.add("never", lambda x: x + 100)
        result = pipe.execute(1)
        assert result.status == PipelineStatus.FAILED
        assert len(result.stages) == 2  # third never ran

    def test_error_skip(self):
        pipe = create_pipeline(error_strategy=ErrorStrategy.SKIP)
        pipe.add("ok", lambda x: x + 1)
        pipe.add("fail", lambda x: 1 / 0)
        pipe.add("after", lambda x: x + 100)
        result = pipe.execute(1)
        assert result.status == PipelineStatus.PARTIAL
        assert result.final_output == 102  # 1+1=2, skip fail, 2+100=102

    def test_error_default(self):
        pipe = create_pipeline(error_strategy=ErrorStrategy.DEFAULT)
        pipe.add("fail", lambda x: 1 / 0, default_value=99)
        pipe.add("after", lambda x: x + 1)
        result = pipe.execute(0)
        assert result.final_output == 100

    def test_retry(self):
        call_count = [0]

        def flaky(data):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("not yet")
            return data * 2

        pipe = create_pipeline()
        pipe.add("flaky", flaky, max_retries=3)
        result = pipe.execute(5)
        assert result.is_success
        assert result.final_output == 10

    def test_condition(self):
        pipe = create_pipeline()
        pipe.add("always", lambda x: x + 1)
        pipe.add("only_big", lambda x: x * 100, condition=lambda x: x > 10)
        result = pipe.execute(5)
        assert result.final_output == 6  # condition not met, skipped

        result = pipe.execute(15)
        assert result.final_output == 1600  # 16 * 100

    def test_run_count(self):
        pipe = create_pipeline()
        pipe.add("a", lambda x: x)
        assert pipe.run_count == 0
        pipe.execute(1)
        pipe.execute(2)
        assert pipe.run_count == 2

    def test_before_after_hooks(self):
        events = []

        def before_hook(name, data):
            events.append(f"before:{name}")

        def after_hook(name, result):
            events.append(f"after:{name}:{result.status.value}")

        pipe = create_pipeline()
        pipe.before(before_hook)
        pipe.after(after_hook)
        pipe.add("step1", lambda x: x + 1)
        pipe.add("step2", lambda x: x * 2)
        pipe.execute(5)

        assert events == [
            "before:step1",
            "after:step1:completed",
            "before:step2",
            "after:step2:completed",
        ]

    def test_before_hook_transforms_data(self):
        pipe = create_pipeline()
        pipe.before(lambda name, data: data + 100 if name == "s1" else None)
        pipe.add("s1", lambda x: x * 2)
        result = pipe.execute(5)
        assert result.final_output == 210  # (5+100)*2

    def test_elapsed_time(self):
        pipe = create_pipeline()
        pipe.add("a", lambda x: x)
        result = pipe.execute(1)
        assert result.total_elapsed_ms >= 0
        assert result.stages[0].elapsed_ms >= 0

    def test_metadata(self):
        pipe = create_pipeline("my-pipe")
        pipe.add("a", lambda x: x)
        result = pipe.execute(1)
        assert result.metadata["pipeline_name"] == "my-pipe"
        assert result.metadata["run_count"] == 1

    def test_none_input(self):
        pipe = create_pipeline()
        pipe.add("init", lambda x: {"value": 42} if x is None else x)
        result = pipe.execute()
        assert result.final_output == {"value": 42}


# ---------------------------------------------------------------------------
# Fan-out / Fan-in
# ---------------------------------------------------------------------------


class TestFanOut:
    def test_fan_out(self):
        results = fan_out(10, {
            "double": lambda x: x * 2,
            "square": lambda x: x ** 2,
            "negate": lambda x: -x,
        })
        assert results["double"].output_data == 20
        assert results["square"].output_data == 100
        assert results["negate"].output_data == -10

    def test_fan_out_with_error(self):
        results = fan_out(5, {
            "ok": lambda x: x,
            "fail": lambda x: 1 / 0,
        })
        assert results["ok"].is_success
        assert results["fail"].is_failure

    def test_fan_in(self):
        results = fan_out(10, {
            "a": lambda x: x + 1,
            "b": lambda x: x + 2,
        })
        combined = fan_in(results, lambda d: sum(d.values()))
        assert combined == 23  # 11 + 12

    def test_fan_in_filters_failures(self):
        results = fan_out(5, {
            "ok": lambda x: x * 2,
            "fail": lambda x: 1 / 0,
        })
        combined = fan_in(results, lambda d: list(d.values()))
        assert combined == [10]


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


class TestBatchProcess:
    def test_batch_success(self):
        result = batch_process([1, 2, 3], lambda x: x * 2)
        assert len(result.successes) == 3
        assert result.outputs == [2, 4, 6]
        assert result.success_rate == 1.0

    def test_batch_with_errors_skip(self):
        def process(x):
            if x == 0:
                raise ValueError("zero!")
            return 10 / x

        result = batch_process([2, 0, 5], process, error_strategy=ErrorStrategy.SKIP)
        assert len(result.successes) == 2
        assert len(result.failures) == 1
        assert result.total_elapsed_ms >= 0

    def test_batch_with_errors_stop(self):
        def process(x):
            if x == 0:
                raise ValueError("zero!")
            return x

        result = batch_process([1, 0, 2], process, error_strategy=ErrorStrategy.STOP)
        assert len(result.items) == 2  # stopped at 0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_validate_pass(self):
        rules = [
            create_validation_rule("positive", lambda x: x > 0, "Must be positive"),
            create_validation_rule("small", lambda x: x < 100, "Must be < 100"),
        ]
        result = validate_data(50, rules)
        assert result.is_valid
        assert result.errors == []

    def test_validate_fail(self):
        rules = [
            create_validation_rule("positive", lambda x: x > 0, "Must be positive"),
        ]
        result = validate_data(-5, rules)
        assert not result.is_valid
        assert "Must be positive" in result.errors[0]

    def test_validate_exception(self):
        rules = [
            create_validation_rule("crash", lambda x: x.nonexistent, "msg"),
        ]
        result = validate_data(42, rules)
        assert not result.is_valid
        assert "error" in result.errors[0].lower()


# ---------------------------------------------------------------------------
# Data transformers
# ---------------------------------------------------------------------------


class TestDataTransformers:
    def test_map_data(self):
        assert map_data([1, 2, 3], lambda x: x * 2) == [2, 4, 6]

    def test_filter_data(self):
        assert filter_data([1, 2, 3, 4, 5], lambda x: x % 2 == 0) == [2, 4]

    def test_reduce_data(self):
        assert reduce_data([1, 2, 3, 4], lambda a, b: a + b) == 10

    def test_reduce_with_initial(self):
        assert reduce_data([1, 2, 3], lambda a, b: a + b, initial=10) == 16

    def test_reduce_empty(self):
        assert reduce_data([], lambda a, b: a + b) is None

    def test_group_by(self):
        items = [1, 2, 3, 4, 5, 6]
        groups = group_by(items, lambda x: "even" if x % 2 == 0 else "odd")
        assert groups["even"] == [2, 4, 6]
        assert groups["odd"] == [1, 3, 5]

    def test_flatten(self):
        assert flatten([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]

    def test_flatten_mixed(self):
        assert flatten([[1, 2], 3, [4]]) == [1, 2, 3, 4]

    def test_distinct(self):
        assert distinct([1, 2, 2, 3, 1, 4]) == [1, 2, 3, 4]

    def test_distinct_with_key(self):
        items = [{"id": 1}, {"id": 2}, {"id": 1}]
        result = distinct(items, key_fn=lambda x: str(x["id"]))
        assert len(result) == 2

    def test_chunk(self):
        assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_chunk_zero(self):
        assert chunk([1, 2], 0) == [[1, 2]]

    def test_chunk_larger_than_list(self):
        assert chunk([1, 2], 5) == [[1, 2]]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestFactory:
    def test_create_pipeline(self):
        pipe = create_pipeline("test", ErrorStrategy.SKIP)
        assert pipe.name == "test"

    def test_create_validation_rule(self):
        rule = create_validation_rule("check", lambda x: x > 0, "positive")
        assert rule.name == "check"
        assert rule.message == "positive"
