from datetime import UTC, datetime
from typing import List

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.model_base import Base
from src.scheme.schemas_task import StatusTask


class Task(Base):
    """
    Database model representing a task within a team.

    A task is an assignable utils_test of work that can be executed by a user,
    tracked by status, and optionally evaluated (grade).

    Attributes:
        id (int):
            Primary key identifier of the task.

        team_id (int):
            Team to which the task belongs.

        executor_user_id (int | None):
            User assigned to execute the task.

        description (str):
            Task description.

        status (StatusTask):
            Current status of the task (e.g. TODO, IN_PROGRESS, DONE).

        grade (int | None):
            Evaluation score for completed task.

        deadline (datetime):
            Deadline for task completion.

        close_date (datetime | None):
            Timestamp when task was closed.

        comment (List[TaskComment]):
            List of comments associated with the task.
    """

    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )

    executor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    last_executor_user_id: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[StatusTask] = mapped_column(
        Enum(StatusTask),
        nullable=False,
    )

    grade: Mapped[int] = mapped_column(default=None, nullable=True)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    comment: Mapped[List["TaskComment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self):
        return f"Task({self.id}) description={self.description[:30]}"


class TaskComment(Base):
    """
    Database model representing comments on tasks.

    Each comment belongs to a specific task and is created by a user.

    Attributes:
        id (int):
            Primary key identifier of the comment.

        user_id (int):
            Author of the comment.

        task_id (int):
            Task to which the comment belongs.

        text (str):
            Comment content.

        created_at (datetime):
            Timestamp when comment was created.

        task (Task):
            Relationship back to the task.
    """

    __tablename__ = "task_comments"
    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))

    text: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    task: Mapped["Task"] = relationship(back_populates="comment", lazy="selectin")

    def __repr__(self):
        return f"TaskComment({self.id}) text={self.text[:30]}"
