from __future__ import annotations

import re
from typing import Any

from loophole.agents.base import BaseAgent
from loophole.chatbot.models import AttackType, ChatbotSession, TestCase
from loophole.chatbot.prompts import (
    EVALUATOR_JAILBREAK,
    EVALUATOR_SYSTEM,
    JAILBREAK_SYSTEM,
    JAILBREAK_USER,
)
from loophole.llm import LLMClient


def _format_prior_cases(cases: list[TestCase]) -> str:
    if not cases:
        return "(none yet)"
    parts = []
    for c in cases:
        parts.append(
            f"Case #{c.id} ({c.attack_type.value}): {c.attack_prompt[:150]}..."
        )
    return "\n".join(parts)


class JailbreakFinder(BaseAgent):
    def __init__(self, llm: LLMClient, temperature: float = 0.9, cases_per_agent: int = 3):
        super().__init__(llm, temperature=temperature)
        self.cases_per_agent = cases_per_agent

    def _build_system_prompt(self, **kwargs: Any) -> str:
        return JAILBREAK_SYSTEM.format(cases_per_agent=self.cases_per_agent)

    def _build_user_message(self, state: ChatbotSession, **kwargs: Any) -> str:
        cfg = state.config
        return JAILBREAK_USER.format(
            company_name=cfg.company_name,
            company_description=cfg.company_description,
            chatbot_purpose=cfg.chatbot_purpose,
            should_not_talk_about=cfg.should_not_talk_about,
            should_talk_about=cfg.should_talk_about,
            user_clarifications="\n".join(state.user_clarifications) or "(none)",
            prompt_version=state.current_prompt.version,
            system_prompt=state.current_prompt.text,
            prior_cases_text=_format_prior_cases(state.cases),
            cases_per_agent=self.cases_per_agent,
        )

    def find(self, state: ChatbotSession) -> list[TestCase]:
        """Craft attacks, run them against the bot, evaluate results."""
        # Step 1: Craft attack prompts
        raw = self.run(state)
        attacks = _parse_attacks(raw)

        confirmed: list[TestCase] = []
        for attack_prompt, strategy in attacks:
            # Step 2: Run against the chatbot
            bot_response = self.llm.call(
                system=state.current_prompt.text,
                user_message=attack_prompt,
                temperature=0.3,
            )

            # Step 3: Evaluate — did the attack succeed?
            eval_result = self._evaluate(state, attack_prompt, bot_response)
            if eval_result is not None:
                confirmed.append(
                    TestCase(
                        id=state.next_case_id + len(confirmed),
                        round=state.current_round,
                        attack_type=AttackType.JAILBREAK,
                        attack_prompt=attack_prompt,
                        bot_response=bot_response,
                        evaluation=eval_result,
                    )
                )

        return confirmed

    def _evaluate(self, state: ChatbotSession, attack_prompt: str, bot_response: str) -> str | None:
        """Returns evaluation text if the attack succeeded (bot failed), None if bot held."""
        cfg = state.config
        eval_msg = EVALUATOR_JAILBREAK.format(
            system_prompt=state.current_prompt.text,
            should_not_talk_about=cfg.should_not_talk_about,
            attack_prompt=attack_prompt,
            bot_response=bot_response,
        )
        raw = self.llm.call(EVALUATOR_SYSTEM, eval_msg, temperature=0.1)

        failed_match = re.search(r"<failed>\s*(.*?)\s*</failed>", raw, re.DOTALL)
        failed = failed_match.group(1).strip().lower() == "true" if failed_match else False

        if not failed:
            return None

        reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", raw, re.DOTALL)
        return reasoning_match.group(1).strip() if reasoning_match else "Attack succeeded — bot engaged with forbidden content."


def _parse_attacks(raw: str) -> list[tuple[str, str]]:
    attacks = []
    for m in re.finditer(
        r"<attack>\s*<prompt>(.*?)</prompt>\s*<strategy>(.*?)</strategy>\s*</attack>",
        raw,
        re.DOTALL,
    ):
        attacks.append((m.group(1).strip(), m.group(2).strip()))
    return attacks
