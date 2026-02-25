"""Tests for deepworm.hooks – pipeline hooks and middleware."""

import pytest

from deepworm.hooks import (
    HookContext,
    HookEntry,
    HookRegistry,
    HookResult,
    HookStage,
    Pipeline,
    PipelineResult,
    create_middleware,
    create_pipeline,
    get_global_registry,
    hook,
)


# ---------------------------------------------------------------------------
# HookStage
# ---------------------------------------------------------------------------

class TestHookStage:
    def test_all_stages(self):
        assert len(HookStage) == 10
        names = {s.value for s in HookStage}
        assert "pre_research" in names
        assert "on_error" in names
        assert "on_complete" in names


# ---------------------------------------------------------------------------
# HookContext
# ---------------------------------------------------------------------------

class TestHookContext:
    def test_defaults(self):
        ctx = HookContext(stage=HookStage.PRE_RESEARCH)
        assert ctx.stage == HookStage.PRE_RESEARCH
        assert ctx.data == {}
        assert not ctx.cancelled

    def test_set_get(self):
        ctx = HookContext(stage=HookStage.PRE_ANALYSIS)
        ctx.set("key", 42)
        assert ctx.get("key") == 42
        assert ctx.get("missing", "default") == "default"

    def test_cancel(self):
        ctx = HookContext(stage=HookStage.PRE_EXPORT)
        ctx.cancel("not allowed")
        assert ctx.cancelled is True
        assert "not allowed" in ctx.errors


# ---------------------------------------------------------------------------
# HookEntry
# ---------------------------------------------------------------------------

class TestHookEntry:
    def test_to_dict(self):
        entry = HookEntry(
            name="my_hook",
            stage=HookStage.POST_RESEARCH,
            callback=lambda ctx: None,
            priority=5,
        )
        d = entry.to_dict()
        assert d["name"] == "my_hook"
        assert d["stage"] == "post_research"
        assert d["priority"] == 5
        assert d["enabled"] is True


# ---------------------------------------------------------------------------
# HookRegistry
# ---------------------------------------------------------------------------

class TestHookRegistry:
    def test_register_and_count(self):
        reg = HookRegistry()
        reg.register(HookStage.PRE_RESEARCH, lambda ctx: None, name="h1")
        assert reg.count == 1

    def test_unregister(self):
        reg = HookRegistry()
        reg.register(HookStage.PRE_ANALYSIS, lambda ctx: None, name="temp")
        assert reg.unregister("temp") == 1
        assert reg.count == 0

    def test_unregister_by_stage(self):
        reg = HookRegistry()
        reg.register(HookStage.PRE_ANALYSIS, lambda ctx: None, name="x")
        reg.register(HookStage.POST_ANALYSIS, lambda ctx: None, name="x")
        assert reg.unregister("x", HookStage.PRE_ANALYSIS) == 1
        assert reg.count == 1

    def test_enable_disable(self):
        reg = HookRegistry()
        reg.register(HookStage.PRE_RESEARCH, lambda ctx: None, name="h")
        assert reg.disable("h") == 1
        assert not reg.get_hooks(HookStage.PRE_RESEARCH)[0].enabled
        assert reg.enable("h") == 1
        assert reg.get_hooks(HookStage.PRE_RESEARCH)[0].enabled

    def test_clear_all(self):
        reg = HookRegistry()
        reg.register(HookStage.PRE_RESEARCH, lambda ctx: None)
        reg.register(HookStage.POST_EXPORT, lambda ctx: None)
        reg.clear()
        assert reg.count == 0

    def test_clear_stage(self):
        reg = HookRegistry()
        reg.register(HookStage.PRE_RESEARCH, lambda ctx: None)
        reg.register(HookStage.POST_EXPORT, lambda ctx: None)
        reg.clear(HookStage.PRE_RESEARCH)
        assert reg.count == 1

    def test_priority_order(self):
        reg = HookRegistry()
        order = []
        reg.register(HookStage.PRE_RESEARCH, lambda ctx: order.append(2), name="b", priority=2)
        reg.register(HookStage.PRE_RESEARCH, lambda ctx: order.append(1), name="a", priority=1)
        reg.execute(HookStage.PRE_RESEARCH)
        assert order == [1, 2]

    def test_execute_basic(self):
        reg = HookRegistry()
        reg.register(HookStage.PRE_ANALYSIS, lambda ctx: ctx.set("done", True) or ctx)
        ctx, result = reg.execute(HookStage.PRE_ANALYSIS)
        assert result.success
        assert result.hooks_run == 1

    def test_execute_disabled_skipped(self):
        reg = HookRegistry()
        entry = reg.register(HookStage.PRE_RESEARCH, lambda ctx: None, name="h")
        entry.enabled = False
        _, result = reg.execute(HookStage.PRE_RESEARCH)
        assert result.hooks_run == 0

    def test_execute_error_handling(self):
        reg = HookRegistry()
        def bad_hook(ctx):
            raise ValueError("boom")
        reg.register(HookStage.PRE_RESEARCH, bad_hook, name="bad")
        ctx, result = reg.execute(HookStage.PRE_RESEARCH)
        assert not result.success
        assert len(result.errors) == 1
        assert "boom" in result.errors[0]

    def test_execute_cancel(self):
        reg = HookRegistry()
        def cancel_hook(ctx):
            ctx.cancel("stop")
            return ctx
        reg.register(HookStage.PRE_RESEARCH, cancel_hook, name="c", priority=0)
        reg.register(HookStage.PRE_RESEARCH, lambda ctx: None, name="after", priority=1)
        ctx, result = reg.execute(HookStage.PRE_RESEARCH)
        assert result.cancelled
        assert result.hooks_run == 1  # second hook skipped

    def test_list_all(self):
        reg = HookRegistry()
        reg.register(HookStage.PRE_RESEARCH, lambda ctx: None, name="a")
        reg.register(HookStage.POST_EXPORT, lambda ctx: None, name="b")
        all_hooks = reg.list_all()
        assert len(all_hooks) == 2


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_basic_run(self):
        p = Pipeline(name="test")
        def research_step(ctx):
            ctx.set("researched", True)
            return ctx
        p.add_step("research", research_step)
        result = p.run(data={"topic": "AI"})
        assert result.success
        assert result.context.get("researched") is True

    def test_hooks_fire(self):
        p = Pipeline()
        fired = []
        p.registry.register(
            HookStage.PRE_RESEARCH,
            lambda ctx: fired.append("pre"),
            name="pre",
        )
        p.registry.register(
            HookStage.POST_RESEARCH,
            lambda ctx: fired.append("post"),
            name="post",
        )
        def research_step(ctx):
            fired.append("step")
            return ctx
        p.add_step("research", research_step)
        p.run()
        assert fired == ["pre", "step", "post"]

    def test_on_complete_always_fires(self):
        p = Pipeline()
        completed = []
        p.registry.register(
            HookStage.ON_COMPLETE,
            lambda ctx: completed.append(True),
        )
        p.run()
        assert completed == [True]

    def test_step_error_triggers_on_error(self):
        p = Pipeline()
        error_caught = []
        p.registry.register(
            HookStage.ON_ERROR,
            lambda ctx: error_caught.append(ctx.metadata.get("error")),
        )
        def bad_step(ctx):
            raise RuntimeError("fail")
        p.add_step("research", bad_step)
        result = p.run()
        assert not result.success
        assert len(error_caught) == 1
        assert "fail" in error_caught[0]

    def test_cancel_halts_pipeline(self):
        p = Pipeline()
        p.registry.register(
            HookStage.PRE_RESEARCH,
            lambda ctx: (ctx.cancel("no"), ctx)[-1],
        )
        steps_run = []
        def research_step(ctx):
            steps_run.append(True)
            return ctx
        p.add_step("research", research_step)
        result = p.run()
        assert not result.success
        assert steps_run == []

    def test_multiple_steps(self):
        p = Pipeline()
        def analysis_step(ctx):
            ctx.set("analyzed", True)
            return ctx
        def generation_step(ctx):
            ctx.set("generated", True)
            return ctx
        p.add_step("analysis", analysis_step)
        p.add_step("generation", generation_step)
        result = p.run()
        assert result.context.get("analyzed") is True
        assert result.context.get("generated") is True

    def test_duration_tracked(self):
        p = Pipeline()
        result = p.run()
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------

