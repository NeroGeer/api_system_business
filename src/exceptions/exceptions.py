class AppError(Exception):
    """Базовое исключение для всех ошибок приложения"""
    status_code: int = 400
    detail: str = "Application error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class FilterContextError(AppError):
    status_code = 422
    detail = "task_id is required when check_executor=True"


class UserAlreadyExistsError(AppError):
    status_code = 409
    detail = "Email already registered"


class TeamMemberAlreadyExistsError(AppError):
    status_code = 409
    detail = "User already in team"


class UserNotFoundError(AppError):
    status_code = 404
    detail = "User not found"


class TeamNotFoundError(AppError):
    status_code = 404
    detail = "Team not found"


class MemberNotFoundError(AppError):
    status_code = 404
    detail = "Member not found in Team"


class TaskNotFoundError(AppError):
    status_code = 404
    detail = "Task not found"


class MeetingNotFoundError(AppError):
    status_code = 404
    detail = "Meeting not found"


class TeamRoleNotFoundError(AppError):
    status_code = 404
    detail = "Team Role not found"


class TeamMemberNotFoundError(AppError):
    status_code = 404
    detail = "Member not found"


class CommentNotFoundError(AppError):
    status_code = 404
    detail = "Comment not found"


class ExecutorNotFoundInTeamError(AppError):
    status_code = 404
    detail = "Executor must be a member of the team"


class CreatorNotFoundInTeamError(AppError):
    status_code = 404
    detail = "Creator must be a member of the team"


class PermissionDeniedError(AppError):
    status_code = 403
    detail = "Permission denied"


class ForbiddenError(AppError):
    status_code = 403
    detail = "Forbidden"


class InvalidCredentialsError(AppError):
    status_code = 401
    detail = "Invalid email or password"


class InvalidAccessTokenError(AppError):
    status_code = 401
    detail = "Invalid token"


class InvalidSubTokenError(AppError):
    status_code = 401
    detail = "Invalid token"


class InvalidRefreshTokenError(AppError):
    status_code = 401
    detail = "Invalid token"


class ExpiredRefreshTokenError(AppError):
    status_code = 401
    detail = "Invalid token"


class EmptyDataError(AppError):
    status_code = 400
    detail = "No data to update"


class ExecutorDataError(AppError):
    status_code = 400
    detail = "Cannot unassign executor: the task has no assigned executor."


class GradeDataError(AppError):
    status_code = 400
    detail = "Grade is required when closing a task."


class MeetingConflictError(AppError):
    status_code = 400
    detail = "Users already have meetings"


class SelfRemovalError(AppError):
    status_code = 400
    detail = "You cannot remove yourself"


class TeamCreateError(AppError):
    status_code = 400
    detail = "Team name or invite code already exists"


class ConflictingFiltersError(AppError):
    status_code = 400
    detail = "Conflicting filters: use only_my_tasks OR executor_user_id"


class InvalidTimeRangeError(AppError):
    status_code = 400
    detail = "Invalid time range"


class TeamRequiredError(AppError):
    status_code = 400
    detail = "team_id required"


class TaskStatusError(AppError):
    status_code = 400
    detail = "Invalid status transition"
