"""Direct unit tests for the three guardrail rails."""

from __future__ import annotations

from sre_harness.guardrails import Guardrails
from sre_harness.tools import ToolSpec


def _spec(name: str, mutating: bool = False) -> ToolSpec:
    return ToolSpec(name=name, description="x", fn=lambda **_: None, mutating=mutating)


def test_read_tool_in_allowlist_is_authorized():
    g = Guardrails(allowed_tools={"list_pods"})
    assert g.authorize(_spec("list_pods"), {}).allowed


def test_tool_outside_allowlist_is_denied():
    g = Guardrails(allowed_tools={"list_pods"})
    d = g.authorize(_spec("restart_pod", mutating=True), {})
    assert not d.allowed
    assert "allowlist" in d.reason


def test_mutating_tool_denied_without_approval():
    g = Guardrails(allowed_tools={"restart_pod"}, approver=lambda spec, args: False)
    d = g.authorize(_spec("restart_pod", mutating=True), {})
    assert not d.allowed
    assert "not approved" in d.reason


def test_mutating_tool_allowed_when_approved():
    g = Guardrails(allowed_tools={"restart_pod"}, approver=lambda spec, args: True)
    assert g.authorize(_spec("restart_pod", mutating=True), {}).allowed


def test_budget_blocks_once_exhausted():
    g = Guardrails(allowed_tools=set(), step_budget=2)
    assert g.check_budget().allowed
    g.record_step()
    g.record_step()
    assert not g.check_budget().allowed
