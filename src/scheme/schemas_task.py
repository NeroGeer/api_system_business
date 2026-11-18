from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from src.scheme.schemas_task_stage import StageSchemaRead


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
    title: str

    stage: StageSchemaRead

    deadline: datetime | None = None

    grade: GradeTask | None = None
    close_date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskCreateSchema(BaseModel):
    executor_user_id: int | None = None

    description: str
    title: str

    deadline: datetime | None = None


class UpdateTaskSchema(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None


class UpdateTaskStageSchema(BaseModel):
    stage_id: int

    grade: GradeTask | None = None


class UpdateTaskExecutorSchema(BaseModel):
    executor_user_id: int | None = None


class OutAVGGradeTaskSchema(BaseModel):
    grade: float
