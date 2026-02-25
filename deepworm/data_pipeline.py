"""Data pipeline for deepworm.

Provides composable ETL (Extract, Transform, Load) pipelines with
stage-based processing, error handling, parallel fan-out, and metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar


T = TypeVar("T")


class StageStatus(Enum):
    """Status of a pipeline stage execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(Enum):
    """Overall pipeline status."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ErrorStrategy(Enum):
    """How to handle errors in the pipeline."""

    STOP = "stop"
    SKIP = "skip"
    RETRY = "retry"
    DEFAULT = "default"


@dataclass
class StageResult:
    """Result of a single stage execution."""

    name: str
    status: StageStatus
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    retries: int = 0

    @property
    def is_success(self) -> bool:
        return self.status == StageStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        return self.status == StageStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "error": self.error,
            "retries": self.retries,
        }


@dataclass
class PipelineResult:
    """Result of a full pipeline execution."""

    status: PipelineStatus
    stages: List[StageResult] = field(default_factory=list)
    final_output: Any = None
    total_elapsed_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == PipelineStatus.COMPLETED

    @property
    def failed_stages(self) -> List[StageResult]:
        return [s for s in self.stages if s.is_failure]

    @property
    def completed_stages(self) -> List[StageResult]:
        return [s for s in self.stages if s.is_success]

    @property
    def stage_count(self) -> int:
        return len(self.stages)

    @property
    def success_rate(self) -> float:
        if not self.stages:
            return 0.0
        return len(self.completed_stages) / len(self.stages)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "total_elapsed_ms": round(self.total_elapsed_ms, 2),
            "stage_count": self.stage_count,
            "success_rate": round(self.success_rate, 2),
            "stages": [s.to_dict() for s in self.stages],
        }

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Pipeline: {self.status.value}",
            f"Stages: {len(self.completed_stages)}/{self.stage_count} completed",
            f"Time: {self.total_elapsed_ms:.1f}ms",
        ]
        if self.failed_stages:
            lines.append(f"Failures: {len(self.failed_stages)}")
            for s in self.failed_stages:
                lines.append(f"  - {s.name}: {s.error}")
        return "\n".join(lines)


@dataclass
class Stage:
    """A pipeline stage definition."""

    name: str
    handler: Callable[[Any], Any]
    error_strategy: ErrorStrategy = ErrorStrategy.STOP
    default_value: Any = None
    max_retries: int = 0
    condition: Optional[Callable[[Any], bool]] = None
    enabled: bool = True

    def should_run(self, data: Any) -> bool:
        if not self.enabled:
            return False
        if self.condition and not self.condition(data):
            return False
        return True


class DataPipeline:
    """Composable data processing pipeline.

    Build ETL pipelines with stages that transform data sequentially.

    Example:
        pipe = DataPipeline("my-pipeline")
        pipe.add("extract", lambda d: fetch_data(d))
        pipe.add("transform", lambda d: clean(d))
        pipe.add("load", lambda d: save(d))
        result = pipe.execute(input_data)
    """

    def __init__(
        self,
        name: str = "pipeline",
        error_strategy: ErrorStrategy = ErrorStrategy.STOP,
    ) -> None:
        self.name = name
        self.default_error_strategy = error_strategy
        self._stages: List[Stage] = []
        self._before_hooks: List[Callable[[str, Any], Any]] = []
        self._after_hooks: List[Callable[[str, StageResult], None]] = []
        self._run_count: int = 0

    def add(
        self,
        name: str,
        handler: Callable[[Any], Any],
        *,
        error_strategy: Optional[ErrorStrategy] = None,
        default_value: Any = None,
        max_retries: int = 0,
        condition: Optional[Callable[[Any], bool]] = None,
    ) -> "DataPipeline":
        """Add a stage to the pipeline. Returns self for chaining."""
        stage = Stage(
            name=name,
            handler=handler,
            error_strategy=error_strategy or self.default_error_strategy,
            default_value=default_value,
            max_retries=max_retries,
            condition=condition,
        )
        self._stages.append(stage)
        return self

    def remove(self, name: str) -> bool:
        """Remove a stage by name."""
        for i, s in enumerate(self._stages):
            if s.name == name:
                self._stages.pop(i)
                return True
        return False

    def enable(self, name: str) -> bool:
        """Enable a stage."""
        for s in self._stages:
            if s.name == name:
                s.enabled = True
                return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a stage."""
        for s in self._stages:
            if s.name == name:
                s.enabled = False
                return True
        return False

    def before(self, hook: Callable[[str, Any], Any]) -> None:
        """Add a before-stage hook. Receives (stage_name, data)."""
        self._before_hooks.append(hook)

    def after(self, hook: Callable[[str, StageResult], None]) -> None:
        """Add an after-stage hook. Receives (stage_name, result)."""
        self._after_hooks.append(hook)

    @property
    def stage_names(self) -> List[str]:
        return [s.name for s in self._stages]

    @property
    def run_count(self) -> int:
        return self._run_count

    def execute(self, data: Any = None) -> PipelineResult:
        """Execute the full pipeline."""
        start = time.perf_counter()
        self._run_count += 1

        results: List[StageResult] = []
        current_data = data
        failed = False

        for stage in self._stages:
            # Check condition
            if not stage.should_run(current_data):
                results.append(StageResult(
                    name=stage.name,
                    status=StageStatus.SKIPPED,
                    input_data=current_data,
                    output_data=current_data,
                ))
                continue

            # Before hooks
            for hook in self._before_hooks:
                hook_result = hook(stage.name, current_data)
                if hook_result is not None:
                    current_data = hook_result

            # Execute stage
            stage_result = self._execute_stage(stage, current_data)
            results.append(stage_result)

            # After hooks
            for hook in self._after_hooks:
                hook(stage.name, stage_result)

            if stage_result.is_success:
                current_data = stage_result.output_data
            elif stage_result.status == StageStatus.SKIPPED:
                continue
            else:
                # Stage failed
                if stage.error_strategy == ErrorStrategy.STOP:
                    failed = True
                    break
                elif stage.error_strategy == ErrorStrategy.SKIP:
                    continue
                elif stage.error_strategy == ErrorStrategy.DEFAULT:
                    current_data = stage.default_value
                else:
                    failed = True
                    break

        elapsed = (time.perf_counter() - start) * 1000

        if failed:
            status = PipelineStatus.FAILED
        elif any(s.is_failure for s in results):
            status = PipelineStatus.PARTIAL
        else:
            status = PipelineStatus.COMPLETED

        return PipelineResult(
            status=status,
            stages=results,
            final_output=current_data,
            total_elapsed_ms=elapsed,
            metadata={"pipeline_name": self.name, "run_count": self._run_count},
        )

    def _execute_stage(self, stage: Stage, data: Any) -> StageResult:
        """Execute a single stage with retry support."""
        retries = 0
        last_error = None

        while True:
            stage_start = time.perf_counter()
            try:
                output = stage.handler(data)
                elapsed = (time.perf_counter() - stage_start) * 1000
                return StageResult(
                    name=stage.name,
                    status=StageStatus.COMPLETED,
                    input_data=data,
                    output_data=output,
                    elapsed_ms=elapsed,
                    retries=retries,
                )
            except Exception as e:
                last_error = str(e)
                retries += 1
                if retries > stage.max_retries:
                    elapsed = (time.perf_counter() - stage_start) * 1000
                    return StageResult(
                        name=stage.name,
                        status=StageStatus.FAILED,
                        input_data=data,
                        error=last_error,
                        elapsed_ms=elapsed,
                        retries=retries - 1,
                    )


