"""Concurrency utilities for deepworm.

Provides thread pool execution, task queues, worker pools, and
synchronization primitives for concurrent processing.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class TaskStatus(Enum):
    """Status of a concurrent task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerState(Enum):
    """State of a worker thread."""

    IDLE = "idle"
    BUSY = "busy"
    STOPPED = "stopped"


@dataclass
class TaskResult:
    """Result of a concurrent task execution."""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    worker_id: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        return self.status == TaskStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "error": self.error,
            "worker_id": self.worker_id,
        }


@dataclass
class PoolStats:
    """Statistics for a worker pool."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_elapsed_ms: float = 0.0
    active_workers: int = 0
    idle_workers: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    @property
    def avg_task_ms(self) -> float:
        if self.completed_tasks == 0:
            return 0.0
        return self.total_elapsed_ms / self.completed_tasks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": round(self.success_rate, 2),
            "avg_task_ms": round(self.avg_task_ms, 2),
            "active_workers": self.active_workers,
            "idle_workers": self.idle_workers,
        }


# ---------------------------------------------------------------------------
# Thread-safe counter
# ---------------------------------------------------------------------------


class AtomicCounter:
    """Thread-safe counter."""

    def __init__(self, initial: int = 0) -> None:
        self._value = initial
        self._lock = threading.Lock()

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

    def increment(self, amount: int = 1) -> int:
        with self._lock:
            self._value += amount
            return self._value

    def decrement(self, amount: int = 1) -> int:
        with self._lock:
            self._value -= amount
            return self._value

    def reset(self, value: int = 0) -> None:
        with self._lock:
            self._value = value


# ---------------------------------------------------------------------------
# Thread-safe value holder
# ---------------------------------------------------------------------------


class AtomicValue:
    """Thread-safe value holder."""

    def __init__(self, initial: Any = None) -> None:
        self._value = initial
        self._lock = threading.Lock()

    @property
    def value(self) -> Any:
        with self._lock:
            return self._value

    def set(self, new_value: Any) -> None:
        with self._lock:
            self._value = new_value

    def compare_and_set(self, expected: Any, new_value: Any) -> bool:
        with self._lock:
            if self._value == expected:
                self._value = new_value
                return True
            return False

    def update(self, fn: Callable[[Any], Any]) -> Any:
        with self._lock:
            self._value = fn(self._value)
            return self._value


# ---------------------------------------------------------------------------
# Task queue
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A task to be executed concurrently."""

    task_id: str
    fn: Callable[[], Any]
    priority: int = 0

    def __lt__(self, other: "Task") -> bool:
        return self.priority > other.priority  # higher priority first


