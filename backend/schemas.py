
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CustomerCreate(BaseModel):
    name: str
    email: str
    password: str


class CustomerLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CustomerResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    customer_id: int
    subject: str
    description: str
    priority: str = "normal"


class TicketResponse(BaseModel):
    id: int
    customer_id: int
    subject: str
    description: str
    status: str
    priority: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class AIRequest(BaseModel):
    issue: str
    customer_history: str = ""


class AIResponse(BaseModel):
    response: str
class TicketAnalysisResponse(BaseModel):
    category: str
    sentiment: str
    priority: str
    summary: str


class MemoryChatRequest(BaseModel):
    customer_id: int
    issue: str


class MemoryChatResponse(BaseModel):
    customer_id: int
    previous_memories: list[str]
    response: str

class TroubleshootingAttemptCreate(BaseModel):
    step: str
    outcome: str
    notes: str | None = None
class TroubleshootingFeedback(BaseModel):
    customer_id: int
    ticket_id: int
    successful: bool
    notes: str | None = None