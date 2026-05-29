"""Verification loops: don't trust the agent's final answer — check it.

Before the harness returns a conclusion, it runs a set of verifiers against
the trace. A verifier is a small predicate that knows one thing about what a
*valid* answer looks like. Here:

- evidence_required: the agent must have actually called a read tool before
  concluding — a conclusion with no gathered evidence is a hallucination.
- no_unapproved_mutation: the trace must not contain any executed mutating
  tool that lacked an approval (defense in depth behind the guardrail).

Failed verifiers are returned to the loop, which can feed them back to the
model for another attempt, or surface them to the operator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .observability import Tracer


@dataclass(frozen=True)
class VerifierResult:
    name: str
    passed: bool
    detail: str


Verifier = Callable[[Tracer, str], VerifierResult]


def evidence_required(tracer: Tracer, answer: str) -> VerifierResult:
    reads = [e for e in tracer.of_kind("tool_result") if not e.data.get("mutating")]
    ok = len(reads) > 0
    return VerifierResult(
        "evidence_required",
        ok,
        "at least one read tool was used" if ok else "answer reached with no evidence gathered",
    )


def no_unapproved_mutation(tracer: Tracer, answer: str) -> VerifierResult:
    bad = [
        e
        for e in tracer.of_kind("tool_result")
        if e.data.get("mutating") and not e.data.get("approved")
    ]
    return VerifierResult(
        "no_unapproved_mutation",
        not bad,
        "no unapproved mutations executed" if not bad else f"{len(bad)} unapproved mutation(s)",
    )


def default_verifiers() -> list[Verifier]:
    return [evidence_required, no_unapproved_mutation]


def run_verifiers(
    verifiers: list[Verifier], tracer: Tracer, answer: str
) -> list[VerifierResult]:
    return [v(tracer, answer) for v in verifiers]
