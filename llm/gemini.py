"""
Gemini implementation of :class:`llm.base.LLMClient`.

Connects to the Google Gemini API via the ``google-genai`` Python SDK.
When running on Replit the ``AI_INTEGRATIONS_GEMINI_BASE_URL`` and
``AI_INTEGRATIONS_GEMINI_API_KEY`` environment variables are set automatically
by the Replit AI Integrations system — no manual key management required.

Supported models (via Replit AI Integrations proxy)::

    gemini-2.5-pro          — best reasoning & coding
    gemini-2.5-flash        — fast, general purpose  (default)
    gemini-3-flash-preview  — hybrid reasoning, high volume
    gemini-3-pro-preview    — agentic / complex tasks
    gemini-3.1-pro-preview  — latest, most powerful

Usage::

    from llm import GeminiClient, LLMMessage

    # Single-turn completion
    llm = GeminiClient()
    answer = llm.complete("Explain Bayesian optimization in one sentence.")

    # Multi-turn chat
    reply = llm.chat([
        LLMMessage(role="system", content="You are a helpful lab assistant."),
        LLMMessage(role="user",   content="What temperature should I use?"),
    ])
"""
from __future__ import annotations

import os
from typing import Any

from llm.base import LLMClient, LLMMessage

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_TOKENS = 8192


class GeminiClient(LLMClient):
    """LLM client backed by the Google Gemini API.

    Args:
        model_name: Gemini model identifier. Defaults to ``"gemini-2.5-flash"``.
        api_key:    Gemini API key. Reads ``AI_INTEGRATIONS_GEMINI_API_KEY``
                    from the environment when not provided.
        base_url:   Override the API base URL. Reads
                    ``AI_INTEGRATIONS_GEMINI_BASE_URL`` from the environment
                    when not provided (used by the Replit proxy).
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(model_name)

        resolved_api_key = api_key or os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY", "")
        resolved_base_url = base_url or os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")

        if not resolved_api_key:
            raise EnvironmentError(
                "Gemini API key not found. Set the AI_INTEGRATIONS_GEMINI_API_KEY "
                "environment variable or pass api_key= directly."
            )

        from google import genai

        # The Replit AI Integrations proxy expects no API version prefix in
        # the path (e.g. "/models/..." not "/v1beta/models/...").
        # Setting api_version="" replicates what the JS SDK does with
        # httpOptions: { apiVersion: "", baseUrl: ... }.
        http_options: dict[str, Any] = {"api_version": ""}
        if resolved_base_url:
            http_options["base_url"] = resolved_base_url

        self._client = genai.Client(
            api_key=resolved_api_key,
            http_options=http_options,
        )

    # ── LLMClient interface ───────────────────────────────────────────────────

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Send a single prompt and return the model's text response.

        Args:
            prompt:     Plain text prompt.
            max_tokens: Maximum output tokens (default 8192).
            temperature: Sampling temperature (0–2).

        Returns:
            The model's text response.
        """
        from google.genai import types

        config = types.GenerateContentConfig(
            max_output_tokens=kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
            **_optional(kwargs, "temperature"),
        )

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> str:
        """Send a conversation history and return the model's reply.

        System messages are extracted and passed as Gemini's
        ``system_instruction``. User / assistant turns are mapped to Gemini's
        ``"user"`` / ``"model"`` roles.

        Args:
            messages:    Ordered list of :class:`~llm.base.LLMMessage` objects.
            max_tokens:  Maximum output tokens (default 8192).
            temperature: Sampling temperature (0–2).

        Returns:
            The model's text response.
        """
        from google.genai import types

        system_parts = [m.content for m in messages if m.role == "system"]
        conversation = [m for m in messages if m.role != "system"]

        contents = [
            types.Content(
                role="model" if m.role == "assistant" else "user",
                parts=[types.Part(text=m.content)],
            )
            for m in conversation
        ]

        config_kwargs: dict[str, Any] = {
            "max_output_tokens": kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
            **_optional(kwargs, "temperature"),
        }
        if system_parts:
            config_kwargs["system_instruction"] = "\n\n".join(system_parts)

        config = types.GenerateContentConfig(**config_kwargs)

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config,
        )
        return response.text or ""


# ── internal helpers ──────────────────────────────────────────────────────────

def _optional(kwargs: dict[str, Any], *keys: str) -> dict[str, Any]:
    """Return a dict with only the kwargs that are present."""
    return {k: kwargs[k] for k in keys if k in kwargs}