class TestPipelineResult:
    def test_to_dict(self):
        ctx = HookContext(stage=HookStage.ON_COMPLETE, data={"key": "val"})
        r = PipelineResult(context=ctx, duration_ms=123.45)
        d = r.to_dict()
        assert d["success"] is True
        assert d["duration_ms"] == 123.45
        assert "key" in d["data_keys"]


# ---------------------------------------------------------------------------
# create_pipeline helper
# ---------------------------------------------------------------------------

class TestCreatePipeline:
    def test_with_steps(self):
        def step_a(ctx):
            ctx.set("a", True)
            return ctx
        p = create_pipeline("p", steps=[("research", step_a)])
        result = p.run()
        assert result.context.get("a") is True

    def test_empty(self):
        p = create_pipeline()
        assert p.name == "default"
        result = p.run()
        assert result.success


# ---------------------------------------------------------------------------
# create_middleware
# ---------------------------------------------------------------------------

class TestMiddleware:
    def test_before_after(self):
        order = []
        @create_middleware(
            before=lambda ctx: order.append("before"),
            after=lambda ctx: order.append("after"),
        )
        def main_hook(ctx):
            order.append("main")
            return ctx

        ctx = HookContext(stage=HookStage.PRE_RESEARCH)
        main_hook(ctx)
        assert order == ["before", "main", "after"]

    def test_cancel_in_before(self):
        def cancel_before(ctx):
            ctx.cancel("stop")
            return ctx

        @create_middleware(before=cancel_before)
        def main_hook(ctx):
            ctx.set("reached", True)
            return ctx

        ctx = HookContext(stage=HookStage.PRE_RESEARCH)
        result = main_hook(ctx)
        assert result.cancelled
        assert result.get("reached") is None


# ---------------------------------------------------------------------------
# Global registry / decorator
# ---------------------------------------------------------------------------

class TestGlobalHook:
    def test_decorator_registers(self):
        reg = get_global_registry()
        initial = reg.count

        @hook(HookStage.POST_GENERATION, name="test_global")
        def my_hook(ctx):
            pass

        assert reg.count == initial + 1
        reg.unregister("test_global")
