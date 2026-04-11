from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.chatbot.models import AttackType, ChatbotSession, ConversationTurn, TestCase
from loophole.chatbot.prompts import (
    EVALUATOR_REFUSAL,
    EVALUATOR_SYSTEM,
    REFUSAL_SYSTEM,
    REFUSAL_USER,
)
from loophole.llm import LLMProvider


def _format_prior_cases(cases: list[TestCase]) -> str:
    if not cases:
        return "(none yet)"
    parts = []
    for c in cases:
        parts.append(
            f"Case #{c.id} ({c.attack_type.value}): {c.attack_prompt[:150]}..."
        )
    return "\n".join(parts)


def _format_prior_attempts(attempts: list[TestCase]) -> str:
    if not attempts:
        return "(none yet)"
    parts = []
    for a in attempts:
        held = "WRONGLY REFUSED" if a.succeeded else "ANSWERED OK"
        parts.append(f"[{held}] {a.attack_prompt[:120]}...")
    return "\n".join(parts)


class RefusalFinder(BaseAgent):
    def __init__(
        self,
        llm: LLMClient,
        temperature: float = 0.9,
        cases_per_agent: int = 3,
        bot_llm: LLMProvider | None = None,
    ):
        super().__init__(llm, temperature=temperature)
        self.cases_per_agent = cases_per_agent
        self.bot_llm = bot_llm or llm

    def _build_system_prompt(self, **kwargs: Any) -> str:
        return REFUSAL_SYSTEM.format(cases_per_agent=self.cases_per_agent)

    def _build_user_message(self, state: ChatbotSession, **kwargs: Any) -> str:
        cfg = state.config
        return REFUSAL_USER.format(
            company_name=cfg.company_name,
            company_description=cfg.company_description,
            chatbot_purpose=cfg.chatbot_purpose,
            should_talk_about=cfg.should_talk_about,
            should_not_talk_about=cfg.should_not_talk_about,
            user_clarifications="\n".join(state.user_clarifications) or "(none)",
            prompt_version=state.current_prompt.version,
            system_prompt=state.current_prompt.text,
            prior_cases_text=_format_prior_cases(state.cases),
            prior_attempts_text=_format_prior_attempts(
                [a for a in state.attempts if a.attack_type == AttackType.REFUSAL]
            ),
            cases_per_agent=self.cases_per_agent,
        )

    def find(self, state: ChatbotSession) -> tuple[list[TestCase], list[TestCase]]:
        """Returns (confirmed_failures, all_attempts)."""
        raw = self.run(state)
        attacks = _parse_attacks(raw)

        confirmed: list[TestCase] = []
        all_attempts: list[TestCase] = []

        for attack_prompt, strategy in attacks:
            bot_response = self.bot_llm.call(
                system=state.current_prompt.text,
                user_message=attack_prompt,
                temperature=0.3,
            )

            conversation = [
                ConversationTurn(role="user", content=attack_prompt),
                ConversationTurn(role="assistant", content=bot_response),
            ]

            eval_result = self._evaluate(state, attack_prompt, bot_response)
            succeeded = eval_result is not None

            attempt = TestCase(
                id=state.next_case_id + len(confirmed),
                round=state.current_round,
                attack_type=AttackType.REFUSAL,
                attack_prompt=attack_prompt,
                bot_response=bot_response,
                conversation=conversation,
                evaluation=eval_result or f"Bot answered correctly. Strategy: {strategy}",
                succeeded=succeeded,
            )
            all_attempts.append(attempt)

            if succeeded:
                confirmed.append(attempt)

        return confirmed, all_attempts

    def _evaluate(self, state: ChatbotSession, attack_prompt: str, bot_response: str) -> str | None:
        cfg = state.config
        eval_msg = EVALUATOR_REFUSAL.format(
            system_prompt=state.current_prompt.text,
            should_talk_about=cfg.should_talk_about,
            attack_prompt=attack_prompt,
            bot_response=bot_response,
        )
        raw = self.llm.call(EVALUATOR_SYSTEM, eval_msg, temperature=0.1)

        failed_match = re.search(r"<failed>\s*(.*?)\s*</failed>", raw, re.DOTALL)
        failed = failed_match.group(1).strip().lower() == "true" if failed_match else False

        if not failed:
            return None

        reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", raw, re.DOTALL)
        return reasoning_match.group(1).strip() if reasoning_match else "Bot wrongly refused a legitimate request."


def _parse_attacks(raw: str) -> list[tuple[str, str]]:
    attacks = []
    for m in re.finditer(
        r"<attack>\s*<prompt>(.*?)</prompt>\s*<strategy>(.*?)</strategy>\s*</attack>",
        raw,
        re.DOTALL,
    ):
        attacks.append((m.group(1).strip(), m.group(2).strip()))
    return attacks
