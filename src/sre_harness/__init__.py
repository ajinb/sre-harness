"""sre-harness: a minimal, runnable reference harness for SRE agents.

Five components, one loop:
  tool orchestration · verification loops · context/memory · guardrails · observability
"""

from .guardrails import Decision, Guardrails
from .harness import Harness, Result
from .memory import Memory
from .model import Action, AnthropicModel, FakeModel, Model, parse_action
from .observability import TraceEvent, Tracer
from .tools import ToolRegistry, ToolSpec, default_registry
from .verification import VerifierResult, default_verifiers, run_verifiers

__version__ = "0.1.0"

__all__ = [
    "Action",
    "AnthropicModel",
    "Decision",
    "FakeModel",
    "Guardrails",
    "Harness",
    "Memory",
    "Model",
    "Result",
    "ToolRegistry",
    "ToolSpec",
    "TraceEvent",
    "Tracer",
    "VerifierResult",
    "default_registry",
    "default_verifiers",
    "parse_action",
    "run_verifiers",
]
