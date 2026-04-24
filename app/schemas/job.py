import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["pending", "running", "done", "failed"]


class JobCreate(BaseModel):
    input_handle: str
    chat_id: int
    message_id: int | None = None


class JobRead(BaseModel):
    id: uuid.UUID
    input_handle: str
    chat_id: int
    status: JobStatus
    created_at: datetime
    finished_at: datetime | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


class JobStatusUpdate(BaseModel):
    status: JobStatus
    error: str | None = None
    finished_at: datetime | None = Field(default_factory=datetime.utcnow)
