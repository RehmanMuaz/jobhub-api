from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Annotated, Literal
from uuid import UUID, uuid4
from datetime import datetime, timezone

# Canonical ID type
ID = Annotated[UUID, "primary identifier"]

# Supported content sources (can extend later)
Source = Literal["linkedin", "indeed", "other"]

class TimestampedModel(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _default_created_at(cls, v):
        return v or datetime.now(timezone.utc)

    @field_validator("updated_at", mode="before")
    @classmethod
    def _default_updated_at(cls, v):
        return v or datetime.now(timezone.utc)

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "from_attributes": True,
        "extra": "ignore",
    }