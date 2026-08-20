from typing import TYPE_CHECKING, List

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.model_base import Base

if TYPE_CHECKING:
    from src.models.model_meeting import Meeting, MeetingParticipant
    from src.models.model_team import TeamMember
    from src.models.model_tasks import Task

from dataclasses import dataclass


@dataclass
class PermissionResult:
    """
    Author: NeroGeer
    GitHub: https://github.com/NeroGeer
    License: MIT

    Result object representing evaluated permissions for a user.

    Attributes:
        is_admin (bool): Whether user has admin-level access.
        is_team_role (bool): Whether user has team-based role access.
        is_executor (bool): Whether user is an executor of a task/resource.
    """

    is_admin: bool
    is_team_role: bool
    is_executor: bool


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE")),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE")),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE")),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE")),
)


class User(Base):
    """
    Database model representing an application user.

    Users can:
        - Belong to multiple teams
        - Have multiple roles (RBAC system)
        - Participate in meetings
        - Create meetings

    Attributes:
        id (int):
            Primary key identifier.

        email (str):
            Unique user email used for authentication.

        hashed_password (str):
            Securely stored password hash.

        is_active (bool):
            Indicates whether user account is active.

        team_memberships (List[TeamMember]):
            Teams the user belongs to.

        roles (List[Role]):
            Assigned roles for RBAC permissions.

        created_meetings (List[Meeting]):
            Meetings created by the user.

        meeting_participations (List[MeetingParticipant]):
            Meetings where user is a participant.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True)

    team_memberships: Mapped[List["TeamMember"]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    roles: Mapped[List["Role"]] = relationship(
        secondary=user_roles, back_populates="users", lazy="selectin"
    )

    created_meetings: Mapped[List["Meeting"]] = relationship(
        back_populates="creator", lazy="selectin"
    )

    meeting_participations: Mapped[List["MeetingParticipant"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="executor",
        foreign_keys="Task.executor_user_id",
    )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, name={self.email})"


class Role(Base):
    """
    Role model for RBAC (Role-Based Access Control).

    Roles define a set of permissions that can be assigned to users.

    Attributes:
        id (int): Primary key.
        name (str): Unique role name.
        users (List[User]): Users assigned to this role.
        permissions (List[Permission]): Permissions granted by this role.
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    users: Mapped[List["User"]] = relationship(
        secondary=user_roles, back_populates="roles", lazy="selectin"
    )

    permissions: Mapped[List["Permission"]] = relationship(
        secondary="role_permissions", back_populates="roles", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Role(name={self.name})"


class Permission(Base):
    """
    Permission model for fine-grained access control.

    Permissions are assigned to roles and define specific allowed actions.

    Attributes:
        id (int): Primary key.
        name (str): Unique permission identifier.
        roles (List[Role]): Roles that include this permission.
    """

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    roles: Mapped[List["Role"]] = relationship(
        secondary="role_permissions", back_populates="permissions", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Permission(name={self.name})"
