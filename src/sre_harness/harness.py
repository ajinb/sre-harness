"""The harness loop: Agent = Model + Harness.

This is the ~40 lines that turn a model into a reliable agent. On each step it:

  1. checks the step budget          (guardrail)
  2. asks the model for an Action    (model + context/memory)
  3. authorizes the action           (guardrail: allowlist + approval gate)
  4. executes the tool               (tool orchestration)
  5. records an observation          (context/memory)
  ... and emits a trace event at every decision point (observability).

When the model returns a final answer, the loop runs the verifiers
(verification) before handing the result back. Nothing here is model-specific:
the same loop runs FakeModel offline or a real Claude call.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .guardrails import Guardrails
from .memory import Memory
from .model import Model
from .observability import Tracer
from .tools import ToolRegistry
from .verification import Verifier, VerifierResult, default_verifiers, run_verifiers


@dataclass
class Result:
    answer: str | None
    verifications: list[VerifierResult] = field(default_factory=list)
    stopped_reason: str = "completed"

    @property
    def verified(self) -> bool:
        return self.answer is not None and all(v.passed for v in self.verifications)


class Harness:
    def __init__(
        self,
        model: Model,
        registry: ToolRegistry,
        guardrails: Guardrails,
        tracer: Tracer | None = None,
        verifiers: list[Verifier] | None = None,
    ) -> None:
        self.model = model
        self.registry = registry
        self.guardrails = guardrails
        self.tracer = tracer or Tracer()
        self.verifiers = verifiers if verifiers is not None else default_verifiers()

    def run(self, task: str) -> Result:
        memory = Memory(task=task)
        catalog = self.registry.catalog()
        self.tracer.emit("run_start", task=task, allowed=sorted(self.guardrails.allowed_tools))

        while True:
            budget = self.guardrails.check_budget()
            if not budget.allowed:
                self.tracer.emit("stop", reason=budget.reason)
                return Result(answer=None, stopped_reason=budget.reason)

            action = self.model.decide(memory.render(), catalog)

            if action.is_final:
                self.tracer.emit("final", answer=action.final)
                results = run_verifiers(self.verifiers, self.tracer, action.final or "")
                for r in results:
                    self.tracer.emit("verify", name=r.name, passed=r.passed, detail=r.detail)
                return Result(answer=action.final, verifications=results)

            self.guardrails.record_step()
            spec = self.registry.get(action.tool)  # raises on unknown tool
            args = action.args or {}
            self.tracer.emit("tool_call", tool=spec.name, args=args, mutating=spec.mutating)

            decision = self.guardrails.authorize(spec, args)
            if not decision.allowed:
                self.tracer.emit("tool_refused", tool=spec.name, reason=decision.reason)
                memory.add_observation(f"{spec.name} refused: {decision.reason}")
                continue

            output = spec(**args)
            self.tracer.emit(
                "tool_result",
                tool=spec.name,
                mutating=spec.mutating,
                approved=spec.mutating,  # reached here only if approved
                output=output,
            )
            memory.add_observation(f"{spec.name}({args}) -> {output}")
