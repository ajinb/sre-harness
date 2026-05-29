"""Runnable, offline demo: an SRE agent triaging a CrashLoopBackOff.

    python examples/triage_demo.py

It runs twice to show the guardrail boundary:

  1. read-only run  — the agent gathers evidence and concludes. The mutating
     restart_pod tool is NOT in the allowlist, so it can't be called.
  2. remediation run — a more eager model gathers evidence and then tries to
     restart_pod. The tool is allowed, but the approver denies it, so the
     harness refuses the mutation and records the refusal on the trace.

No API key, no network. Swap the model for AnthropicModel to use real Claude.
"""

from __future__ import annotations

from sre_harness import Action, FakeModel, Guardrails, Harness, Tracer, default_registry


class EagerRemediationModel:
    """Gathers the same evidence, then attempts a restart (which gets refused)."""

    def decide(self, context: str, tool_catalog: str) -> Action:
        if "list_pods" not in context:
            return Action(tool="list_pods", args={"namespace": "default"})
        if "get_metrics" not in context:
            return Action(tool="get_metrics", args={"pod": "checkout-7f9c"})
        if "restart_pod" not in context:
            return Action(tool="restart_pod", args={"pod": "checkout-7f9c"})
        return Action(final="I tried to restart checkout-7f9c but was not allowed to.")


def run(label: str, model, allowed: set[str], approver=None) -> None:
    print(f"\n=== {label} ===")
    tracer = Tracer(sink=print)
    kwargs = {"allowed_tools": allowed}
    if approver is not None:
        kwargs["approver"] = approver
    harness = Harness(
        model=model,
        registry=default_registry(),
        guardrails=Guardrails(**kwargs),
        tracer=tracer,
    )
    result = harness.run("checkout-7f9c is flapping — what's wrong and what should we do?")
    print("\n--- result ---")
    print("verified:", result.verified)
    print("answer:", result.answer)


if __name__ == "__main__":
    # 1. Read-only investigation: restart_pod is not granted at all.
    run("read-only triage", FakeModel(), allowed={"list_pods", "get_metrics", "get_logs"})

    # 2. Eager model tries to restart; write tool granted but approver says no.
    run(
        "remediation attempt, approval denied",
        EagerRemediationModel(),
        allowed={"list_pods", "get_metrics", "restart_pod"},
        approver=lambda spec, args: False,
    )
