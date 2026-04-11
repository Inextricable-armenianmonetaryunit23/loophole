from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.models import Case, LegalCode, SessionState
from loophole.prompts import SIMPLIFIER_SYSTEM, SIMPLIFIER_USER


def _format_resolved_cases(cases: list[Case]) -> str:
    if not cases:
        return "(none yet)"
    parts = []
    for c in cases:
        parts.append(
            f"Case #{c.id} ({c.case_type.value}) — {c.scenario}\n"
            f"  Resolution: {c.resolution}\n"
            f"  Resolved by: {c.resolved_by}"
        )
    return "\n\n".join(parts)


class Simplifier(BaseAgent):
    def _build_system_prompt(self, **kwargs: Any) -> str:
        return SIMPLIFIER_SYSTEM

    def _build_user_message(self, state: SessionState, **kwargs: Any) -> str:
        return SIMPLIFIER_USER.format(
            code_version=state.current_code.version,
            moral_principles=state.moral_principles,
            legal_code=state.current_code.text,
            resolved_cases_text=_format_resolved_cases(state.resolved_cases),
        )

    def simplify(self, state: SessionState) -> LegalCode | None:
        raw = self.run(state)
        text = _extract_tag(raw, "legal_code")
        if not text:
            return None
        changelog = _extract_tag(raw, "changelog")
        return LegalCode(
            version=state.current_code.version + 1,
            text=text.strip(),
            changelog=f"[Simplification] {changelog or 'Compressed code'}",
        )


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else None
