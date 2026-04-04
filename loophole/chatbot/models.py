from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AttackType(str, Enum):
    JAILBREAK = "jailbreak"  # Bot responds when it shouldn't
    REFUSAL = "refusal"  # Bot refuses when it shouldn't


class CaseStatus(str, Enum):
    PENDING = "pending"
    AUTO_RESOLVED = "auto_resolved"
    ESCALATED = "escalated"
    USER_RESOLVED = "user_resolved"


class ConversationTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class TestCase(BaseModel):
    id: int
    round: int
    attack_type: AttackType
    attack_prompt: str  # The final adversarial user message (or summary)
    bot_response: str  # The bot's final response
    conversation: list[ConversationTurn] = Field(default_factory=list)  # Full multi-turn log
    evaluation: str  # Why this is a failure
    succeeded: bool = True  # False for logged-but-held attempts
    status: CaseStatus = CaseStatus.PENDING
    resolution: str | None = None
    resolved_by: str | None = None  # "judge" or "user"
    created_at: datetime = Field(default_factory=datetime.now)


class SystemPrompt(BaseModel):
    version: int
    text: str
    changelog: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class ChatbotConfig(BaseModel):
    company_name: str
    company_description: str
    chatbot_purpose: str
    should_talk_about: str
    should_not_talk_about: str
    tone: str = ""


class ChatbotSession(BaseModel):
    session_id: str
    config: ChatbotConfig
    user_clarifications: list[str] = Field(default_factory=list)
    current_prompt: SystemPrompt
    prompt_history: list[SystemPrompt] = Field(default_factory=list)
    cases: list[TestCase] = Field(default_factory=list)  # Only confirmed failures
    attempts: list[TestCase] = Field(default_factory=list)  # ALL attempts (pass and fail)
    current_round: int = 0
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def resolved_cases(self) -> list[TestCase]:
        return [
            c
            for c in self.cases
            if c.status in (CaseStatus.AUTO_RESOLVED, CaseStatus.USER_RESOLVED)
        ]

    @property
    def next_case_id(self) -> int:
        return len(self.cases) + 1
