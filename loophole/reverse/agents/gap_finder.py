from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.reverse.agents.contradiction_finder import (
    _extract_tag,
    _format_prior_findings,
    _format_tensions,
    _parse_findings,
)
from loophole.reverse.models import CaseType, ReverseFinding, ReverseSession
from loophole.reverse.prompts import GAP_FINDER_SYSTEM, GAP_FINDER_USER


class GapFinder(BaseAgent):
    def __init__(self, *args: Any, cases_per_agent: int = 3, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.cases_per_agent = cases_per_agent

    def _build_system_prompt(self, **kwargs: Any) -> str:
        return GAP_FINDER_SYSTEM.format(cases_per_agent=self.cases_per_agent)

    def _build_user_message(self, state: ReverseSession, **kwargs: Any) -> str:
        return GAP_FINDER_USER.format(
            document_name=state.document_name,
            legal_text=state.legal_text,
            user_clarifications="\n".join(state.user_clarifications) or "(none)",
            principles_version=state.current_principles.version,
            current_principles=state.current_principles.text,
            prior_findings_text=_format_prior_findings(state.findings),
            tensions_text=_format_tensions(state.tension_findings),
            cases_per_agent=self.cases_per_agent,
        )

    def find(self, state: ReverseSession) -> list[ReverseFinding]:
        raw = self.run(state)
        return _parse_findings(raw, state, CaseType.GAP)
