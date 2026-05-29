"""The model: the reasoning core the harness wraps.

The harness depends only on the `Model` protocol — one `decide` method that
takes the rendered context plus the tool catalog and returns the next Action.
This is the seam that makes "Agent = Model + Harness" literal: swap the model
and the harness is unchanged.

Two implementations ship here:

- FakeModel: deterministic, offline, and used by the demo and tests. It runs a
  realistic memory-pressure triage (list -> metrics -> logs -> conclude) with
  no API key and no network.
- AnthropicModel: a thin adapter showing where a real Claude call slots in. It
  is import-light so the package works without the SDK installed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Action:
    """Either a tool call (tool set) or a final answer (final set)."""

    tool: str | None = None
    args: dict[str, Any] | None = None
    final: str | None = None

    @property
    def is_final(self) -> bool:
        return self.final is not None


class Model(Protocol):
    def decide(self, context: str, tool_catalog: str) -> Action: ...


class FakeModel:
    """Deterministic triage policy driven by what's already in context."""

    def decide(self, context: str, tool_catalog: str) -> Action:
        if "list_pods" not in context:
            return Action(tool="list_pods", args={"namespace": "default"})
        if "get_metrics" not in context:
            return Action(tool="get_metrics", args={"pod": "checkout-7f9c"})
        if "get_logs" not in context:
            return Action(tool="get_logs", args={"pod": "checkout-7f9c", "lines": 5})
        return Action(
            final=(
                "checkout-7f9c is in CrashLoopBackOff from an OOMKill: memory at 97% with "
                "3 OOM kills, and logs show 'OutOfMemoryError: Java heap space' against a "
                "512Mi limit. Likely cause is an undersized heap/limit, not a transient "
                "fault. Recommend raising the memory limit and JVM heap, then redeploying. "
                "A restart alone will not fix it — it will crash again."
            )
        )


class AnthropicModel:
    """Adapter for a real Claude call. Requires `anthropic` to be installed."""

    def __init__(self, model: str = "claude-opus-4-7", max_tokens: int = 1024) -> None:
        self.model = model
        self.max_tokens = max_tokens

    def decide(self, context: str, tool_catalog: str) -> Action:
        from anthropic import Anthropic  # imported lazily

        client = Anthropic()
        system = (
            "You are an SRE diagnostic agent. You may ONLY act by emitting a single "
            "JSON object and nothing else. To call a tool: "
            '{"tool": "<name>", "args": {...}}. To finish: {"final": "<diagnosis>"}.\n'
            f"Available tools:\n{tool_catalog}\n"
            "Gather evidence with read-only tools before concluding. Never restart or "
            "mutate anything unless the evidence proves it is the fix."
        )
        resp = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": context}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return parse_action(text)


def parse_action(text: str) -> Action:
    """Parse a model's JSON action, tolerating surrounding prose/fences."""

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return Action(final=text.strip())
    obj = json.loads(text[start : end + 1])
    if "final" in obj:
        return Action(final=str(obj["final"]))
    return Action(tool=obj.get("tool"), args=obj.get("args") or {})
