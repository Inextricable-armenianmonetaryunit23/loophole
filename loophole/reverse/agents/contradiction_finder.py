from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.reverse.models import CaseType, ReverseFinding, ReverseSession
from loophole.reverse.prompts import CONTRADICTION_FINDER_SYSTEM, CONTRADICTION_FINDER_USER


def _format_prior_findings(findings: list[ReverseFinding]) -> str:
    if not findings:
        return "(none yet)"
    parts = []
    for f in findings:
        parts.append(
            f"Finding #{f.id} ({f.case_type.value}): {f.scenario[:150]}..."
        )
    return "\n".join(parts)


def _format_tensions(findings: list[ReverseFinding]) -> str:
    if not findings:
        return "(none yet)"
    parts = []
    for f in findings:
        parts.append(
            f"Tension #{f.id}: {f.scenario[:150]}... "
            f"[{', '.join(f.principles_involved)}]"
        )
    return "\n".join(parts)


class ContradictionFinder(BaseAgent):
    def __init__(self, *args: Any, cases_per_agent: int = 3, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.cases_per_agent = cases_per_agent

    def _build_system_prompt(self, **kwargs: Any) -> str:
        return CONTRADICTION_FINDER_SYSTEM.format(
            cases_per_agent=self.cases_per_agent
        )

    def _build_user_message(self, state: ReverseSession, **kwargs: Any) -> str:
        return CONTRADICTION_FINDER_USER.format(
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
        return _parse_findings(raw, state, CaseType.CONTRADICTION)


def _parse_findings(
    raw: str, state: ReverseSession, case_type: CaseType
) -> list[ReverseFinding]:
    findings = []
    for m in re.finditer(r"<finding>(.*?)</finding>", raw, re.DOTALL):
        block = m.group(1)
        scenario = _extract_tag(block, "scenario")
        explanation = _extract_tag(block, "explanation")
        involved_raw = _extract_tag(block, "principles_involved") or ""
        involved = [p.strip() for p in involved_raw.split(",") if p.strip()]

        if scenario and explanation:
            findings.append(
                ReverseFinding(
                    id=state.next_finding_id + len(findings),
                    round=state.current_round,
                    case_type=case_type,
                    scenario=scenario,
                    explanation=explanation,
                    principles_involved=involved,
                )
            )
    return findings


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else None
