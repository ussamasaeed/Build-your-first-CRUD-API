from typing import Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    """Domain model — what a task looks like once it's stored."""
    id: int
    title: str
    done: bool = False


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None)
    done: Optional[bool] = Field(default=None)
