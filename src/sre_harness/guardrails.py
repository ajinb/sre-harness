"""Guardrails: the safety rails between the model's intent and the real world.

Three independent rails, checked in order before any tool runs:

1. Step budget   — a hard ceiling on how many actions the loop may take, so a
                   confused agent burns out instead of running forever.
2. Allowlist     — the agent may only call tools that were explicitly granted
                   for this run. An unknown or ungranted tool is refused.
3. Approval gate — mutating tools require a human (or policy) to approve the
                   *specific* call. Read-only tools pass freely.

Each rail returns a Decision; the harness records all of them on the trace,
so a refusal is as auditable as an allow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .tools import ToolSpec


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


# An Approver receives the tool and its arguments and returns True to allow.
Approver = Callable[[ToolSpec, dict[str, Any]], bool]


def deny_all_writes(spec: ToolSpec, args: dict[str, Any]) -> bool:
    return False


class Guardrails:
    def __init__(
        self,
        allowed_tools: set[str],
        approver: Approver = deny_all_writes,
        step_budget: int = 12,
    ) -> None:
        self.allowed_tools = allowed_tools
        self.approver = approver
        self.step_budget = step_budget
        self.steps_used = 0

    def check_budget(self) -> Decision:
        if self.steps_used >= self.step_budget:
            return Decision(False, f"step budget exhausted ({self.step_budget})")
        return Decision(True, "within budget")

    def authorize(self, spec: ToolSpec, args: dict[str, Any]) -> Decision:
        if spec.name not in self.allowed_tools:
            return Decision(False, f"tool '{spec.name}' not in allowlist")
        if spec.mutating and not self.approver(spec, args):
            return Decision(False, f"mutating tool '{spec.name}' was not approved")
        return Decision(True, "authorized")

    def record_step(self) -> None:
        self.steps_used += 1