class TaskQueue:
    """Thread-safe priority task queue."""

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=maxsize)
        self._counter = AtomicCounter()

    def put(self, task: Task) -> None:
        """Add a task to the queue."""
        self._queue.put((task.priority * -1, self._counter.increment(), task))

    def get(self, timeout: Optional[float] = None) -> Optional[Task]:
        """Get the highest priority task. Returns None on timeout."""
        try:
            _, _, task = self._queue.get(timeout=timeout)
            return task
        except queue.Empty:
            return None

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        return self._queue.empty()

    def clear(self) -> int:
        """Clear all pending tasks. Returns count cleared."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        return count


# ---------------------------------------------------------------------------
# Worker pool
# ---------------------------------------------------------------------------


class WorkerPool:
    """Thread pool for concurrent task execution.

    Example:
        pool = WorkerPool(workers=4)
        pool.start()
        pool.submit("task1", lambda: compute_something())
        pool.submit("task2", lambda: compute_other())
        pool.wait()
        results = pool.results
        pool.stop()
    """

    def __init__(
        self,
        workers: int = 4,
        queue_size: int = 0,
    ) -> None:
        self._num_workers = max(1, workers)
        self._task_queue = TaskQueue(maxsize=queue_size)
        self._results: Dict[str, TaskResult] = {}
        self._results_lock = threading.Lock()
        self._threads: List[threading.Thread] = []
        self._running = False
        self._stop_event = threading.Event()
        self._active_count = AtomicCounter()
        self._stats = PoolStats()
        self._stats_lock = threading.Lock()

    def start(self) -> None:
        """Start worker threads."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        for i in range(self._num_workers):
            t = threading.Thread(
                target=self._worker_loop,
                name=f"worker-{i}",
                daemon=True,
            )
            t.start()
            self._threads.append(t)

    def stop(self, timeout: float = 5.0) -> None:
        """Stop all workers."""
        self._stop_event.set()
        self._running = False
        for t in self._threads:
            t.join(timeout=timeout)
        self._threads.clear()

    def submit(
        self,
        task_id: str,
        fn: Callable[[], Any],
        priority: int = 0,
    ) -> None:
        """Submit a task for execution."""
        task = Task(task_id=task_id, fn=fn, priority=priority)
        self._task_queue.put(task)
        with self._stats_lock:
            self._stats.total_tasks += 1

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for all tasks to complete.

        Returns True if all completed, False if timed out.
        """
        start = time.time()
        while True:
            if self._task_queue.empty and self._active_count.value == 0:
                return True
            if timeout is not None and (time.time() - start) > timeout:
                return False
            time.sleep(0.01)

    @property
    def results(self) -> Dict[str, TaskResult]:
        with self._results_lock:
            return dict(self._results)

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        with self._results_lock:
            return self._results.get(task_id)

    @property
    def stats(self) -> PoolStats:
        with self._stats_lock:
            self._stats.active_workers = self._active_count.value
            self._stats.idle_workers = len(self._threads) - self._active_count.value
            return PoolStats(
                total_tasks=self._stats.total_tasks,
                completed_tasks=self._stats.completed_tasks,
                failed_tasks=self._stats.failed_tasks,
                total_elapsed_ms=self._stats.total_elapsed_ms,
                active_workers=self._stats.active_workers,
                idle_workers=self._stats.idle_workers,
            )

    @property
    def pending_count(self) -> int:
        return self._task_queue.size

    @property
    def is_running(self) -> bool:
        return self._running

    def _worker_loop(self) -> None:
        """Worker thread main loop."""
        thread_name = threading.current_thread().name
        while not self._stop_event.is_set():
            task = self._task_queue.get(timeout=0.1)
            if task is None:
                continue

            self._active_count.increment()
            start = time.perf_counter()
            try:
                result = task.fn()
                elapsed = (time.perf_counter() - start) * 1000
                task_result = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    elapsed_ms=elapsed,
                    worker_id=thread_name,
                )
                with self._stats_lock:
                    self._stats.completed_tasks += 1
                    self._stats.total_elapsed_ms += elapsed
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                task_result = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    elapsed_ms=elapsed,
                    worker_id=thread_name,
                )
                with self._stats_lock:
                    self._stats.failed_tasks += 1
            finally:
                self._active_count.decrement()

            with self._results_lock:
                self._results[task.task_id] = task_result


# ---------------------------------------------------------------------------
# Parallel map
# ---------------------------------------------------------------------------


def parallel_map(
    fn: Callable[[Any], Any],
    items: List[Any],
    workers: int = 4,
) -> List[TaskResult]:
    """Apply a function to items concurrently.

    Returns list of TaskResult in same order as items.
    """
    pool = WorkerPool(workers=workers)
    pool.start()

    for i, item in enumerate(items):
        pool.submit(f"item_{i}", lambda x=item: fn(x))

    pool.wait()
    pool.stop()

    results = pool.results
    return [results.get(f"item_{i}", TaskResult(
        task_id=f"item_{i}",
        status=TaskStatus.FAILED,
        error="Missing result",
    )) for i in range(len(items))]


# ---------------------------------------------------------------------------
# Debounce / Throttle
# ---------------------------------------------------------------------------


class Debouncer:
    """Debounce function calls — only execute after a quiet period."""

    def __init__(self, delay_ms: float) -> None:
        self._delay_s = delay_ms / 1000.0
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._last_result: Any = None
        self._call_count = 0

    def __call__(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()

            def execute():
                self._last_result = fn(*args, **kwargs)
                self._call_count += 1

            self._timer = threading.Timer(self._delay_s, execute)
            self._timer.daemon = True
            self._timer.start()

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def last_result(self) -> Any:
        return self._last_result

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class Throttle:
    """Throttle function calls — at most once per interval."""

    def __init__(self, interval_ms: float) -> None:
        self._interval_s = interval_ms / 1000.0
        self._last_call: float = 0
        self._lock = threading.Lock()
        self._call_count = 0

    def __call__(self, fn: Callable, *args: Any, **kwargs: Any) -> Optional[Any]:
        with self._lock:
            now = time.time()
            if now - self._last_call >= self._interval_s:
                self._last_call = now
                self._call_count += 1
                return fn(*args, **kwargs)
            return None

    @property
    def call_count(self) -> int:
        return self._call_count

    def reset(self) -> None:
        with self._lock:
            self._last_call = 0
            self._call_count = 0


# ---------------------------------------------------------------------------
# Once — execute exactly once
# ---------------------------------------------------------------------------


class Once:
    """Execute a function exactly once, thread-safely."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._called = False
        self._result: Any = None

    def __call__(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if not self._called:
                self._result = fn(*args, **kwargs)
                self._called = True
            return self._result

    @property
    def called(self) -> bool:
        return self._called

    @property
    def result(self) -> Any:
        return self._result

    def reset(self) -> None:
        with self._lock:
            self._called = False
            self._result = None


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def create_worker_pool(
    workers: int = 4,
    queue_size: int = 0,
) -> WorkerPool:
    """Create a new worker pool."""
    return WorkerPool(workers=workers, queue_size=queue_size)


def create_task_queue(maxsize: int = 0) -> TaskQueue:
    """Create a new task queue."""
    return TaskQueue(maxsize=maxsize)


def create_counter(initial: int = 0) -> AtomicCounter:
    """Create a thread-safe counter."""
    return AtomicCounter(initial=initial)


def create_atomic(initial: Any = None) -> AtomicValue:
    """Create a thread-safe value holder."""
    return AtomicValue(initial=initial)
