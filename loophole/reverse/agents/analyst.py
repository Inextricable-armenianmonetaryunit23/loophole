from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.reverse.models import CaseResolution, PrinciplesList, ReverseFinding, ReverseSession
from loophole.reverse.prompts import ANALYST_INITIAL, ANALYST_REVISE, ANALYST_SYSTEM


def _format_refined_findings(findings: list[ReverseFinding]) -> str:
    if not findings:
        return "(none yet)"
    parts = []
    for f in findings:
        parts.append(
            f"Finding #{f.id} ({f.case_type.value})\n"
            f"  Scenario: {f.scenario}\n"
            f"  User instruction: {f.user_instruction}"
        )
    return "\n\n".join(parts)


def _format_tensions(findings: list[ReverseFinding]) -> str:
    if not findings:
        return "(none yet)"
    parts = []
    for f in findings:
        parts.append(
            f"Tension #{f.id}: {f.scenario}\n"
            f"  Why unresolvable: {f.tension_note}"
        )
    return "\n\n".join(parts)


class Analyst(BaseAgent):
    def _build_system_prompt(self, **kwargs: Any) -> str:
        return ANALYST_SYSTEM

    def _build_user_message(self, state: ReverseSession, **kwargs: Any) -> str:
        finding: ReverseFinding | None = kwargs.get("finding")
        if finding is None:
            return ANALYST_INITIAL.format(
                document_name=state.document_name,
                legal_text=state.legal_text,
            )
        return ANALYST_REVISE.format(
            document_name=state.document_name,
            legal_text=state.legal_text,
            user_clarifications="\n".join(state.user_clarifications) or "(none)",
            principles_version=state.current_principles.version,
            current_principles=state.current_principles.text,
            case_type=finding.case_type.value,
            scenario=finding.scenario,
            explanation=finding.explanation,
            user_instruction=finding.user_instruction,
            prior_refinements_text=_format_refined_findings(state.refined_findings),
            tensions_text=_format_tensions(state.tension_findings),
        )

    def extract_initial(self, state: ReverseSession) -> PrinciplesList:
        raw = self.run(state)
        text = _extract_tag(raw, "principles") or raw
        return PrinciplesList(version=1, text=text.strip())

    def revise(self, state: ReverseSession, finding: ReverseFinding) -> PrinciplesList:
        raw = self.run(state, finding=finding)
        text = _extract_tag(raw, "principles") or raw
        changelog = _extract_tag(raw, "changelog")
        return PrinciplesList(
            version=state.current_principles.version + 1,
            text=text.strip(),
            changelog=changelog,
        )


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else None
