from datetime import date
from typing import Annotated, Generic, TypeVar, Type

from pydantic import BaseModel, Field
from fastapi import Depends

from src.exceptions import exceptions as c_exp
from src.models.model_user import User
from src.database.database import SessionDep, RedisDep
from src.core.security import dependencies as jwt
from src.core.security.rbac import has_role, has_permission
from src.models.model_user import PermissionResult
from src.core.context.context_service import ContextService
from src.core.context.context_repository import ContextRepository
from src.scheme.schemas_team import TeamRole
from src.scheme.schemas_user import UserRole


class Scope(BaseModel):
    team_id: int | None = None
    task_id: int | None = None
    user_id: int | None = None
    comment_id: int | None = None
    meeting_id: int | None = None


def build_scope(
        team_id: int | None = None,
        task_id: int | None = None,
        user_id: int | None = None,
        comment_id: int | None = None,
        meeting_id: int | None = None,
) -> Scope:
    return Scope(
        team_id=team_id,
        task_id=task_id,
        user_id=user_id,
        comment_id=comment_id,
        meeting_id=meeting_id,
    )


class BaseFilters(BaseModel):
    pass


class UserFilter(BaseFilters):
    invite_code: str


class TaskFilter(BaseFilters):
    only_my: bool = Field(False, description='Only my tasks or meeting bools check')
    executor_user_id: int | None = Field(None, description='participant or executor user id')
    start_date: date | None = Field(None)
    end_date: date | None = Field(None)


class DateFilter(BaseFilters):
    start_date: date | None = None
    end_date: date | None = None


class MeetingFilter(BaseFilters):
    users_ids: list[int]


F = TypeVar("F", bound=BaseFilters)


class BaseContext(Generic[F]):
    def __init__(
            self,
            current_user: User,
            session: SessionDep,
            redis: RedisDep,
            scope: Scope | None = None,
            filters: F | None = None,
    ):
        self.current_user = current_user
        self.session = session
        self.redis = redis
        self.scope = scope
        self.filters = filters

    def require_admin(self):
        """
               Permission guard for admin access only.

               This function verifies whether a user has permission.

               Logic:
               - checks if user is admin

               Args:
                   self.current_user: Authenticated user.

               Raises:
                   HTTPException:
                       - 403 if user has no required permissions
               """
        if not has_role(user=self.current_user, roles={UserRole.admin}):
            raise c_exp.ForbiddenError()

    def require_permission(self,
                           permission: str
                           ):
        """
        FastAPI dependency that restricts access based on a specific permission.

        Args:
            self.current_user: Authenticated user.
            permission (str): Required permission name.

        """
        if not has_permission(user=self.current_user, permission=permission):
            raise c_exp.PermissionDeniedError()

    async def require_admin_or_team_role_or_executor(
            self,
            team_role: set[TeamRole] | None = None,
            check_executor: bool = False,
    ) -> PermissionResult:
        """
        Permission guard for admin, team roles or task executor access.

        This function verifies whether a user has permission to perform
        actions inside a specific team context.

        Logic:
        - checks if team exists
        - checks if user is admin
        - checks if user has required team role
        - optionally checks if user is task executor

        Args:
            self.session: Database session dependency.
            self.current_user: Authenticated user.
            self.scope.team_id: Target team ID.
            team_role: Allowed team roles (default: manager).
            check_executor: Enable executor permission check.
            self.scope.task_id: Required if check_executor=True.

        Returns:
            PermissionResult:
                Object containing:
                - is_admin
                - is_team_role
                - is_executor

        Raises:
            - 404 if team not found
            - 422 if task_id missing when check_executor=True
            - 403 if user has no required permissions
        """

        if self.scope is None or self.scope.team_id is None:
            raise c_exp.TeamRequiredError()

        team_id = self.scope.team_id
        task_id = self.scope.task_id
        user = self.current_user

        serv_fact = build_service(repository_cls=ContextRepository,
                                  service_cls=ContextService, session=self.session)

        check_roles: set[TeamRole] = team_role if team_role is not None else {TeamRole.manager}

        await serv_fact.get_team(team_id=team_id)

        is_team_role = False
        is_executor = False

        is_admin = has_role(user=user, roles={UserRole.admin})

        if not is_admin:
            is_team_role = await serv_fact.has_team_role(
                user_id=user.id,
                team_id=team_id,
                roles=check_roles,
            )

            is_executor = False

            if check_executor:
                if task_id is None:
                    raise c_exp.FilterContextError()

                is_executor = await serv_fact.check_executor(user_id=user.id, team_id=team_id, task_id=task_id)

        if not (is_admin or is_team_role or is_executor):
            raise c_exp.ForbiddenError()

        return PermissionResult(
            is_admin=is_admin,
            is_team_role=is_team_role,
            is_executor=is_executor,
        )


def build_context_with_filters(filter_schema: Type[F] | None = None):
    async def _dependency(
            session: SessionDep,
            redis: RedisDep,
            scope: Annotated[Scope, Depends(build_scope)],
            current_user: Annotated[User, Depends(jwt.get_current_user)],
            filters=Depends(filter_schema) if filter_schema else None,
    ) -> BaseContext[F]:
        return BaseContext(
            session=session,
            redis=redis,
            scope=scope,
            current_user=current_user,
            filters=filters,
        )

    return _dependency


def build_service(repository_cls, service_cls, session, ctx=None):
    return service_cls(repository_cls(session=session), context=ctx)
