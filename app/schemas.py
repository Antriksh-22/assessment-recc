from typing import List, Literal

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict, field_validator
except ImportError:  # Pydantic v1 compatibility
    ConfigDict = None
    from pydantic import validator

    def field_validator(*fields, **kwargs):
        return validator(*fields)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)

    if ConfigDict:
        model_config = ConfigDict(extra="forbid")

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_length=1)

    if ConfigDict:
        model_config = ConfigDict(extra="forbid")


class Recommendation(BaseModel):
    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    test_type: str = Field(..., min_length=1)

    if ConfigDict:
        model_config = ConfigDict(extra="forbid")


class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation] = Field(default_factory=list, max_length=10)
    end_of_conversation: bool = False

    if ConfigDict:
        model_config = ConfigDict(extra="forbid")

