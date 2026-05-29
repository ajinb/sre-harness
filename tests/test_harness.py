from __future__ import annotations

from sre_harness import (
    Action,
    FakeModel,
    Guardrails,
    Harness,
    Tracer,
    default_registry,
    parse_action,
)
from sre_harness.model import Model


def make_harness(allowed: set[str], approver=None, model: Model | None = None) -> Harness:
    kwargs = {"allowed_tools": allowed}
    if approver is not None:
        kwargs["approver"] = approver
    return Harness(
        model=model or FakeModel(),
        registry=default_registry(),
        guardrails=Guardrails(**kwargs),
        tracer=Tracer(),
    )


def test_readonly_run_gathers_evidence_and_verifies():
    h = make_harness({"list_pods", "get_metrics", "get_logs"})
    result = h.run("triage checkout-7f9c")
    assert result.answer is not None
    assert result.verified  # all verifiers pass
    assert "OutOfMemoryError" in result.answer
    # all three read tools fired
    assert len(h.tracer.of_kind("tool_result")) == 3


def test_ungranted_mutating_tool_is_refused():
    # restart_pod not in allowlist; FakeModel never calls it anyway, but a
    # model that did would be refused.
    h = make_harness({"list_pods"}, model=_RestartHappyModel())
    result = h.run("restart it")
    refusals = h.tracer.of_kind("tool_refused")
    assert any("allowlist" in e.data["reason"] for e in refusals)
    assert result.answer is not None


def test_mutating_tool_requires_approval():
    h = make_harness(
        {"restart_pod"}, approver=lambda spec, args: False, model=_RestartHappyModel()
    )
    h.run("restart it")
    refusals = h.tracer.of_kind("tool_refused")
    assert any("not approved" in e.data["reason"] for e in refusals)


def test_approved_mutation_executes():
    h = make_harness(
        {"restart_pod"}, approver=lambda spec, args: True, model=_RestartHappyModel()
    )
    h.run("restart it")
    results = h.tracer.of_kind("tool_result")
    assert any(e.data["tool"] == "restart_pod" and e.data["approved"] for e in results)


def test_step_budget_stops_runaway():
    h = make_harness({"list_pods"}, model=_LoopForeverModel())
    h.guardrails.step_budget = 3
    result = h.run("loop")
    assert result.answer is None
    assert "budget" in result.stopped_reason


def test_evidence_required_verifier_fails_with_no_reads():
    h = make_harness(set(), model=_ImmediateFinalModel())
    result = h.run("guess")
    assert result.answer is not None
    assert not result.verified
    ev = next(v for v in result.verifications if v.name == "evidence_required")
    assert not ev.passed


def test_parse_action_tolerates_fences_and_prose():
    a = parse_action('Sure! ```json\n{"tool": "list_pods", "args": {}}\n```')
    assert a.tool == "list_pods"
    b = parse_action('{"final": "done"}')
    assert b.is_final and b.final == "done"
    c = parse_action("no json here")
    assert c.is_final and c.final == "no json here"


class _RestartHappyModel:
    def decide(self, context: str, tool_catalog: str) -> Action:
        if "restart_pod" in context:  # already tried/observed
            return Action(final="tried to restart")
        return Action(tool="restart_pod", args={"pod": "checkout-7f9c"})


class _LoopForeverModel:
    def decide(self, context: str, tool_catalog: str) -> Action:
        return Action(tool="list_pods", args={})


class _ImmediateFinalModel:
    def decide(self, context: str, tool_catalog: str) -> Action:
        return Action(final="it's definitely fine, trust me")
