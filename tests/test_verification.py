"""Direct unit tests for the verifiers."""

from __future__ import annotations

from sre_harness.observability import Tracer
from sre_harness.verification import evidence_required, no_unapproved_mutation


def test_evidence_required_fails_with_no_reads():
    tracer = Tracer()
    assert not evidence_required(tracer, "an answer").passed


def test_evidence_required_passes_after_a_read():
    tracer = Tracer()
    tracer.emit("tool_result", tool="list_pods", mutating=False)
    assert evidence_required(tracer, "an answer").passed


def test_unapproved_mutation_is_flagged():
    tracer = Tracer()
    tracer.emit("tool_result", tool="restart_pod", mutating=True, approved=False)
    assert not no_unapproved_mutation(tracer, "an answer").passed


def test_approved_mutation_passes():
    tracer = Tracer()
    tracer.emit("tool_result", tool="restart_pod", mutating=True, approved=True)
    assert no_unapproved_mutation(tracer, "an answer").passed
