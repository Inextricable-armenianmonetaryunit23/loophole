from __future__ import annotations

import json
from pathlib import Path

from loophole.chatbot.models import CaseStatus, ChatbotConfig, ChatbotSession, SystemPrompt


class ChatbotSessionManager:
    def __init__(self, base_dir: str = "sessions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        session_id: str,
        config: ChatbotConfig,
        initial_prompt: SystemPrompt,
    ) -> ChatbotSession:
        state = ChatbotSession(
            session_id=session_id,
            config=config,
            current_prompt=initial_prompt,
            prompt_history=[initial_prompt],
        )
        self.save(state)
        return state

    def save(self, state: ChatbotSession) -> None:
        session_dir = self.base_dir / state.session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        (session_dir / "state.json").write_text(
            state.model_dump_json(indent=2)
        )

        (session_dir / "system_prompt.md").write_text(
            f"# System Prompt v{state.current_prompt.version}\n\n"
            f"*{state.config.company_name}*\n\n"
            f"{state.current_prompt.text}\n"
        )

        (session_dir / "case_log.md").write_text(
            _render_case_log(state)
        )

    def load(self, session_id: str) -> ChatbotSession:
        state_path = self.base_dir / session_id / "state.json"
        return ChatbotSession.model_validate_json(state_path.read_text())

    def list_sessions(self) -> list[dict]:
        sessions = []
        for p in sorted(self.base_dir.iterdir()):
            state_path = p / "state.json"
            if state_path.exists():
                data = json.loads(state_path.read_text())
                if "config" not in data:
                    continue  # Skip legal sessions
                sessions.append({
                    "id": data["session_id"],
                    "company": data["config"]["company_name"],
                    "round": data["current_round"],
                    "cases": len(data["cases"]),
                    "prompt_version": data["current_prompt"]["version"],
                })
        return sessions


def _render_case_log(state: ChatbotSession) -> str:
    lines = [
        f"# Case Log — {state.config.company_name}",
        f"*Session: {state.session_id}*\n",
    ]

    status_labels = {
        CaseStatus.AUTO_RESOLVED: "Auto-resolved by Judge",
        CaseStatus.USER_RESOLVED: "Resolved by User",
        CaseStatus.ESCALATED: "ESCALATED — awaiting user",
        CaseStatus.PENDING: "Pending",
    }

    for case in state.cases:
        label = status_labels.get(case.status, case.status.value)
        type_label = "JAILBREAK" if case.attack_type.value == "jailbreak" else "FALSE REFUSAL"
        lines.append(f"## Case #{case.id} ({type_label}) — Round {case.round}")
        lines.append(f"**Status:** {label}\n")
        lines.append(f"**Attack prompt:** {case.attack_prompt}\n")
        lines.append(f"**Bot response:** {case.bot_response}\n")
        lines.append(f"**Problem:** {case.evaluation}\n")
        if case.resolution:
            lines.append(f"**Resolution:** {case.resolution}\n")
        lines.append("---\n")

    return "\n".join(lines)
