from __future__ import annotations

from typing import Any

from loophole.llm import LLMProvider
from loophole.models import SessionState


class BaseAgent:
    def __init__(self, llm: LLMProvider, temperature: float = 0.5):
        self.llm = llm
        self.temperature = temperature

    def _build_system_prompt(self, **kwargs: Any) -> str:
        raise NotImplementedError

    def _build_user_message(self, state: SessionState, **kwargs: Any) -> str:
        raise NotImplementedError

    def run(self, state: SessionState, **kwargs: Any) -> str:
        system = self._build_system_prompt(**kwargs)
        user_msg = self._build_user_message(state, **kwargs)
        return self.llm.call(system, user_msg, temperature=self.temperature)
