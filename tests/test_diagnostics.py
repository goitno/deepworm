"""Tests for deepworm.diagnostics module."""

import time

import pytest

from deepworm.diagnostics import (
    CheckCategory,
    CheckResult,
    DependencyStatus,
    DiagnosticReport,
    EnvironmentInfo,
    HealthStatus,
    ProfileResult,
    Profiler,
    check_dependencies,
    collect_environment,
    create_profiler,
    quick_check,
    run_diagnostics,
    self_test,
)


# ---------------------------------------------------------------------------
# HealthStatus enum
# ---------------------------------------------------------------------------


class TestHealthStatus:
    def test_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_all_members(self):
        assert len(HealthStatus) == 4


# ---------------------------------------------------------------------------
# CheckCategory enum
# ---------------------------------------------------------------------------


class TestCheckCategory:
    def test_values(self):
        assert CheckCategory.SYSTEM.value == "system"
        assert CheckCategory.DEPENDENCY.value == "dependency"
        assert CheckCategory.CONFIGURATION.value == "configuration"
        assert CheckCategory.NETWORK.value == "network"
        assert CheckCategory.PERFORMANCE.value == "performance"
        assert CheckCategory.STORAGE.value == "storage"

    def test_all_members(self):
        assert len(CheckCategory) == 6


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_creation(self):
        r = CheckResult(
            name="test_check",
            category=CheckCategory.SYSTEM,
            status=HealthStatus.HEALTHY,
            message="All good",
        )
        assert r.name == "test_check"
        assert r.is_healthy

    def test_unhealthy(self):
        r = CheckResult(
            name="bad", category=CheckCategory.SYSTEM, status=HealthStatus.UNHEALTHY
        )
        assert not r.is_healthy

    def test_to_dict(self):
        r = CheckResult(
            name="t",
            category=CheckCategory.DEPENDENCY,
            status=HealthStatus.DEGRADED,
            message="msg",
            duration_ms=1.234,
            details={"k": "v"},
        )
        d = r.to_dict()
        assert d["name"] == "t"
        assert d["category"] == "dependency"
        assert d["status"] == "degraded"
        assert d["message"] == "msg"
        assert d["duration_ms"] == 1.23
        assert d["details"]["k"] == "v"

    def test_default_details_empty(self):
        r = CheckResult(name="x", category=CheckCategory.SYSTEM, status=HealthStatus.HEALTHY)
        assert r.details == {}
        assert r.duration_ms == 0.0


# ---------------------------------------------------------------------------
# DiagnosticReport
# ---------------------------------------------------------------------------


