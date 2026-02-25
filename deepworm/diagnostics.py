"""Diagnostics and health checking for the deepworm system.

Provides system health checks, dependency verification, performance profiling,
environment diagnostics, and self-test capabilities.
"""

from __future__ import annotations

import os
import platform
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckCategory(Enum):
    """Categories for diagnostic checks."""

    SYSTEM = "system"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PERFORMANCE = "performance"
    STORAGE = "storage"


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""

    name: str
    category: CheckCategory
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
            "details": self.details,
        }


@dataclass
class DiagnosticReport:
    """Full diagnostic report."""

    checks: List[CheckResult] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    total_duration_ms: float = 0.0

    @property
    def overall_status(self) -> HealthStatus:
        if not self.checks:
            return HealthStatus.UNKNOWN
        if any(c.status == HealthStatus.UNHEALTHY for c in self.checks):
            return HealthStatus.UNHEALTHY
        if any(c.status == HealthStatus.DEGRADED for c in self.checks):
            return HealthStatus.DEGRADED
        if all(c.status == HealthStatus.HEALTHY for c in self.checks):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.checks if c.is_healthy)

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    def by_category(self, category: CheckCategory) -> List[CheckResult]:
        return [c for c in self.checks if c.category == category]

    def by_status(self, status: HealthStatus) -> List[CheckResult]:
        return [c for c in self.checks if c.status == status]

    def to_markdown(self) -> str:
        lines = ["# Diagnostic Report", ""]
        lines.append(f"- **Overall status**: {self.overall_status.value}")
        lines.append(f"- **Checks**: {self.healthy_count}/{self.total_checks} healthy")
        lines.append(f"- **Duration**: {self.total_duration_ms:.1f}ms")
        lines.append("")

        # Group by category
        categories = sorted(set(c.category for c in self.checks), key=lambda c: c.value)
        for cat in categories:
            lines.append(f"## {cat.value.title()}")
            lines.append("")
            for check in self.by_category(cat):
                icon = "✓" if check.is_healthy else "✗"
                lines.append(f"- {icon} **{check.name}**: {check.status.value}")
                if check.message:
                    lines.append(f"  - {check.message}")
                if check.details:
                    for k, v in check.details.items():
                        lines.append(f"  - {k}: {v}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "healthy_count": self.healthy_count,
            "total_checks": self.total_checks,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "checks": [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# Profile timer
# ---------------------------------------------------------------------------

@dataclass
class ProfileResult:
    """Result of performance profiling."""

    name: str
    iterations: int
    total_ms: float
    min_ms: float
    max_ms: float
    avg_ms: float
    median_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_ms": round(self.total_ms, 3),
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "avg_ms": round(self.avg_ms, 3),
            "median_ms": round(self.median_ms, 3),
        }

    def to_line(self) -> str:
        return (
            f"{self.name}: {self.avg_ms:.3f}ms avg "
            f"(min={self.min_ms:.3f}, max={self.max_ms:.3f}, "
            f"n={self.iterations})"
        )


class Profiler:
    """Simple performance profiler for benchmarking functions."""

    def __init__(self) -> None:
        self._results: List[ProfileResult] = []

    def profile(
        self,
        func: Callable,
        *args: Any,
        iterations: int = 100,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> ProfileResult:
        """Profile a function over multiple iterations."""
        name = name or getattr(func, "__name__", "unknown")
        timings: List[float] = []

        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            timings.append(elapsed)

        timings.sort()
        result = ProfileResult(
            name=name,
            iterations=iterations,
            total_ms=sum(timings),
            min_ms=timings[0],
            max_ms=timings[-1],
            avg_ms=sum(timings) / len(timings),
            median_ms=timings[len(timings) // 2],
        )
        self._results.append(result)
        return result

    @property
    def results(self) -> List[ProfileResult]:
        return list(self._results)

    def summary(self) -> str:
        lines = ["Profile Summary", "=" * 60]
        for r in self._results:
            lines.append(r.to_line())
        return "\n".join(lines)

    def reset(self) -> None:
        self._results.clear()


# ---------------------------------------------------------------------------
# Environment info
# ---------------------------------------------------------------------------

@dataclass
class EnvironmentInfo:
    """System and runtime environment information."""

    python_version: str = ""
    platform_system: str = ""
    platform_release: str = ""
    platform_machine: str = ""
    cpu_count: int = 0
    cwd: str = ""
    env_vars: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "python_version": self.python_version,
            "platform_system": self.platform_system,
            "platform_release": self.platform_release,
            "platform_machine": self.platform_machine,
            "cpu_count": self.cpu_count,
            "cwd": self.cwd,
            "env_vars": self.env_vars,
        }


def collect_environment() -> EnvironmentInfo:
    """Collect current environment information."""
    # Collect deepworm-related env vars
    dw_vars = {}
    for key, value in os.environ.items():
        lower = key.lower()
        if lower.startswith("deepworm") or lower.endswith("api_key"):
            # Mask secrets
            if "key" in lower or "secret" in lower or "token" in lower:
                dw_vars[key] = value[:4] + "****" if len(value) > 4 else "****"
            else:
                dw_vars[key] = value

    return EnvironmentInfo(
        python_version=sys.version,
        platform_system=platform.system(),
        platform_release=platform.release(),
        platform_machine=platform.machine(),
        cpu_count=os.cpu_count() or 0,
        cwd=os.getcwd(),
        env_vars=dw_vars,
    )


# ---------------------------------------------------------------------------
# Dependency checker
# ---------------------------------------------------------------------------

@dataclass
class DependencyStatus:
    """Status of a single dependency."""

    name: str
    required: bool
    installed: bool
    version: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "required": self.required,
            "installed": self.installed,
            "version": self.version,
            "error": self.error,
        }


def check_dependencies() -> List[DependencyStatus]:
    """Check all deepworm dependencies."""
    deps: List[Tuple[str, bool]] = [
        ("httpx", True),
        ("rich", True),
        ("openai", True),
        ("anthropic", False),
        ("yaml", False),
        ("pydantic", False),
    ]

    results = []
    for name, required in deps:
        try:
            mod = __import__(name)
            version = getattr(mod, "__version__", "unknown")
            results.append(DependencyStatus(
                name=name, required=required, installed=True, version=version,
            ))
        except ImportError as e:
            results.append(DependencyStatus(
                name=name, required=required, installed=False, error=str(e),
            ))

    return results


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

def _check_python_version() -> CheckResult:
    """Check Python version compatibility."""
    start = time.perf_counter()
    version = sys.version_info
    if version >= (3, 9):
        status = HealthStatus.HEALTHY
        msg = f"Python {version.major}.{version.minor}.{version.micro}"
    elif version >= (3, 8):
        status = HealthStatus.DEGRADED
        msg = f"Python {version.major}.{version.minor} — 3.9+ recommended"
    else:
        status = HealthStatus.UNHEALTHY
        msg = f"Python {version.major}.{version.minor} — 3.9+ required"
    elapsed = (time.perf_counter() - start) * 1000
    return CheckResult(
        name="python_version",
        category=CheckCategory.SYSTEM,
        status=status,
        message=msg,
        duration_ms=elapsed,
        details={"version": f"{version.major}.{version.minor}.{version.micro}"},
    )


def _check_import() -> CheckResult:
    """Check that deepworm can be imported."""
    start = time.perf_counter()
    try:
        import deepworm
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult(
            name="import_deepworm",
            category=CheckCategory.SYSTEM,
            status=HealthStatus.HEALTHY,
            message=f"deepworm {deepworm.__version__}",
            duration_ms=elapsed,
            details={"version": deepworm.__version__},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult(
            name="import_deepworm",
            category=CheckCategory.SYSTEM,
            status=HealthStatus.UNHEALTHY,
            message=f"Import failed: {e}",
            duration_ms=elapsed,
        )


def _check_dependencies() -> List[CheckResult]:
    """Check dependency health."""
    results = []
    deps = check_dependencies()
    for dep in deps:
        if dep.installed:
            status = HealthStatus.HEALTHY
            msg = f"{dep.name} {dep.version}"
        elif dep.required:
            status = HealthStatus.UNHEALTHY
            msg = f"{dep.name} not installed (required)"
        else:
            status = HealthStatus.DEGRADED
            msg = f"{dep.name} not installed (optional)"
        results.append(CheckResult(
            name=f"dep_{dep.name}",
            category=CheckCategory.DEPENDENCY,
            status=status,
            message=msg,
        ))
    return results


def _check_disk_space() -> CheckResult:
    """Check available disk space."""
    start = time.perf_counter()
    try:
        stat = os.statvfs(os.getcwd())
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        elapsed = (time.perf_counter() - start) * 1000

        if free_gb > 1.0:
            status = HealthStatus.HEALTHY
        elif free_gb > 0.1:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        return CheckResult(
            name="disk_space",
            category=CheckCategory.STORAGE,
            status=status,
            message=f"{free_gb:.1f} GB free",
            duration_ms=elapsed,
            details={"free_gb": round(free_gb, 2)},
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckResult(
            name="disk_space",
            category=CheckCategory.STORAGE,
            status=HealthStatus.UNKNOWN,
            message=str(e),
            duration_ms=elapsed,
        )


def _check_env_config() -> CheckResult:
    """Check environment configuration."""
    start = time.perf_counter()
    env = collect_environment()
    issues: List[str] = []

    # Check for at least one API key
    has_provider = any(
        k in os.environ
        for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    )

    if has_provider:
        status = HealthStatus.HEALTHY
        msg = "API key configured"
    else:
        status = HealthStatus.DEGRADED
        msg = "No API key found; use Ollama or set OPENAI_API_KEY"

    elapsed = (time.perf_counter() - start) * 1000
    return CheckResult(
        name="env_config",
        category=CheckCategory.CONFIGURATION,
        status=status,
        message=msg,
        duration_ms=elapsed,
        details={"platform": env.platform_system},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_diagnostics(
    include_deps: bool = True,
    include_disk: bool = True,
    include_config: bool = True,
) -> DiagnosticReport:
    """Run a full diagnostic check.

    Returns a DiagnosticReport with results of all checks.
    """
    start = time.perf_counter()
    report = DiagnosticReport()

    # System checks
    report.checks.append(_check_python_version())
    report.checks.append(_check_import())

    # Dependencies
    if include_deps:
        report.checks.extend(_check_dependencies())

    # Storage
    if include_disk:
        report.checks.append(_check_disk_space())

    # Configuration
    if include_config:
        report.checks.append(_check_env_config())

    report.total_duration_ms = (time.perf_counter() - start) * 1000
    return report


def quick_check() -> Dict[str, str]:
    """Run a quick health check and return summary dict."""
    report = run_diagnostics(include_deps=False, include_disk=False, include_config=False)
    return {
        "status": report.overall_status.value,
        "healthy": f"{report.healthy_count}/{report.total_checks}",
        "duration_ms": f"{report.total_duration_ms:.1f}",
    }


def create_profiler() -> Profiler:
    """Create a new profiler instance."""
    return Profiler()


def self_test() -> DiagnosticReport:
    """Run self-tests to verify deepworm is working correctly.

    Imports and instantiates key components to verify functionality.
    """
    start = time.perf_counter()
    report = DiagnosticReport()

    # Test 1: Import
    try:
        import deepworm
        report.checks.append(CheckResult(
            name="self_import",
            category=CheckCategory.SYSTEM,
            status=HealthStatus.HEALTHY,
            message=f"v{deepworm.__version__}",
        ))
    except Exception as e:
        report.checks.append(CheckResult(
            name="self_import",
            category=CheckCategory.SYSTEM,
            status=HealthStatus.UNHEALTHY,
            message=str(e),
        ))
        report.total_duration_ms = (time.perf_counter() - start) * 1000
        return report

    # Test 2: Readability
    test_start = time.perf_counter()
    try:
        from deepworm.readability import analyze_readability
        result = analyze_readability("This is a test document for diagnostic purposes.")
        assert result.flesch_ease is not None
        duration = (time.perf_counter() - test_start) * 1000
        report.checks.append(CheckResult(
            name="self_readability",
            category=CheckCategory.PERFORMANCE,
            status=HealthStatus.HEALTHY,
            message="Readability analysis works",
            duration_ms=duration,
        ))
    except Exception as e:
        duration = (time.perf_counter() - test_start) * 1000
        report.checks.append(CheckResult(
            name="self_readability",
            category=CheckCategory.PERFORMANCE,
            status=HealthStatus.UNHEALTHY,
            message=str(e),
            duration_ms=duration,
        ))

    # Test 3: Keywords
    test_start = time.perf_counter()
    try:
        from deepworm.keywords import extract_keywords
        keywords = extract_keywords("Machine learning is a subset of artificial intelligence.")
        assert len(keywords.keywords) > 0
        duration = (time.perf_counter() - test_start) * 1000
        report.checks.append(CheckResult(
            name="self_keywords",
            category=CheckCategory.PERFORMANCE,
            status=HealthStatus.HEALTHY,
            message="Keyword extraction works",
            duration_ms=duration,
        ))
    except Exception as e:
        duration = (time.perf_counter() - test_start) * 1000
        report.checks.append(CheckResult(
            name="self_keywords",
            category=CheckCategory.PERFORMANCE,
            status=HealthStatus.UNHEALTHY,
            message=str(e),
            duration_ms=duration,
        ))

    # Test 4: Scoring
    test_start = time.perf_counter()
    try:
        from deepworm.scoring import score_report
        score = score_report("# Title\n\nSome content here.\n\n## Section\n\nMore content.")
        assert score.overall >= 0
        duration = (time.perf_counter() - test_start) * 1000
        report.checks.append(CheckResult(
            name="self_scoring",
            category=CheckCategory.PERFORMANCE,
            status=HealthStatus.HEALTHY,
            message=f"Scoring works (grade: {score.grade})",
            duration_ms=duration,
        ))
    except Exception as e:
        duration = (time.perf_counter() - test_start) * 1000
        report.checks.append(CheckResult(
            name="self_scoring",
            category=CheckCategory.PERFORMANCE,
            status=HealthStatus.UNHEALTHY,
            message=str(e),
            duration_ms=duration,
        ))

    # Test 5: Export count
    test_start = time.perf_counter()
    try:
        import deepworm
        export_count = len(deepworm.__all__)
        duration = (time.perf_counter() - test_start) * 1000
        report.checks.append(CheckResult(
            name="self_exports",
            category=CheckCategory.SYSTEM,
            status=HealthStatus.HEALTHY,
            message=f"{export_count} public exports",
            duration_ms=duration,
            details={"export_count": export_count},
        ))
    except Exception as e:
        duration = (time.perf_counter() - test_start) * 1000
        report.checks.append(CheckResult(
            name="self_exports",
            category=CheckCategory.SYSTEM,
            status=HealthStatus.UNHEALTHY,
            message=str(e),
            duration_ms=duration,
        ))

    report.total_duration_ms = (time.perf_counter() - start) * 1000
    return report
