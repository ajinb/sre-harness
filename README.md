# sre-harness

> A minimal, **runnable** reference harness for SRE agents. The five things the surrounding infrastructure has to do — tool orchestration, verification, memory, guardrails, observability — in one ~40-line loop you can read in a sitting.

[![CI](https://github.com/ajinb/sre-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/ajinb/sre-harness/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Agent = Model + Harness.** In 2026 the model is rarely the constraint; the harness around it is. This repo is the smallest honest demonstration of what that harness actually contains — not a framework to adopt, but a reference to read, copy, and outgrow.

It runs **offline with no API key**: a deterministic `FakeModel` drives a realistic SRE triage so you can see every component fire. Swap in `AnthropicModel` to use real Claude.

## The five components

| Component | Where | What it does |
|---|---|---|
| **Tool orchestration** | [`tools.py`](src/sre_harness/tools.py) | A registry the agent selects from. Each tool declares `mutating` — the one flag the guardrails key off of. |
| **Guardrails** | [`guardrails.py`](src/sre_harness/guardrails.py) | Step budget · tool allowlist · approval gate for mutating actions. Read-only runs free; writes need a human/policy yes. |
| **Context & memory** | [`memory.py`](src/sre_harness/memory.py) | Working memory with compaction — caps what's fed back to the model so a long investigation doesn't blow the window. |
| **Verification** | [`verification.py`](src/sre_harness/verification.py) | Checks the answer against the trace before returning: evidence was gathered, no unapproved mutations ran. |
| **Observability** | [`observability.py`](src/sre_harness/observability.py) | Every decision emits a structured JSON-line event. The trace *is* the audit log. |

The loop that ties them together is [`harness.py`](src/sre_harness/harness.py).

## Run it

```bash
git clone https://github.com/ajinb/sre-harness.git
cd sre-harness
pip install -e ".[dev]"
python examples/triage_demo.py
```

You'll see the agent triage a `CrashLoopBackOff` twice. First read-only: it
gathers metrics and logs, concludes it's an OOMKill, and notes a restart won't
fix it. Then with the `restart_pod` write tool granted but the approver saying
no — the harness **refuses the mutation** and records the refusal on the trace.

## Use real Claude

```python
from sre_harness import AnthropicModel, Guardrails, Harness, default_registry

harness = Harness(
    model=AnthropicModel(model="claude-opus-4-7"),
    registry=default_registry(),
    guardrails=Guardrails(allowed_tools={"list_pods", "get_metrics", "get_logs"}),
)
print(harness.run("checkout-7f9c is flapping — what's wrong?").answer)
```

`pip install -e ".[anthropic]"` and set `ANTHROPIC_API_KEY`. The loop is
unchanged — that's the whole point.

## Design stance

- **Read-only by default.** Mutating tools exist, but nothing mutates without
  an explicit approval for the *specific* call. The AI layer is additive, never
  load-bearing.
- **The trace is the contract.** In a regulated or safety-critical environment,
  "what did the agent do" must be answerable from an artifact, not a vibe.
- **Outgrow it.** Real memory is a vector store; real approval is a Slack
  round-trip; real tools wrap your orchestrator. Every component is behind a
  small seam so you can replace it without touching the loop. Graduate when the
  system demands it, not when a checklist says so.

## Companion reading

Built alongside the writeup *"Harness engineering: the third phase of AI maturity"* on [cloudandsre.com](https://cloudandsre.com). Related work: the MCP gateway pattern and [`cloudandsre-skills`](https://github.com/ajinb/cloudandsre-skills).

---

Apache-2.0. Built by [Ajin Baby](https://cloudandsre.com).
