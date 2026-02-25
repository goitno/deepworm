"""Tests for deepworm.concurrency module."""

import time
import threading

import pytest

from deepworm.concurrency import (
    AtomicCounter,
    AtomicValue,
    Debouncer,
    Once,
    PoolStats,
    Task,
    TaskQueue,
    TaskResult,
    TaskStatus,
    Throttle,
    WorkerPool,
    WorkerState,
    create_atomic,
    create_counter,
    create_task_queue,
    create_worker_pool,
    parallel_map,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_task_status(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_worker_state(self):
        assert WorkerState.IDLE.value == "idle"
        assert WorkerState.BUSY.value == "busy"
        assert WorkerState.STOPPED.value == "stopped"


# ---------------------------------------------------------------------------
# TaskResult
# ---------------------------------------------------------------------------


class TestTaskResult:
    def test_success(self):
        r = TaskResult(task_id="t1", status=TaskStatus.COMPLETED, result=42)
        assert r.is_success
        assert not r.is_failure

    def test_failure(self):
        r = TaskResult(task_id="t1", status=TaskStatus.FAILED, error="boom")
        assert r.is_failure
        assert not r.is_success

    def test_to_dict(self):
        r = TaskResult(task_id="t1", status=TaskStatus.COMPLETED, elapsed_ms=1.5)
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "completed"


# ---------------------------------------------------------------------------
# PoolStats
# ---------------------------------------------------------------------------


class TestPoolStats:
    def test_success_rate(self):
        s = PoolStats(total_tasks=10, completed_tasks=8, failed_tasks=2)
        assert s.success_rate == 0.8

    def test_avg_task_ms(self):
        s = PoolStats(completed_tasks=4, total_elapsed_ms=100)
        assert s.avg_task_ms == 25.0

    def test_empty(self):
        s = PoolStats()
        assert s.success_rate == 0.0
        assert s.avg_task_ms == 0.0

    def test_to_dict(self):
        s = PoolStats(total_tasks=5)
        d = s.to_dict()
        assert d["total_tasks"] == 5


# ---------------------------------------------------------------------------
# AtomicCounter
# ---------------------------------------------------------------------------


class TestAtomicCounter:
    def test_basic(self):
        c = create_counter(10)
        assert c.value == 10
        assert c.increment() == 11
        assert c.decrement() == 10
        c.reset()
        assert c.value == 0

    def test_thread_safety(self):
        c = create_counter()
        threads = []
        for _ in range(10):
            t = threading.Thread(target=lambda: [c.increment() for _ in range(100)])
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        assert c.value == 1000


# ---------------------------------------------------------------------------
# AtomicValue
# ---------------------------------------------------------------------------


class TestAtomicValue:
    def test_basic(self):
        v = create_atomic("hello")
        assert v.value == "hello"
        v.set("world")
        assert v.value == "world"

    def test_compare_and_set(self):
        v = create_atomic(10)
        assert v.compare_and_set(10, 20) is True
        assert v.value == 20
        assert v.compare_and_set(10, 30) is False
        assert v.value == 20

    def test_update(self):
        v = create_atomic(5)
        result = v.update(lambda x: x * 2)
        assert result == 10
        assert v.value == 10


# ---------------------------------------------------------------------------
# TaskQueue
# ---------------------------------------------------------------------------


class TestTaskQueue:
    def test_put_get(self):
        q = create_task_queue()
        q.put(Task(task_id="t1", fn=lambda: 1))
        assert q.size == 1
        task = q.get(timeout=1)
        assert task.task_id == "t1"
        assert q.empty

    def test_priority(self):
        q = create_task_queue()
        q.put(Task(task_id="low", fn=lambda: 1, priority=1))
        q.put(Task(task_id="high", fn=lambda: 2, priority=10))
        q.put(Task(task_id="med", fn=lambda: 3, priority=5))
        # Highest priority first
        t1 = q.get(timeout=1)
        assert t1.task_id == "high"

    def test_get_timeout(self):
        q = create_task_queue()
        result = q.get(timeout=0.01)
        assert result is None

    def test_clear(self):
        q = create_task_queue()
        q.put(Task(task_id="a", fn=lambda: 1))
        q.put(Task(task_id="b", fn=lambda: 2))
        count = q.clear()
        assert count == 2
        assert q.empty


# ---------------------------------------------------------------------------
# WorkerPool
# ---------------------------------------------------------------------------


class TestWorkerPool:
    def test_basic_execution(self):
        pool = create_worker_pool(workers=2)
        pool.start()
        pool.submit("t1", lambda: 42)
        pool.submit("t2", lambda: "hello")
        pool.wait(timeout=5)
        pool.stop()

        r1 = pool.get_result("t1")
        r2 = pool.get_result("t2")
        assert r1 is not None
        assert r1.result == 42
        assert r2 is not None
        assert r2.result == "hello"

    def test_error_handling(self):
        pool = create_worker_pool(workers=1)
        pool.start()
        pool.submit("fail", lambda: 1 / 0)
        pool.wait(timeout=5)
        pool.stop()

        r = pool.get_result("fail")
        assert r is not None
        assert r.is_failure
        assert "division" in r.error.lower()

    def test_stats(self):
        pool = create_worker_pool(workers=2)
        pool.start()
        pool.submit("ok", lambda: 1)
        pool.submit("fail", lambda: 1 / 0)
        pool.wait(timeout=5)
        pool.stop()

        stats = pool.stats
        assert stats.total_tasks == 2
        assert stats.completed_tasks == 1
        assert stats.failed_tasks == 1

    def test_is_running(self):
        pool = create_worker_pool(workers=1)
        assert not pool.is_running
        pool.start()
        assert pool.is_running
        pool.stop()
        assert not pool.is_running

    def test_multiple_tasks(self):
        pool = create_worker_pool(workers=4)
        pool.start()
        for i in range(20):
            pool.submit(f"t{i}", lambda x=i: x * 2)
        pool.wait(timeout=10)
        pool.stop()

        results = pool.results
        assert len(results) == 20
        for i in range(20):
            assert results[f"t{i}"].result == i * 2


# ---------------------------------------------------------------------------
# parallel_map
# ---------------------------------------------------------------------------


class TestParallelMap:
    def test_basic(self):
        results = parallel_map(lambda x: x * 2, [1, 2, 3, 4, 5], workers=2)
        assert len(results) == 5
        values = [r.result for r in results if r.is_success]
        assert sorted(values) == [2, 4, 6, 8, 10]

    def test_with_errors(self):
        def process(x):
            if x == 0:
                raise ValueError("zero!")
            return 10 / x

        results = parallel_map(process, [2, 0, 5], workers=2)
        successes = [r for r in results if r.is_success]
        failures = [r for r in results if r.is_failure]
        assert len(successes) == 2
        assert len(failures) == 1


# ---------------------------------------------------------------------------
# Throttle
# ---------------------------------------------------------------------------


class TestThrottle:
    def test_basic(self):
        t = Throttle(interval_ms=100)
        r1 = t(lambda: "first")
        assert r1 == "first"
        r2 = t(lambda: "second")
        assert r2 is None  # throttled
        assert t.call_count == 1

    def test_after_interval(self):
        t = Throttle(interval_ms=50)
        t(lambda: "a")
        time.sleep(0.06)
        r = t(lambda: "b")
        assert r == "b"
        assert t.call_count == 2

    def test_reset(self):
        t = Throttle(interval_ms=1000)
        t(lambda: 1)
        t.reset()
        r = t(lambda: 2)
        assert r == 2


# ---------------------------------------------------------------------------
# Once
# ---------------------------------------------------------------------------


class TestOnce:
    def test_executes_once(self):
        once = Once()
        r1 = once(lambda: 42)
        r2 = once(lambda: 99)
        assert r1 == 42
        assert r2 == 42  # same result
        assert once.called

    def test_reset(self):
        once = Once()
        once(lambda: 1)
        once.reset()
        assert not once.called
        r = once(lambda: 2)
        assert r == 2

    def test_thread_safety(self):
        once = Once()
        results = []

        def worker():
            r = once(lambda: threading.current_thread().name)
            results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should have the same result
        assert len(set(results)) == 1


# ---------------------------------------------------------------------------
# Debouncer
# ---------------------------------------------------------------------------


class TestDebouncer:
    def test_basic(self):
        d = Debouncer(delay_ms=50)
        results = []
        d(lambda: results.append("call"))
        time.sleep(0.1)  # wait for debounce
        assert len(results) == 1

    def test_debounce_rapid(self):
        d = Debouncer(delay_ms=100)
        results = []
        # Rapid calls - only last should execute
        for i in range(5):
            d(lambda v=i: results.append(v))
            time.sleep(0.01)  # small gaps
        time.sleep(0.15)  # wait for debounce
        assert len(results) == 1
        assert results[0] == 4  # last call

    def test_cancel(self):
        d = Debouncer(delay_ms=100)
        results = []
        d(lambda: results.append("call"))
        d.cancel()
        time.sleep(0.15)
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestFactory:
    def test_create_worker_pool(self):
        pool = create_worker_pool(workers=2, queue_size=10)
        assert pool is not None

    def test_create_task_queue(self):
        q = create_task_queue(maxsize=5)
        assert q is not None

    def test_create_counter(self):
        c = create_counter(42)
        assert c.value == 42

    def test_create_atomic(self):
        v = create_atomic("test")
        assert v.value == "test"