# ---------------------------------------------------------------------------
# Fan-out / Fan-in
# ---------------------------------------------------------------------------


def fan_out(
    data: Any,
    handlers: Dict[str, Callable[[Any], Any]],
) -> Dict[str, StageResult]:
    """Execute multiple handlers on the same data (fan-out).

    Returns a dict mapping handler name to StageResult.
    """
    results = {}
    for name, handler in handlers.items():
        start = time.perf_counter()
        try:
            output = handler(data)
            elapsed = (time.perf_counter() - start) * 1000
            results[name] = StageResult(
                name=name,
                status=StageStatus.COMPLETED,
                input_data=data,
                output_data=output,
                elapsed_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            results[name] = StageResult(
                name=name,
                status=StageStatus.FAILED,
                input_data=data,
                error=str(e),
                elapsed_ms=elapsed,
            )
    return results


def fan_in(
    results: Dict[str, StageResult],
    combiner: Callable[[Dict[str, Any]], Any],
) -> Any:
    """Combine fan-out results into a single value.

    Only uses successful stage outputs.
    """
    successful = {
        name: r.output_data
        for name, r in results.items()
        if r.is_success
    }
    return combiner(successful)


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


@dataclass
class BatchResult:
    """Result of batch processing."""

    items: List[StageResult]
    total_elapsed_ms: float = 0.0

    @property
    def successes(self) -> List[StageResult]:
        return [i for i in self.items if i.is_success]

    @property
    def failures(self) -> List[StageResult]:
        return [i for i in self.items if i.is_failure]

    @property
    def success_rate(self) -> float:
        if not self.items:
            return 0.0
        return len(self.successes) / len(self.items)

    @property
    def outputs(self) -> List[Any]:
        return [i.output_data for i in self.successes]


def batch_process(
    items: List[Any],
    handler: Callable[[Any], Any],
    *,
    error_strategy: ErrorStrategy = ErrorStrategy.SKIP,
) -> BatchResult:
    """Process a list of items through a handler.

    Returns BatchResult with individual item results.
    """
    start = time.perf_counter()
    results = []

    for i, item in enumerate(items):
        item_start = time.perf_counter()
        try:
            output = handler(item)
            elapsed = (time.perf_counter() - item_start) * 1000
            results.append(StageResult(
                name=f"item_{i}",
                status=StageStatus.COMPLETED,
                input_data=item,
                output_data=output,
                elapsed_ms=elapsed,
            ))
        except Exception as e:
            elapsed = (time.perf_counter() - item_start) * 1000
            results.append(StageResult(
                name=f"item_{i}",
                status=StageStatus.FAILED,
                input_data=item,
                error=str(e),
                elapsed_ms=elapsed,
            ))
            if error_strategy == ErrorStrategy.STOP:
                break

    total = (time.perf_counter() - start) * 1000
    return BatchResult(items=results, total_elapsed_ms=total)


# ---------------------------------------------------------------------------
# Data validators
# ---------------------------------------------------------------------------


@dataclass
class ValidationRule:
    """A validation rule for pipeline data."""

    name: str
    check: Callable[[Any], bool]
    message: str = ""


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_data(
    data: Any,
    rules: List[ValidationRule],
) -> ValidationResult:
    """Validate data against a list of rules."""
    errors = []
    for rule in rules:
        try:
            if not rule.check(data):
                errors.append(rule.message or f"Validation failed: {rule.name}")
        except Exception as e:
            errors.append(f"Rule '{rule.name}' error: {str(e)}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Data transformers
# ---------------------------------------------------------------------------


def map_data(items: List[Any], fn: Callable[[Any], Any]) -> List[Any]:
    """Apply a function to each item."""
    return [fn(item) for item in items]


def filter_data(items: List[Any], predicate: Callable[[Any], bool]) -> List[Any]:
    """Filter items by predicate."""
    return [item for item in items if predicate(item)]


def reduce_data(
    items: List[Any],
    fn: Callable[[Any, Any], Any],
    initial: Any = None,
) -> Any:
    """Reduce items to a single value."""
    if initial is not None:
        acc = initial
        for item in items:
            acc = fn(acc, item)
        return acc

    if not items:
        return None

    acc = items[0]
    for item in items[1:]:
        acc = fn(acc, item)
    return acc


def group_by(
    items: List[Any],
    key_fn: Callable[[Any], str],
) -> Dict[str, List[Any]]:
    """Group items by key function."""
    groups: Dict[str, List[Any]] = {}
    for item in items:
        key = key_fn(item)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups


def flatten(nested: List[List[Any]]) -> List[Any]:
    """Flatten a list of lists."""
    result = []
    for sublist in nested:
        if isinstance(sublist, list):
            result.extend(sublist)
        else:
            result.append(sublist)
    return result


def distinct(items: List[Any], key_fn: Optional[Callable[[Any], str]] = None) -> List[Any]:
    """Remove duplicates, preserving order."""
    seen = set()
    result = []
    for item in items:
        k = key_fn(item) if key_fn else str(item)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def chunk(items: List[Any], size: int) -> List[List[Any]]:
    """Split a list into chunks of given size."""
    if size <= 0:
        return [items] if items else []
    return [items[i:i + size] for i in range(0, len(items), size)]


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def create_pipeline(
    name: str = "pipeline",
    error_strategy: ErrorStrategy = ErrorStrategy.STOP,
) -> DataPipeline:
    """Create a new data pipeline."""
    return DataPipeline(name=name, error_strategy=error_strategy)


def create_validation_rule(
    name: str,
    check: Callable[[Any], bool],
    message: str = "",
) -> ValidationRule:
    """Create a validation rule."""
    return ValidationRule(name=name, check=check, message=message)
