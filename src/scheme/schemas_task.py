from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class StatusTask(str, Enum):
    open = "open"
    work = "work"
    review = "review"
    closed = "closed"


class GradeTask(int, Enum):
    one = 1
    two = 2
    three = 3
    four = 4
    five = 5


class CommentSchema(BaseModel):
    id: int
    task_id: int
    user_id: int
    text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentCreateSchema(BaseModel):
    text: str


class ExecutorSchema(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)


class TaskSchema(BaseModel):
    id: int
    team_id: int
    executor_user_id: int | None = None
    executor: ExecutorSchema | None = None
    description: str
    status: StatusTask
    deadline: datetime
    grade: GradeTask | None = None
    close_date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskCreateSchema(BaseModel):
    executor_user_id: int | None = None
    description: str
    status: StatusTask
    deadline: datetime


class UpdateTaskSchema(BaseModel):
    description: str | None = None
    deadline: datetime | None = None


class UpdateTaskStatusSchema(BaseModel):
    status: StatusTask | None = None
    grade: GradeTask | None = None


class UpdateTaskExecutorSchema(BaseModel):
    executor_user_id: int | None = None


class OutAVGGradeTaskSchema(BaseModel):
    grade: float
