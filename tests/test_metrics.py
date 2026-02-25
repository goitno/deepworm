"""Tests for deepworm.metrics — research metrics tracking."""

import time

from deepworm.metrics import Metrics, MetricsCollector


def test_metrics_defaults():
    m = Metrics()
    assert m.api_calls == 0
    assert m.total_time == 0.0
    assert m.errors == 0


def test_metrics_to_dict():
    m = Metrics(api_calls=5, search_queries=10, errors=1)
    d = m.to_dict()
    assert d["api_calls"] == 5
    assert d["search_queries"] == 10
    assert d["errors"] == 1


def test_metrics_success_rate():
    m = Metrics(pages_fetched=8, pages_failed=2)
    assert m.success_rate == 0.8


def test_metrics_success_rate_zero():
    m = Metrics()
    assert m.success_rate == 0.0


def test_metrics_summary():
    m = Metrics(total_time=5.5, api_calls=3, search_queries=4, pages_fetched=10)
    s = m.summary
    assert "5.5s" in s
    assert "3" in s


def test_collector_increment():
    mc = MetricsCollector()
    mc.increment("api_calls")
    mc.increment("api_calls", 2)
    assert mc.metrics.api_calls == 3


def test_collector_record_error():
    mc = MetricsCollector()
    mc.record_error("timeout")
    mc.record_error("timeout")
    mc.record_error("parse")
    assert mc.metrics.errors == 3
    assert mc.metrics.error_types["timeout"] == 2
    assert mc.metrics.error_types["parse"] == 1


def test_collector_timer():
    mc = MetricsCollector()
    with mc.time("search"):
        time.sleep(0.05)
    assert mc.metrics.search_time >= 0.04


def test_collector_finalize():
    mc = MetricsCollector()
    mc.increment("api_calls", 5)
    result = mc.finalize()
    assert result.api_calls == 5
    assert result.total_time > 0
