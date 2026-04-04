from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.chatbot.models import ChatbotSession, TestCase
from loophole.chatbot.prompts import JUDGE_RESOLVE, JUDGE_SYSTEM, JUDGE_VALIDATE


def _format_resolved_cases(cases: list[TestCase]) -> str:
    if not cases:
        return "(none yet)"
    parts = []
    for c in cases:
        parts.append(
            f"Case #{c.id} ({c.attack_type.value})\n"
            f"  User message: {c.attack_prompt}\n"
            f"  Bot response: {c.bot_response[:200]}...\n"
            f"  Problem: {c.evaluation}\n"
            f"  Resolution: {c.resolution}"
        )
    return "\n\n".join(parts)


@dataclass
class JudgeResult:
    resolvable: bool
    reasoning: str
    proposed_revision: str | None = None
    resolution_summary: str | None = None
    conflict_explanation: str | None = None


@dataclass
class ValidationResult:
    passes: bool
    details: str


class Judge(BaseAgent):
    def _build_system_prompt(self, **kwargs: Any) -> str:
        return JUDGE_SYSTEM

    def _build_user_message(self, state: ChatbotSession, **kwargs: Any) -> str:
        case: TestCase = kwargs["case"]
        cfg = state.config
        return JUDGE_RESOLVE.format(
            company_name=cfg.company_name,
            company_description=cfg.company_description,
            chatbot_purpose=cfg.chatbot_purpose,
            should_talk_about=cfg.should_talk_about,
            should_not_talk_about=cfg.should_not_talk_about,
            user_clarifications="\n".join(state.user_clarifications) or "(none)",
            prompt_version=state.current_prompt.version,
            system_prompt=state.current_prompt.text,
            case_type=case.attack_type.value,
            attack_prompt=case.attack_prompt,
            bot_response=case.bot_response,
            evaluation=case.evaluation,
            resolved_cases_text=_format_resolved_cases(state.resolved_cases),
        )

    def evaluate(self, state: ChatbotSession, case: TestCase) -> JudgeResult:
        raw = self.run(state, case=case)

        verdict_match = re.search(r"<verdict>\s*(.*?)\s*</verdict>", raw, re.DOTALL)
        verdict = verdict_match.group(1).strip().lower() if verdict_match else "unresolvable"

        reasoning = _extract_tag(raw, "reasoning") or ""

        if verdict == "resolvable":
            return JudgeResult(
                resolvable=True,
                reasoning=reasoning,
                proposed_revision=_extract_tag(raw, "proposed_revision"),
                resolution_summary=_extract_tag(raw, "resolution_summary"),
            )
        return JudgeResult(
            resolvable=False,
            reasoning=reasoning,
            conflict_explanation=_extract_tag(raw, "conflict_explanation"),
        )

    def validate(self, state: ChatbotSession, proposed_prompt: str) -> ValidationResult:
        resolved = state.resolved_cases
        if not resolved:
            return ValidationResult(passes=True, details="No prior cases to validate against.")

        user_msg = JUDGE_VALIDATE.format(
            proposed_prompt=proposed_prompt,
            resolved_cases_text=_format_resolved_cases(resolved),
        )
        raw = self.llm.call(JUDGE_SYSTEM, user_msg, temperature=self.temperature)

        passes_match = re.search(r"<passes>\s*(.*?)\s*</passes>", raw, re.DOTALL)
        passes = passes_match.group(1).strip().lower() == "true" if passes_match else False

        details = _extract_tag(raw, "details") or raw
        return ValidationResult(passes=passes, details=details)


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else None
