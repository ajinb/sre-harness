"""Observability: structured tracing of every step the agent takes.

A harness you cannot inspect is a harness you cannot trust. Every tool call,
guardrail decision, verification result, and model turn emits a structured
event with a monotonic sequence number and a wall-clock timestamp. The trace
is the audit log: in a regulated environment it is the artifact you hand an
auditor, and in an incident it is how you reconstruct what the agent did.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceEvent:
    seq: int
    ts: float
    kind: str
    data: dict[str, Any]

    def as_line(self) -> str:
        payload = {"seq": self.seq, "ts": round(self.ts, 3), "kind": self.kind, **self.data}
        return json.dumps(payload, default=str)


@dataclass
class Tracer:
    """Collects ordered events and emits them as JSON lines.

    `sink` defaults to None (events are only retained in memory). Pass a
    callable (e.g. ``print`` or a logger) to stream events as they happen.
    """

    sink: Any = None
    events: list[TraceEvent] = field(default_factory=list)
    _seq: int = 0

    def emit(self, kind: str, **data: Any) -> TraceEvent:
        event = TraceEvent(seq=self._seq, ts=time.time(), kind=kind, data=data)
        self._seq += 1
        self.events.append(event)
        if self.sink is not None:
            self.sink(event.as_line())
        return event

    def of_kind(self, kind: str) -> list[TraceEvent]:
        return [e for e in self.events if e.kind == kind]
