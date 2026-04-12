from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CaseType(str, Enum):
    CONTRADICTION = "contradiction"  # Two principles conflict
    GAP = "gap"  # Legal text implies a value the principles miss


class CaseResolution(str, Enum):
    PENDING = "pending"
    REFINED = "refined"  # User refined the principles
    TENSION = "tension"  # User marked as genuine unresolvable tension


class ReverseFinding(BaseModel):
    id: int
    round: int
    case_type: CaseType
    scenario: str
    explanation: str
    principles_involved: list[str] = Field(default_factory=list)
    resolution: CaseResolution = CaseResolution.PENDING
    user_instruction: str | None = None  # If refined: what the user said
    tension_note: str | None = None  # If tension: why it's unresolvable
    created_at: datetime = Field(default_factory=datetime.now)


class PrinciplesList(BaseModel):
    version: int
    text: str
    changelog: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class ReverseSession(BaseModel):
    session_id: str
    document_name: str
    legal_text: str  # Fixed — never changes
    user_clarifications: list[str] = Field(default_factory=list)
    current_principles: PrinciplesList
    principles_history: list[PrinciplesList] = Field(default_factory=list)
    findings: list[ReverseFinding] = Field(default_factory=list)
    tensions: list[ReverseFinding] = Field(default_factory=list)
    current_round: int = 0
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def refined_findings(self) -> list[ReverseFinding]:
        return [f for f in self.findings if f.resolution == CaseResolution.REFINED]

    @property
    def tension_findings(self) -> list[ReverseFinding]:
        return [f for f in self.findings if f.resolution == CaseResolution.TENSION]

    @property
    def next_finding_id(self) -> int:
        return len(self.findings) + 1
