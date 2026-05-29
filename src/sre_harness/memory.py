"""Context & memory: what the model gets to see on each turn.

This is a deliberately small working memory: the original task plus every
observation the agent has gathered so far. The point the reference makes is
*compaction* — `render` caps how much history is fed back to the model, so a
long investigation does not blow the context window. Swap this class for a
vector store, a summarizer, or a tiered memory system without touching the
loop; the loop only depends on `add_observation` and `render`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Memory:
    task: str
    max_observations: int = 8
    _observations: list[str] = field(default_factory=list)

    def add_observation(self, text: str) -> None:
        self._observations.append(text)

    def render(self) -> str:
        recent = self._observations[-self.max_observations :]
        dropped = len(self._observations) - len(recent)
        header = f"TASK: {self.task}"
        if not recent:
            return header + "\n(no observations yet)"
        prefix = f"[{dropped} earlier observation(s) compacted away]\n" if dropped else ""
        body = "\n".join(f"- {o}" for o in recent)
        return f"{header}\n{prefix}OBSERVATIONS:\n{body}"
