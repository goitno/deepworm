"""Batch research orchestration.

Run multiple research tasks concurrently or sequentially,
with progress tracking and result aggregation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class BatchStatus(str, Enum):
    """Status of a batch task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchTask:
    """A single research task in a batch."""

    topic: str
    id: int = 0
    status: BatchStatus = BatchStatus.PENDING
    result: str = ""
    error: str = ""
    duration: float = 0.0
    config_overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "topic": self.topic,
            "status": self.status.value,
            "duration": round(self.duration, 2),
        }
        if self.error:
            d["error"] = self.error
        if self.result:
            d["result_length"] = len(self.result)
        return d


@dataclass
class BatchResult:
    """Result of a batch research operation."""

    tasks: list[BatchTask] = field(default_factory=list)
    total_duration: float = 0.0

    @property
    def completed(self) -> list[BatchTask]:
        return [t for t in self.tasks if t.status == BatchStatus.COMPLETED]

    @property
    def failed(self) -> list[BatchTask]:
        return [t for t in self.tasks if t.status == BatchStatus.FAILED]

    @property
    def success_rate(self) -> float:
        if not self.tasks:
            return 0.0
        return len(self.completed) / len(self.tasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": len(self.tasks),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "success_rate": round(self.success_rate, 2),
            "total_duration": round(self.total_duration, 2),
            "tasks": [t.to_dict() for t in self.tasks],
        }

    def to_markdown(self) -> str:
        """Render batch results as markdown summary."""
        lines = [
            "## Batch Research Results",
            "",
            f"**Total tasks**: {len(self.tasks)}",
            f"**Completed**: {len(self.completed)}",
            f"**Failed**: {len(self.failed)}",
            f"**Success rate**: {self.success_rate:.0%}",
            f"**Total duration**: {self.total_duration:.1f}s",
            "",
            "| # | Topic | Status | Duration |",
            "|---|-------|--------|----------|",
        ]
        for task in self.tasks:
            status_icon = {
                BatchStatus.COMPLETED: "✅",
                BatchStatus.FAILED: "❌",
                BatchStatus.RUNNING: "🔄",
                BatchStatus.PENDING: "⏳",
                BatchStatus.SKIPPED: "⏭️",
            }.get(task.status, "❓")
            lines.append(
                f"| {task.id} | {task.topic[:50]} | "
                f"{status_icon} {task.status.value} | {task.duration:.1f}s |"
            )
        return "\n".join(lines)

    def combine_reports(self, separator: str = "\n\n---\n\n") -> str:
        """Combine all completed research reports into one document."""
        parts: list[str] = []
        for task in self.completed:
            if task.result:
                parts.append(task.result)
        return separator.join(parts)


@dataclass
class BatchConfig:
    """Configuration for batch research."""

    max_concurrent: int = 1  # Sequential by default
    stop_on_error: bool = False
    retry_failed: bool = False
    max_retries: int = 2
    delay_between: float = 1.0  # Seconds between tasks
    on_task_complete: Optional[Callable[[BatchTask], None]] = None
    on_task_error: Optional[Callable[[BatchTask], None]] = None


def create_batch(
    topics: list[str],
    config_overrides: Optional[dict[str, Any]] = None,
) -> list[BatchTask]:
    """Create a batch of research tasks from topic list.

    Args:
        topics: List of research topics.
        config_overrides: Optional config to apply to all tasks.

    Returns:
        List of BatchTask objects.
    """
    tasks: list[BatchTask] = []
    overrides = config_overrides or {}
    for i, topic in enumerate(topics, 1):
        tasks.append(
            BatchTask(
                topic=topic.strip(),
                id=i,
                config_overrides=dict(overrides),
            )
        )
    return tasks


def run_batch(
    tasks: list[BatchTask],
    researcher_fn: Optional[Callable[[str], str]] = None,
    config: Optional[BatchConfig] = None,
) -> BatchResult:
    """Execute a batch of research tasks sequentially.

    Args:
        tasks: List of BatchTask objects.
        researcher_fn: Function that takes topic and returns report.
            If None, uses a default stub.
        config: Batch configuration.

    Returns:
        BatchResult with all task outcomes.
    """
    cfg = config or BatchConfig()
    fn = researcher_fn or _default_researcher

    start_time = time.monotonic()

    for task in tasks:
        task.status = BatchStatus.RUNNING
        task_start = time.monotonic()

        attempts = 1 + (cfg.max_retries if cfg.retry_failed else 0)
        for attempt in range(attempts):
            try:
                task.result = fn(task.topic)
                task.status = BatchStatus.COMPLETED
                task.duration = time.monotonic() - task_start

                if cfg.on_task_complete:
                    cfg.on_task_complete(task)
                break

            except Exception as e:
                task.error = str(e)
                if attempt >= attempts - 1:
                    task.status = BatchStatus.FAILED
                    task.duration = time.monotonic() - task_start

                    if cfg.on_task_error:
                        cfg.on_task_error(task)

                    if cfg.stop_on_error:
                        # Mark remaining as skipped
                        for remaining in tasks:
                            if remaining.status == BatchStatus.PENDING:
                                remaining.status = BatchStatus.SKIPPED
                        break

        if cfg.stop_on_error and task.status == BatchStatus.FAILED:
            break

        if cfg.delay_between > 0 and task != tasks[-1]:
            time.sleep(cfg.delay_between)

    total_duration = time.monotonic() - start_time

    return BatchResult(tasks=tasks, total_duration=total_duration)


def batch_from_file(filepath: str) -> list[BatchTask]:
    """Load batch tasks from a text file (one topic per line).

    Args:
        filepath: Path to topics file.

    Returns:
        List of BatchTask objects.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    topics = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return create_batch(topics)


def _default_researcher(topic: str) -> str:
    """Default stub researcher for testing."""
    return f"# Research: {topic}\n\nThis is a placeholder report for: {topic}"
