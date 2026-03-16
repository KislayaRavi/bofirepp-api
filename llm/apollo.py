"""
Apollo-backed LLM clients for OpenAI and Anthropic.

Both classes route requests through the ``apollo_client`` SDK, which handles
authentication and routing to the underlying provider.

Usage::

    from llm import ApolloOpenAIClient, ApolloAnthropicClient, LLMMessage

    # OpenAI via Apollo
    openai_llm = ApolloOpenAIClient()
    answer = openai_llm.complete("What is Bayesian optimization?")

    # Anthropic via Apollo
    anthropic_llm = ApolloAnthropicClient()
    reply = anthropic_llm.chat([
        LLMMessage(role="system", content="You are a helpful lab assistant."),
        LLMMessage(role="user",   content="Suggest an experiment."),
    ])
"""
from __future__ import annotations

from typing import Any

from llm.base import LLMClient, LLMMessage

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude_3_5_haiku"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TIMEOUT = 120


class ApolloOpenAIClient(LLMClient):
    """LLM client backed by OpenAI models, routed through the Apollo gateway.

    Args:
        model_name: OpenAI model identifier.
                    Defaults to ``"gpt-4o-mini"``.
        timeout:    HTTP timeout in seconds passed to the Apollo client.
                    Defaults to ``120``.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_OPENAI_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(model_name)
        from apollo_client import OpenAI

        self._client = OpenAI(timeout=timeout)

    # ── LLMClient interface ───────────────────────────────────────────────────

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Send a single prompt and return the model's text response.

        Args:
            prompt:      Plain text prompt.
            max_tokens:  Maximum output tokens (default 8192).
            temperature: Sampling temperature (0–2).

        Returns:
            The model's text response.
        """
        messages = [{"role": "user", "content": prompt}]
        return self._create(messages, **kwargs)

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> str:
        """Send a conversation history and return the model's reply.

        System, user, and assistant messages are all passed directly in the
        OpenAI messages list.

        Args:
            messages:    Ordered list of :class:`~llm.base.LLMMessage` objects.
            max_tokens:  Maximum output tokens (default 8192).
            temperature: Sampling temperature (0–2).

        Returns:
            The model's text response.
        """
        openai_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]
        return self._create(openai_messages, **kwargs)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _create(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        create_kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
        }
        if "temperature" in kwargs:
            create_kwargs["temperature"] = kwargs["temperature"]

        response = self._client.chat.completions.create(**create_kwargs)
        return response.choices[0].message.content or ""


class ApolloAnthropicClient(LLMClient):
    """LLM client backed by Anthropic models, routed through the Apollo gateway.

    Args:
        model_name: Anthropic model identifier.
                    Defaults to ``"claude_3_5_haiku"``.
        timeout:    HTTP timeout in seconds passed to the Apollo client.
                    Defaults to ``120``.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_ANTHROPIC_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(model_name)
        from apollo_client import Anthropic

        self._client = Anthropic(timeout=timeout)

    # ── LLMClient interface ───────────────────────────────────────────────────

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Send a single prompt and return the model's text response.

        Args:
            prompt:      Plain text prompt.
            max_tokens:  Maximum output tokens (default 8192).
            temperature: Sampling temperature (0–2).

        Returns:
            The model's text response.
        """
        messages = [{"role": "user", "content": prompt}]
        return self._create(messages, system=None, **kwargs)

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> str:
        """Send a conversation history and return the model's reply.

        System messages are extracted and passed as Anthropic's top-level
        ``system`` parameter; user/assistant turns go in ``messages``.

        Args:
            messages:    Ordered list of :class:`~llm.base.LLMMessage` objects.
            max_tokens:  Maximum output tokens (default 8192).
            temperature: Sampling temperature (0–2).

        Returns:
            The model's text response.
        """
        system_parts = [m.content for m in messages if m.role == "system"]
        system = "\n\n".join(system_parts) if system_parts else None

        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        return self._create(anthropic_messages, system=system, **kwargs)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _create(
        self,
        messages: list[dict[str, str]],
        system: str | None,
        **kwargs: Any,
    ) -> str:
        create_kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
        }
        if system:
            create_kwargs["system"] = system
        if "temperature" in kwargs:
            create_kwargs["temperature"] = kwargs["temperature"]

        response = self._client.messages.create(**create_kwargs)
        return response.content[0].text or ""
