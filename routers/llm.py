from __future__ import annotations

from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/llm", tags=["LLM"])


class LLMProvider(str, Enum):
    # openai = "openai"
    # anthropic = "anthropic"
    gemini = "gemini"


class LLMCompleteRequest(BaseModel):
    provider: LLMProvider = Field(
        ...,
        description="Which LLM provider to use: ``openai`` or ``anthropic``.",
    )
    model_name: Optional[str] = Field(
        default=None,
        description=(
            "Model identifier. Defaults to ``gpt-4o-mini`` for OpenAI, "
            "``claude_3_5_haiku`` for Anthropic, and ``gemini-2.5-flash`` "
            "for Gemini when omitted."
        ),
    )
    message: str = Field(..., description="The user message to send to the model.")
    max_tokens: int = Field(default=8192, description="Maximum tokens to generate.")
    temperature: Optional[float] = Field(
        default=None, description="Sampling temperature (0–2)."
    )


class LLMCompleteResponse(BaseModel):
    provider: str
    model_name: str
    response: str


@router.post(
    "/complete",
    response_model=LLMCompleteResponse,
    summary="Single-turn LLM completion",
    description=(
        "Send a single message to an Apollo-backed LLM (OpenAI or Anthropic) "
        "and receive the model's text response."
    ),
)
def llm_complete(request: LLMCompleteRequest) -> LLMCompleteResponse:
    kwargs: dict = {"max_tokens": request.max_tokens}
    if request.temperature is not None:
        kwargs["temperature"] = request.temperature

    try:
        # if request.provider == LLMProvider.openai:
        #     from llm.apollo import ApolloOpenAIClient

        #     client = ApolloOpenAIClient(
        #         model_name=request.model_name or "gpt-4o-mini"
        #     )
        # elif request.provider == LLMProvider.anthropic:
        #     from llm.apollo import ApolloAnthropicClient

        #     client = ApolloAnthropicClient(
        #         model_name=request.model_name or "claude_3_5_haiku"
        #     )
        # else:
        if request.provider == LLMProvider.gemini:
            from llm.gemini import GeminiClient

            client = GeminiClient(
                model_name=request.model_name or "gemini-2.5-flash"
            )

        text = client.complete(request.message, **kwargs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return LLMCompleteResponse(
        provider=request.provider.value,
        model_name=client.model_name,
        response=text,
    )
