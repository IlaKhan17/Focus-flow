from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class FocusSession(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True)
    task_title: str
    started_at: datetime
    ended_at: Optional[datetime] = None

