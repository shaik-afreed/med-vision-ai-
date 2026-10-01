from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    # At most one of these: the X-ray report or the lab/medical document
    # the user is asking about.
    report_id: int | None = None
    document_id: int | None = None
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def check_turn_order(self):
        if self.report_id is not None and self.document_id is not None:
            raise ValueError("send report_id or document_id, not both")
        for index, message in enumerate(self.messages):
            expected = "user" if index % 2 == 0 else "assistant"
            if message.role != expected:
                raise ValueError(
                    "messages must alternate user/assistant, starting with user"
                )
        if self.messages[-1].role != "user":
            raise ValueError("the last message must be from the user")
        return self


class ChatResponse(BaseModel):
    reply: str
    source: Literal["nvidia", "local_llm", "builtin"]
    model: str | None = None


class ChatStatusResponse(BaseModel):
    # True when any AI model (hosted or local) can answer free-form questions.
    llm_available: bool
    # Which engine answers first: "nvidia", "local_llm", or "none" (built-in answers only).
    provider: Literal["nvidia", "local_llm", "none"]
    model: str | None = None
