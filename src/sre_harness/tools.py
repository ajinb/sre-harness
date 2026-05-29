"""Tool orchestration: the registry the agent selects from, and the example
SRE tools it can call.

Each tool declares whether it is read-only or mutating. That single flag is
what the guardrail layer keys off of: read-only tools run freely, mutating
tools route through an approval gate. The agent never decides on its own
whether an action is safe — the tool's own declaration does.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    fn: Callable[..., Any]
    mutating: bool = False

    def __call__(self, **kwargs: Any) -> Any:
        return self.fn(**kwargs)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def catalog(self) -> str:
        lines = []
        for name in self.names():
            spec = self._tools[name]
            kind = "MUTATING" if spec.mutating else "read-only"
            lines.append(f"- {name} ({kind}): {spec.description}")
        return "\n".join(lines)


# --- Example SRE tools. In a real harness these wrap your metrics backend,
# --- log store, and orchestrator. Here they read from a fixed fixture so the
# --- demo and tests run offline and deterministically.

_FIXTURE = {
    "pods": [
        {"name": "checkout-7f9c", "status": "CrashLoopBackOff", "restarts": 14},
        {"name": "checkout-2a1b", "status": "Running", "restarts": 0},
    ],
    "metrics": {"checkout-7f9c": {"cpu": 0.92, "mem": 0.97, "oom_kills": 3}},
    "logs": {
        "checkout-7f9c": [
            "FATAL: java.lang.OutOfMemoryError: Java heap space",
            "Container exceeded memory limit (512Mi), killed by cgroup",
        ]
    },
}


def list_pods(namespace: str = "default") -> list[dict[str, Any]]:
    return _FIXTURE["pods"]


def get_metrics(pod: str) -> dict[str, Any]:
    return _FIXTURE["metrics"].get(pod, {})


def get_logs(pod: str, lines: int = 20) -> list[str]:
    return _FIXTURE["logs"].get(pod, [])[:lines]


def restart_pod(pod: str) -> dict[str, Any]:
    # Mutating: the harness will not reach this without an approval.
    return {"pod": pod, "action": "restarted", "ok": True}


def default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolSpec("list_pods", "List pods and their status in a namespace.", list_pods))
    reg.register(ToolSpec("get_metrics", "CPU/mem/OOM stats for one pod.", get_metrics))
    reg.register(ToolSpec("get_logs", "Recent log lines for one pod.", get_logs))
    reg.register(
        ToolSpec("restart_pod", "Restart a pod. Mutating.", restart_pod, mutating=True)
    )
    return reg
