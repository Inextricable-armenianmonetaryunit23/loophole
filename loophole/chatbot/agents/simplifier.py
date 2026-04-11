from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.chatbot.models import ChatbotSession, SystemPrompt, TestCase
from loophole.chatbot.prompts import SIMPLIFIER_SYSTEM, SIMPLIFIER_USER


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


class Simplifier(BaseAgent):
    def _build_system_prompt(self, **kwargs: Any) -> str:
        return SIMPLIFIER_SYSTEM

    def _build_user_message(self, state: ChatbotSession, **kwargs: Any) -> str:
        cfg = state.config
        return SIMPLIFIER_USER.format(
            prompt_version=state.current_prompt.version,
            company_name=cfg.company_name,
            company_description=cfg.company_description,
            chatbot_purpose=cfg.chatbot_purpose,
            should_talk_about=cfg.should_talk_about,
            should_not_talk_about=cfg.should_not_talk_about,
            system_prompt=state.current_prompt.text,
            resolved_cases_text=_format_resolved_cases(state.resolved_cases),
        )

    def simplify(self, state: ChatbotSession) -> SystemPrompt | None:
        raw = self.run(state)
        text = _extract_tag(raw, "system_prompt")
        if not text:
            return None
        changelog = _extract_tag(raw, "changelog")
        return SystemPrompt(
            version=state.current_prompt.version + 1,
            text=text.strip(),
            changelog=f"[Simplification] {changelog or 'Compressed prompt'}",
        )


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1).strip() if m else None