class TestDiagnosticReport:
    def test_empty_report(self):
        r = DiagnosticReport()
        assert r.overall_status == HealthStatus.UNKNOWN
        assert r.healthy_count == 0
        assert r.total_checks == 0

    def test_all_healthy(self):
        r = DiagnosticReport(
            checks=[
                CheckResult("a", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
                CheckResult("b", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
            ]
        )
        assert r.overall_status == HealthStatus.HEALTHY
        assert r.healthy_count == 2

    def test_degraded_overrides(self):
        r = DiagnosticReport(
            checks=[
                CheckResult("a", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
                CheckResult("b", CheckCategory.SYSTEM, HealthStatus.DEGRADED),
            ]
        )
        assert r.overall_status == HealthStatus.DEGRADED

    def test_unhealthy_overrides_all(self):
        r = DiagnosticReport(
            checks=[
                CheckResult("a", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
                CheckResult("b", CheckCategory.SYSTEM, HealthStatus.DEGRADED),
                CheckResult("c", CheckCategory.SYSTEM, HealthStatus.UNHEALTHY),
            ]
        )
        assert r.overall_status == HealthStatus.UNHEALTHY

    def test_by_category(self):
        r = DiagnosticReport(
            checks=[
                CheckResult("a", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
                CheckResult("b", CheckCategory.DEPENDENCY, HealthStatus.HEALTHY),
                CheckResult("c", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
            ]
        )
        assert len(r.by_category(CheckCategory.SYSTEM)) == 2
        assert len(r.by_category(CheckCategory.DEPENDENCY)) == 1
        assert len(r.by_category(CheckCategory.NETWORK)) == 0

    def test_by_status(self):
        r = DiagnosticReport(
            checks=[
                CheckResult("a", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
                CheckResult("b", CheckCategory.SYSTEM, HealthStatus.DEGRADED),
                CheckResult("c", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
            ]
        )
        assert len(r.by_status(HealthStatus.HEALTHY)) == 2
        assert len(r.by_status(HealthStatus.DEGRADED)) == 1

    def test_to_markdown(self):
        r = DiagnosticReport(
            checks=[
                CheckResult(
                    "pyver",
                    CheckCategory.SYSTEM,
                    HealthStatus.HEALTHY,
                    message="Python 3.11",
                    details={"version": "3.11"},
                ),
            ],
            total_duration_ms=5.0,
        )
        md = r.to_markdown()
        assert "# Diagnostic Report" in md
        assert "pyver" in md
        assert "healthy" in md

    def test_to_dict(self):
        r = DiagnosticReport(
            checks=[
                CheckResult("x", CheckCategory.SYSTEM, HealthStatus.HEALTHY),
            ],
            total_duration_ms=1.0,
        )
        d = r.to_dict()
        assert d["overall_status"] == "healthy"
        assert d["total_checks"] == 1


# ---------------------------------------------------------------------------
# ProfileResult
# ---------------------------------------------------------------------------


class TestProfileResult:
    def test_to_dict(self):
        pr = ProfileResult(
            name="func",
            iterations=100,
            total_ms=50.0,
            min_ms=0.3,
            max_ms=1.2,
            avg_ms=0.5,
            median_ms=0.45,
        )
        d = pr.to_dict()
        assert d["name"] == "func"
        assert d["iterations"] == 100

    def test_to_line(self):
        pr = ProfileResult("f", 10, 5.0, 0.1, 1.0, 0.5, 0.4)
        line = pr.to_line()
        assert "f:" in line
        assert "avg" in line
        assert "n=10" in line


# ---------------------------------------------------------------------------
# Profiler
# ---------------------------------------------------------------------------


class TestProfiler:
    def test_profile_basic(self):
        p = Profiler()

        def noop():
            pass

        result = p.profile(noop, iterations=10)
        assert result.name == "noop"
        assert result.iterations == 10
        assert result.total_ms >= 0
        assert result.min_ms <= result.avg_ms <= result.max_ms

    def test_profile_with_name(self):
        p = Profiler()
        result = p.profile(lambda: None, iterations=5, name="custom")
        assert result.name == "custom"

    def test_profile_with_args(self):
        p = Profiler()

        def add(a, b):
            return a + b

        result = p.profile(add, 1, 2, iterations=10)
        assert result.iterations == 10

    def test_results_accumulated(self):
        p = Profiler()
        p.profile(lambda: None, iterations=5, name="f1")
        p.profile(lambda: None, iterations=5, name="f2")
        assert len(p.results) == 2
        assert p.results[0].name == "f1"
        assert p.results[1].name == "f2"

    def test_summary(self):
        p = Profiler()
        p.profile(lambda: None, iterations=5, name="f1")
        s = p.summary()
        assert "Profile Summary" in s
        assert "f1" in s

    def test_reset(self):
        p = Profiler()
        p.profile(lambda: None, iterations=5, name="f1")
        assert len(p.results) == 1
        p.reset()
        assert len(p.results) == 0


# ---------------------------------------------------------------------------
# EnvironmentInfo
# ---------------------------------------------------------------------------


class TestEnvironmentInfo:
    def test_to_dict(self):
        env = EnvironmentInfo(
            python_version="3.11.0",
            platform_system="Darwin",
            platform_release="23.0",
            platform_machine="arm64",
            cpu_count=8,
            cwd="/tmp",
        )
        d = env.to_dict()
        assert d["python_version"] == "3.11.0"
        assert d["cpu_count"] == 8


# ---------------------------------------------------------------------------
# collect_environment
# ---------------------------------------------------------------------------


class TestCollectEnvironment:
    def test_basic(self):
        env = collect_environment()
        assert env.python_version != ""
        assert env.platform_system != ""
        assert env.cpu_count > 0
        assert env.cwd != ""

    def test_masks_secrets(self, monkeypatch):
        monkeypatch.setenv("DEEPWORM_API_KEY", "sk-verysecretvalue123")
        env = collect_environment()
        if "DEEPWORM_API_KEY" in env.env_vars:
            assert "verysecretvalue" not in env.env_vars["DEEPWORM_API_KEY"]
            assert "****" in env.env_vars["DEEPWORM_API_KEY"]


# ---------------------------------------------------------------------------
# DependencyStatus
# ---------------------------------------------------------------------------


class TestDependencyStatus:
    def test_to_dict(self):
        ds = DependencyStatus(
            name="httpx", required=True, installed=True, version="0.25.0"
        )
        d = ds.to_dict()
        assert d["name"] == "httpx"
        assert d["installed"] is True


# ---------------------------------------------------------------------------
# check_dependencies
# ---------------------------------------------------------------------------


class TestCheckDependencies:
    def test_returns_list(self):
        deps = check_dependencies()
        assert isinstance(deps, list)
        assert len(deps) > 0

    def test_has_names(self):
        deps = check_dependencies()
        names = {d.name for d in deps}
        assert "httpx" in names or "openai" in names  # at least one known dep


# ---------------------------------------------------------------------------
# run_diagnostics
# ---------------------------------------------------------------------------


class TestRunDiagnostics:
    def test_full_run(self):
        report = run_diagnostics()
        assert isinstance(report, DiagnosticReport)
        assert report.total_checks > 0
        assert report.total_duration_ms > 0

    def test_minimal_run(self):
        report = run_diagnostics(
            include_deps=False, include_disk=False, include_config=False
        )
        # Should have system checks only
        assert report.total_checks >= 2  # python_version + import

    def test_has_python_version_check(self):
        report = run_diagnostics(include_deps=False, include_disk=False, include_config=False)
        names = [c.name for c in report.checks]
        assert "python_version" in names

    def test_has_import_check(self):
        report = run_diagnostics(include_deps=False, include_disk=False, include_config=False)
        names = [c.name for c in report.checks]
        assert "import_deepworm" in names


# ---------------------------------------------------------------------------
# quick_check
# ---------------------------------------------------------------------------


class TestQuickCheck:
    def test_returns_dict(self):
        result = quick_check()
        assert isinstance(result, dict)
        assert "status" in result
        assert "healthy" in result
        assert "duration_ms" in result


# ---------------------------------------------------------------------------
# create_profiler
# ---------------------------------------------------------------------------


class TestCreateProfiler:
    def test_factory(self):
        p = create_profiler()
        assert isinstance(p, Profiler)
        assert len(p.results) == 0


# ---------------------------------------------------------------------------
# self_test
# ---------------------------------------------------------------------------


class TestSelfTest:
    def test_runs(self):
        report = self_test()
        assert isinstance(report, DiagnosticReport)
        assert report.total_checks >= 3  # import + readability + keywords + scoring + exports

    def test_checks_named(self):
        report = self_test()
        names = [c.name for c in report.checks]
        assert "self_import" in names

    def test_has_performance_checks(self):
        report = self_test()
        perf_checks = report.by_category(CheckCategory.PERFORMANCE)
        assert len(perf_checks) >= 1
