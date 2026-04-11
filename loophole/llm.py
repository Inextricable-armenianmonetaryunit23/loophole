from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Protocol that all LLM providers must satisfy."""

    model: str
    max_tokens: int

    def call(self, system: str, user_message: str, temperature: float = 0.5) -> str: ...

    def call_messages(
        self, system: str, messages: list[dict], temperature: float = 0.5
    ) -> str: ...


class AnthropicProvider:
    def __init__(self, model: str = "claude-sonnet-4-20250514", max_tokens: int = 4096):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def call(self, system: str, user_message: str, temperature: float = 0.5) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def call_messages(
        self, system: str, messages: list[dict], temperature: float = 0.5
    ) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        return response.content[0].text


class OpenAIProvider:
    def __init__(
        self,
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        base_url: str | None = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self._base_url = base_url
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai

            kwargs = {}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = openai.OpenAI(**kwargs)
        return self._client

    def call(self, system: str, user_message: str, temperature: float = 0.5) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content or ""

    def call_messages(
        self, system: str, messages: list[dict], temperature: float = 0.5
    ) -> str:
        full_messages = [{"role": "system", "content": system}] + messages
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            messages=full_messages,
        )
        return response.choices[0].message.content or ""


class OllamaProvider(OpenAIProvider):
    """Ollama uses an OpenAI-compatible API."""

    def __init__(
        self,
        model: str = "llama3.1",
        max_tokens: int = 4096,
        base_url: str = "http://localhost:11434/v1",
    ):
        super().__init__(model=model, max_tokens=max_tokens, base_url=base_url)


def _infer_provider(model: str) -> str:
    """Infer provider name from model string."""
    if model.startswith("claude-"):
        return "anthropic"
    if model.startswith(("gpt-", "o1-", "o3-", "o4-")):
        return "openai"
    return "ollama"


def create_provider(
    provider: str, model: str, max_tokens: int = 4096, **kwargs
) -> LLMProvider:
    """Factory: create a provider by name."""
    if provider == "anthropic":
        return AnthropicProvider(model=model, max_tokens=max_tokens)
    if provider == "openai":
        return OpenAIProvider(
            model=model, max_tokens=max_tokens, base_url=kwargs.get("base_url")
        )
    if provider == "ollama":
        return OllamaProvider(
            model=model,
            max_tokens=max_tokens,
            base_url=kwargs.get("base_url", "http://localhost:11434/v1"),
        )
    raise ValueError(f"Unknown provider: {provider}")


def LLMClient(
    model: str = "claude-sonnet-4-20250514", max_tokens: int = 4096
) -> LLMProvider:
    """Backward-compatible constructor. Infers provider from model name."""
    provider = _infer_provider(model)
    return create_provider(provider, model, max_tokens)
