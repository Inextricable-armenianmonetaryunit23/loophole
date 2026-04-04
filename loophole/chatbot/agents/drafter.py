from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.chatbot.models import ChatbotSession, SystemPrompt, TestCase
from loophole.chatbot.prompts import DRAFTER_INITIAL, DRAFTER_REVISE, DRAFTER_SYSTEM


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


class Drafter(BaseAgent):
    def _build_system_prompt(self, **kwargs: Any) -> str:
        return DRAFTER_SYSTEM

    def _build_user_message(self, state: ChatbotSession, **kwargs: Any) -> str:
        case: TestCase | None = kwargs.get("case")
        cfg = state.config
        if case is None:
            return DRAFTER_INITIAL.format(
                company_name=cfg.company_name,
                company_description=cfg.company_description,
                chatbot_purpose=cfg.chatbot_purpose,
                should_talk_about=cfg.should_talk_about,
                should_not_talk_about=cfg.should_not_talk_about,
                tone=cfg.tone or "(no specific tone guidelines)",
            )
        return DRAFTER_REVISE.format(
            company_name=cfg.company_name,
            company_description=cfg.company_description,
            chatbot_purpose=cfg.chatbot_purpose,
            should_talk_about=cfg.should_talk_about,
            should_not_talk_about=cfg.should_not_talk_about,
            tone=cfg.tone or "(no specific tone guidelines)",
            user_clarifications="\n".join(state.user_clarifications) or "(none)",
            prompt_version=state.current_prompt.version,
            system_prompt=state.current_prompt.text,
            case_type=case.attack_type.value,
            attack_prompt=case.attack_prompt,
            bot_response=case.bot_response,
            evaluation=case.evaluation,
            case_resolution=case.resolution,
            resolved_cases_text=_format_resolved_cases(state.resolved_cases),
        )

    def draft_initial(self, state: ChatbotSession) -> SystemPrompt:
        raw = self.run(state)
        text = _extract_tag(raw, "system_prompt") or raw
        return SystemPrompt(version=1, text=text.strip())

    def revise(self, state: ChatbotSession, case: TestCase) -> SystemPrompt:
        raw = self.run(state, case=case)
        text = _extract_tag(raw, "system_prompt") or raw
        changelog = _extract_tag(raw, "changelog")
        return SystemPrompt(
            version=state.current_prompt.version + 1,
            text=text.strip(),
            changelog=changelog,
        )


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else None
