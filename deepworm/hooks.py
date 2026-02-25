"""Pipeline hooks and middleware for document processing.

Register pre/post-processing hooks at various lifecycle stages:
before/after research, analysis, generation, and export.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


class HookStage(Enum):
    """Processing pipeline stages."""
    PRE_RESEARCH = "pre_research"
    POST_RESEARCH = "post_research"
    PRE_ANALYSIS = "pre_analysis"
    POST_ANALYSIS = "post_analysis"
    PRE_GENERATION = "pre_generation"
    POST_GENERATION = "post_generation"
    PRE_EXPORT = "pre_export"
    POST_EXPORT = "post_export"
    ON_ERROR = "on_error"
    ON_COMPLETE = "on_complete"


@dataclass
class HookContext:
    """Context passed to hook functions."""

    stage: HookStage
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    cancelled: bool = False

    def cancel(self, reason: str = "") -> None:
        """Cancel further processing."""
        self.cancelled = True
        if reason:
            self.errors.append(reason)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


HookFunction = Callable[[HookContext], Optional[HookContext]]


@dataclass
class HookEntry:
    """A registered hook."""

    name: str
    stage: HookStage
    callback: HookFunction
    priority: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "stage": self.stage.value,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class HookResult:
    """Result of hook execution."""

    stage: HookStage
    hooks_run: int = 0
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    cancelled: bool = False

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 and not self.cancelled


class HookRegistry:
    """Central registry for lifecycle hooks."""

    def __init__(self) -> None:
        self._hooks: Dict[HookStage, List[HookEntry]] = {
            stage: [] for stage in HookStage
        }

    def register(
        self,
        stage: HookStage,
        callback: HookFunction,
        name: str = "",
        priority: int = 0,
    ) -> HookEntry:
        """Register a hook at a specific stage.

        Args:
            stage: Processing stage to hook into.
            callback: Function to call.
            name: Optional descriptive name.
            priority: Execution order (lower runs first).

        Returns:
            The registered HookEntry.
        """
        if not name:
            name = getattr(callback, "__name__", "anonymous")
        entry = HookEntry(
            name=name, stage=stage, callback=callback, priority=priority
        )
        self._hooks[stage].append(entry)
        self._hooks[stage].sort(key=lambda h: h.priority)
        return entry

    def unregister(self, name: str, stage: Optional[HookStage] = None) -> int:
        """Remove hooks by name, optionally filtered by stage.

        Returns:
            Number of hooks removed.
        """
        removed = 0
        stages = [stage] if stage else list(HookStage)
        for s in stages:
            before = len(self._hooks[s])
            self._hooks[s] = [h for h in self._hooks[s] if h.name != name]
            removed += before - len(self._hooks[s])
        return removed

    def enable(self, name: str) -> int:
        """Enable hooks by name. Returns count enabled."""
        count = 0
        for hooks in self._hooks.values():
            for h in hooks:
                if h.name == name and not h.enabled:
                    h.enabled = True
                    count += 1
        return count

    def disable(self, name: str) -> int:
        """Disable hooks by name. Returns count disabled."""
        count = 0
        for hooks in self._hooks.values():
            for h in hooks:
                if h.name == name and h.enabled:
                    h.enabled = False
                    count += 1
        return count

    def clear(self, stage: Optional[HookStage] = None) -> None:
        """Clear all hooks, optionally for a specific stage."""
        if stage:
            self._hooks[stage] = []
        else:
            for s in HookStage:
                self._hooks[s] = []

    def get_hooks(self, stage: HookStage) -> List[HookEntry]:
        """List hooks for a stage."""
        return list(self._hooks[stage])

    def execute(
        self,
        stage: HookStage,
        context: Optional[HookContext] = None,
    ) -> Tuple[HookContext, HookResult]:
        """Execute all hooks for a stage.

        Args:
            stage: The stage to execute.
            context: Optional context; created if not provided.

        Returns:
            Tuple of (final context, result).
        """
        if context is None:
            context = HookContext(stage=stage)
        else:
            context.stage = stage

        result = HookResult(stage=stage)
        start = time.monotonic()

        for entry in self._hooks[stage]:
            if not entry.enabled:
                continue
            if context.cancelled:
                result.cancelled = True
                break

            try:
                ret = entry.callback(context)
                if ret is not None:
                    context = ret
                result.hooks_run += 1
            except Exception as exc:
                msg = f"Hook '{entry.name}' failed: {exc}"
                result.errors.append(msg)
                context.errors.append(msg)

        result.duration_ms = (time.monotonic() - start) * 1000
        result.cancelled = context.cancelled
        return context, result

    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered hooks."""
        out: List[Dict[str, Any]] = []
        for stage in HookStage:
            for h in self._hooks[stage]:
                out.append(h.to_dict())
        return out

    @property
    def count(self) -> int:
        return sum(len(hooks) for hooks in self._hooks.values())


