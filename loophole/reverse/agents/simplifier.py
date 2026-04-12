from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.reverse.agents.analyst import _format_refined_findings, _format_tensions
from loophole.reverse.models import PrinciplesList, ReverseSession
from loophole.reverse.prompts import SIMPLIFIER_SYSTEM, SIMPLIFIER_USER


class Simplifier(BaseAgent):
    def _build_system_prompt(self, **kwargs: Any) -> str:
        return SIMPLIFIER_SYSTEM

    def _build_user_message(self, state: ReverseSession, **kwargs: Any) -> str:
        return SIMPLIFIER_USER.format(
            principles_version=state.current_principles.version,
            document_name=state.document_name,
            legal_text=state.legal_text,
            current_principles=state.current_principles.text,
            refined_findings_text=_format_refined_findings(state.refined_findings),
            tensions_text=_format_tensions(state.tension_findings),
        )

    def simplify(self, state: ReverseSession) -> PrinciplesList | None:
        raw = self.run(state)
        text = _extract_tag(raw, "principles")
        if not text:
            return None
        changelog = _extract_tag(raw, "changelog")
        return PrinciplesList(
            version=state.current_principles.version + 1,
            text=text.strip(),
            changelog=f"[Simplification] {changelog or 'Compressed principles'}",
        )


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else None
