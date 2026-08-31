from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    language: str = "bn"
    conversation_id: int | None = None      # None starts a new conversation


class Source(BaseModel):
    food: str
    portion: str
    ref: str


class ChatResponse(BaseModel):
    answer: str
    language: str
    sources: list[Source]
    message_id: int
    conversation_id: int | None = None      # None for anonymous users