class Pipeline:
    """Composable processing pipeline with hook support."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.registry = HookRegistry()
        self._steps: List[Tuple[str, Callable[[HookContext], HookContext]]] = []

    def add_step(
        self,
        name: str,
        func: Callable[[HookContext], HookContext],
    ) -> None:
        """Add a processing step to the pipeline."""
        self._steps.append((name, func))

    def run(
        self,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """Execute the pipeline with hooks.

        Runs steps in order, executing PRE/POST hooks around each step.
        The ON_ERROR hook fires on exceptions, ON_COMPLETE always fires.
        """
        context = HookContext(
            stage=HookStage.PRE_RESEARCH,
            data=data or {},
            metadata=metadata or {},
        )
        results: List[HookResult] = []
        start = time.monotonic()

        try:
            for step_name, func in self._steps:
                # Pre-step
                pre_stage = _step_to_pre_stage(step_name)
                if pre_stage:
                    context, r = self.registry.execute(pre_stage, context)
                    results.append(r)
                    if context.cancelled:
                        break

                # Execute step
                try:
                    context = func(context)
                except Exception as exc:
                    context.errors.append(f"Step '{step_name}' failed: {exc}")
                    err_ctx = HookContext(
                        stage=HookStage.ON_ERROR,
                        data=context.data.copy(),
                        metadata={"error": str(exc), "step": step_name},
                    )
                    _, r = self.registry.execute(HookStage.ON_ERROR, err_ctx)
                    results.append(r)
                    break

                # Post-step
                post_stage = _step_to_post_stage(step_name)
                if post_stage:
                    context, r = self.registry.execute(post_stage, context)
                    results.append(r)
                    if context.cancelled:
                        break
        finally:
            # Always fire ON_COMPLETE
            _, r = self.registry.execute(HookStage.ON_COMPLETE, context)
            results.append(r)

        duration = (time.monotonic() - start) * 1000
        return PipelineResult(
            context=context,
            hook_results=results,
            duration_ms=duration,
        )


@dataclass
class PipelineResult:
    """Result of a full pipeline execution."""

    context: HookContext
    hook_results: List[HookResult] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        return not self.context.cancelled and len(self.context.errors) == 0

    @property
    def total_hooks_run(self) -> int:
        return sum(r.hooks_run for r in self.hook_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "duration_ms": round(self.duration_ms, 2),
            "total_hooks_run": self.total_hooks_run,
            "errors": self.context.errors,
            "data_keys": list(self.context.data.keys()),
        }


def _step_to_pre_stage(step_name: str) -> Optional[HookStage]:
    mapping = {
        "research": HookStage.PRE_RESEARCH,
        "analysis": HookStage.PRE_ANALYSIS,
        "generation": HookStage.PRE_GENERATION,
        "export": HookStage.PRE_EXPORT,
    }
    return mapping.get(step_name.lower())


def _step_to_post_stage(step_name: str) -> Optional[HookStage]:
    mapping = {
        "research": HookStage.POST_RESEARCH,
        "analysis": HookStage.POST_ANALYSIS,
        "generation": HookStage.POST_GENERATION,
        "export": HookStage.POST_EXPORT,
    }
    return mapping.get(step_name.lower())


# ---------------------------------------------------------------------------
# Convenience decorators
# ---------------------------------------------------------------------------

_global_registry = HookRegistry()


def hook(
    stage: HookStage,
    name: str = "",
    priority: int = 0,
) -> Callable[[HookFunction], HookFunction]:
    """Decorator to register a function as a global hook."""

    def decorator(func: HookFunction) -> HookFunction:
        _global_registry.register(stage, func, name=name or func.__name__, priority=priority)
        return func

    return decorator


def get_global_registry() -> HookRegistry:
    """Return the global hook registry."""
    return _global_registry


def create_pipeline(
    name: str = "default",
    steps: Optional[Sequence[Tuple[str, Callable]]] = None,
) -> Pipeline:
    """Create a pipeline with optional initial steps."""
    p = Pipeline(name=name)
    if steps:
        for step_name, func in steps:
            p.add_step(step_name, func)
    return p


def create_middleware(
    before: Optional[HookFunction] = None,
    after: Optional[HookFunction] = None,
) -> Callable[[HookFunction], HookFunction]:
    """Create a middleware wrapper that runs before/after a hook."""

    def decorator(func: HookFunction) -> HookFunction:
        def wrapper(ctx: HookContext) -> Optional[HookContext]:
            if before:
                ret = before(ctx)
                if ret is not None:
                    ctx = ret
                if ctx.cancelled:
                    return ctx
            result = func(ctx)
            if result is not None:
                ctx = result
            if after:
                ret = after(ctx)
                if ret is not None:
                    ctx = ret
            return ctx

        wrapper.__name__ = getattr(func, "__name__", "wrapped")
        return wrapper

    return decorator
