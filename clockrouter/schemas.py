from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: Literal["system", "developer", "user", "assistant", "tool"]
    content: Any = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str = Field(default="clock/auto", min_length=1, max_length=200)
    messages: list[ChatMessage] = Field(min_length=1, max_length=10_000)
    stream: bool = False
    max_tokens: int | None = Field(default=None, ge=1)


def error_payload(message: str, error_type: str, code: str) -> dict[str, dict[str, str | None]]:
    return {"error": {"message": message, "type": error_type, "param": None, "code": code}}
