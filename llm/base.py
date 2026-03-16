"""
Abstract base class for LLM clients.

Any LLM provider (Gemini, OpenAI, Anthropic, …) must implement this interface.
The two core operations are:

- ``complete`` — single-turn: send one prompt, get one text response.
- ``chat``     — multi-turn: send a conversation history, get one text response.

Usage example::

    from llm import GeminiClient

    llm = GeminiClient(model_name="gemini-2.5-flash")
    answer = llm.complete("What is Bayesian optimization?")
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class LLMMessage:
    """A single message in a conversation.

    Attributes:
        role:    Who sent this message — ``"user"``, ``"assistant"``, or ``"system"``.
        content: The text body of the message.
    """
    role: Literal["user", "assistant", "system"]
    content: str


class LLMClient(ABC):
    """Abstract base class that every LLM provider must implement.

    Subclasses must:

    1. Call ``super().__init__(model_name)`` (or set ``self.model_name`` directly).
    2. Implement :meth:`complete` for single-turn text generation.
    3. Implement :meth:`chat` for multi-turn conversation.

    Attributes:
        model_name: The identifier of the underlying model
                    (e.g. ``"gemini-2.5-flash"``).
    """

    def __init__(self, model_name: str) -> None:
        self.model_name: str = model_name

    # ── abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text response for a single prompt.

        Args:
            prompt:  The input text to send to the model.
            **kwargs: Provider-specific options (e.g. ``max_tokens``,
                      ``temperature``).

        Returns:
            The model's text response as a plain string.
        """

    @abstractmethod
    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> str:
        """Generate a response given a full conversation history.

        Args:
            messages: Ordered list of :class:`LLMMessage` objects representing
                      the conversation so far. May include ``"system"``,
                      ``"user"``, and ``"assistant"`` turns.
            **kwargs: Provider-specific options (e.g. ``max_tokens``,
                      ``temperature``).

        Returns:
            The model's text response as a plain string.
        """

    # ── convenience helpers ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model_name={self.model_name!r})"
