from datetime import UTC, datetime
from typing import List

from sqlalchemy import (DateTime, ForeignKey, String, Enum as SAEnum,
                        func, Index, text, UniqueConstraint,
                        CheckConstraint, ForeignKeyConstraint, )
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.model_base import Base
from src.scheme.schemas_task_stage import StageType


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
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    stage_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )

    executor: Mapped["User | None"] = relationship(
        "User"
    )

    last_executor_user_id: Mapped[int | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    grade: Mapped[int | None] = mapped_column(default=None, nullable=True)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    comment: Mapped[List["TaskComment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    change_stage_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        default=None,
        index=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["team_id", "stage_id"],
            ["team_task_stages.team_id", "team_task_stages.id"],
            ondelete="RESTRICT",
            name="fk_task_stage_same_team",
        ),
    )

    def __repr__(self):
        return f"Task({self.id}) description={self.description[:30]}"


class TeamTaskStage(Base):
    __tablename__ = "team_task_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_type: Mapped[StageType] = mapped_column(
        SAEnum(
            StageType,
            name="task_stage_type",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        default=None,
        index=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    outgoing_transitions: Mapped[list["TeamStageTransition"]] = relationship(
        "TeamStageTransition",
        primaryjoin="and_(TeamTaskStage.team_id == TeamStageTransition.team_id, TeamTaskStage.id == "
                    "TeamStageTransition.from_stage_id)",
        foreign_keys="[TeamStageTransition.team_id, TeamStageTransition.from_stage_id]",
        back_populates="from_stage",
        overlaps="incoming_transitions,to_stage",
    )
    incoming_transitions: Mapped[list["TeamStageTransition"]] = relationship(
        "TeamStageTransition",
        primaryjoin="and_(TeamTaskStage.team_id == TeamStageTransition.team_id, TeamTaskStage.id == "
                    "TeamStageTransition.to_stage_id)",
        foreign_keys="[TeamStageTransition.team_id, TeamStageTransition.to_stage_id]",
        back_populates="to_stage",
        overlaps="outgoing_transitions,from_stage",
    )

    __table_args__ = (
        # PostgreSQL deferrable constraint allows positions to be shifted
        # without transient uniqueness collisions inside one transaction.
        UniqueConstraint(
            "team_id",
            "id",
            name="uq_team_task_stages_team_id_id"
        ),

        UniqueConstraint(
            "team_id", "position",
            name="uq_team_stage_position",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index(
            "uq_team_open_stage", "team_id", unique=True,
            postgresql_where=text("stage_type = 'OPEN' AND deleted_at IS NULL"),
        ),
        Index(
            "uq_team_end_stage", "team_id", unique=True,
            postgresql_where=text("stage_type = 'END' AND deleted_at IS NULL"),
        ),
        CheckConstraint("position >= 0", name="ck_team_stage_position"),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_team_stage_name_not_empty",
        ),
    )


class TeamStageTransition(Base):
    __tablename__ = "team_stage_transitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    from_stage_id: Mapped[int] = mapped_column(nullable=False)
    to_stage_id: Mapped[int] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    from_stage: Mapped["TeamTaskStage"] = relationship(
        "TeamTaskStage",
        primaryjoin="and_(TeamStageTransition.team_id == TeamTaskStage.team_id, TeamStageTransition.from_stage_id == "
                    "TeamTaskStage.id)",
        foreign_keys="[TeamStageTransition.team_id, TeamStageTransition.from_stage_id]",
        back_populates="outgoing_transitions",
        overlaps="incoming_transitions,to_stage",
    )
    to_stage: Mapped["TeamTaskStage"] = relationship(
        "TeamTaskStage",
        primaryjoin="and_(TeamStageTransition.team_id == TeamTaskStage.team_id, TeamStageTransition.to_stage_id == "
                    "TeamTaskStage.id)",
        foreign_keys="[TeamStageTransition.team_id, TeamStageTransition.to_stage_id]",
        back_populates="incoming_transitions",
        overlaps="outgoing_transitions,from_stage",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["team_id", "from_stage_id"],
            ["team_task_stages.team_id", "team_task_stages.id"],
            ondelete="CASCADE",
            name="fk_transition_from_stage_same_team",
        ),
        ForeignKeyConstraint(
            ["team_id", "to_stage_id"],
            ["team_task_stages.team_id", "team_task_stages.id"],
            ondelete="CASCADE",
            name="fk_transition_to_stage_same_team",
        ),
        UniqueConstraint(
            "team_id",
            "from_stage_id",
            "to_stage_id",
            name="uq_team_stage_transition",
        ),
        CheckConstraint(
            "from_stage_id <> to_stage_id",
            name="ck_stage_transition_not_self",
        ),
    )


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
