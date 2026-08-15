from datetime import datetime, UTC

from src.exceptions import exceptions as c_exp
from src.logger.logger import logger
from src.models.model_tasks import Task
from src.scheme.schemas_task import StatusTask, TaskCreateSchema, UpdateTaskSchema, UpdateTaskStatusSchema
from src.scheme.schemas_team import TeamRole
from src.utils.utils import make_date_range, normalize_date_range


class TaskService:
    def __init__(self, repo, context=None):
        self.repo = repo
        self.ctx = context

    async def validate_user_in_team(self, user_id: int, team_id: int):
        """
        Checks whether a user is a member of a given team.
        """
        if not await self.repo.validate_team(
                user_id=user_id,
                team_id=team_id
        ):
            raise c_exp.ExecutorNotFoundInTeamError()

    async def task_stmt(self, task_id: int, team_id: int) -> Task | None:
        """
        Fetch a task by ID within a specific team.

        Returns:
            Task object
        """

        task = await self.repo.get_task_id(task_id=task_id, team_id=team_id)
        if task is None:
            logger.warning(f"Task not found: task_id={task_id}, team_id={team_id}")
            raise c_exp.TaskNotFoundError()
        return task

    @staticmethod
    def resolve_task_status(executor_user_id: int | None) -> StatusTask:
        """
        Resolve task status based on executor assignment.
        """
        return StatusTask.work if executor_user_id else StatusTask.open

    async def get_tasks_or_task_by_id(self):
        """
        Retrieve tasks for a team with optional filters.

        Supports:
            - filtering by executor
            - filtering only current user tasks
            - filtering by date range

        Returns:
            Task | list[Task]
        """

        user_id = self.ctx.current_user.id
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id
        only_my_tasks = self.ctx.filters.only_my
        executor_user_id = self.ctx.filters.executor_user_id
        start_date = self.ctx.filters.start_date
        end_date = self.ctx.filters.end_date

        logger.debug(
            f"Fetching tasks: user_id={user_id}, team_id={team_id}, "
            f"task_id={task_id}"
        )
        await self.ctx.require_admin_or_team_role_or_executor(
            team_role={TeamRole.manager, TeamRole.employee}
        )

        if task_id is not None:
            task = await self.task_stmt(task_id=task_id, team_id=team_id)

            return task

        if start_date is not None and end_date is not None:
            start_date, end_date = await make_date_range(start_date, end_date)

        if only_my_tasks and executor_user_id is not None:
            raise c_exp.ConflictingFiltersError()

        if only_my_tasks:
            executor_user_id = user_id

        if executor_user_id is not None:
            await self.validate_user_in_team(
                    user_id=executor_user_id,
                    team_id=team_id
            )

        tasks = self.repo.get(
            team_id=team_id,
            executor_user_id=executor_user_id,
            start_dt=start_date, end_dt=end_date)

        return tasks

    async def get_avg_grade_task_make_date_range(self):

        user_id = self.ctx.current_user.id
        team_id = self.ctx.scope.team_id
        start_date = self.ctx.filters.start_date
        end_date = self.ctx.filters.end_date

        await self.ctx.require_admin_or_team_role_or_executor(
            team_role={TeamRole.manager, TeamRole.employee}
        )

        start_date, end_date = await normalize_date_range(
            start_date=start_date, end_date=end_date
        )

        logger.debug(
            f"Calculating avg grade: user_id={user_id}, team_id={team_id}, "
            f"range=({start_date} -> {end_date})"
        )

        start_dt, end_dt = await make_date_range(start=start_date, end=end_date)

        return await self.repo.get_avg_grade(
            team_id=team_id,
            start_dt=start_dt,
            end_dt=end_dt,
            user_id=user_id
        )

    async def create_task(
        self, data: TaskCreateSchema
    ):
        """
        Author: NeroGeer
        GitHub: https://github.com/NeroGeer
        License: MIT

        Creates a new task in a team.

        Rules:
            - only admin or team manager can create
            - executor must belong to team (if provided)
            - status is auto-resolved
        """

        user_id = self.ctx.current_user.id
        team_id = self.ctx.scope.team_id

        logger.info(f"Creating task: user_id={user_id}, team_id={team_id}")

        await self.ctx.require_admin_or_team_role_or_executor()

        if data.executor_user_id is not None:
            await self.validate_user_in_team(
                user_id=data.executor_user_id,
                team_id=team_id
            )

        new_task = Task(
            team_id=team_id,
            executor_user_id=data.executor_user_id,
            description=data.description,
            deadline=data.deadline,
            status=self.resolve_task_status(data.executor_user_id),
        )

        logger.info(f"Task created: task_id={new_task.id}")
        return await self.repo.create(new_task=new_task)

    async def update_task(
        self,
        data: UpdateTaskSchema,
    ):
        """
        Updates task fields:
            - executor user
            - description
            - deadline
            - auto status recalculation

        Rules:
            - executor must belong to team
            - status is auto-derived from executor

        """

        current_user = self.ctx.current_user.id
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id

        if not data or data is None:
            raise c_exp.EmptyDataError()

        logger.debug(f"Updating task: task_id={task_id}, user_id={current_user.id}")

        await self.ctx.require_admin_or_team_role_or_executor(check_executor=True)

        task = await self.task_stmt(task_id=task_id, team_id=team_id)

        if data.description is not None:
            task.description = data.description

        if data.deadline is not None:
            task.deadline = data.deadline

        logger.info(f"Task updated: task_id={task.id}")

        return await self.repo.update(task=task)

    async def update_task_status(
        self,
        data: UpdateTaskStatusSchema,
    ):
        """
        Author: NeroGeer
        GitHub: https://github.com/NeroGeer
        License: MIT

        Handles task status transitions.

        Rules:
            - closing task requires grade
            - reopening task clears grade and close_date
            - status transitions are validated
        """

        user_id = self.ctx.current_user.id
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id

        logger.debug(f"Updating task status: task_id={task_id}, user_id={user_id}")

        result = await self.ctx.require_admin_or_team_role_or_executor(check_executor=True)
        task = await self.task_stmt(task_id=task_id, team_id=team_id)

        is_current_executor = (task.executor_user_id == user_id)

        old_status = task.status
        new_status = data.status if data.status is not None else old_status

        if is_current_executor and not (result.is_admin or result.is_team_role):

            if data.status is not None and data.status != old_status:
                if data.status == StatusTask.review:
                    task.status = data.status

                elif data.status == StatusTask.open:
                    task.last_executor_user_id = is_current_executor
                    task.status = data.status

        elif result.is_admin or result.is_team_role:

            if data.executor_user_id is not None and task.executor_user_id != data.executor_user_id:
                await self.validate_user_in_team(
                    user_id=data.executor_user_id,
                    team_id=team_id
                )
                task.executor_user_id = data.executor_user_id
                task.status = StatusTask.work
                task.grade = None
                task.close_date = None

            elif old_status != StatusTask.closed and new_status == StatusTask.closed:
                if data.grade is None:
                    raise c_exp.GradeDataError()

                task.grade = data.grade
                task.status = new_status
                task.close_date = datetime.now(UTC)

                logger.debug(f"Task closed: task_id={task.id}, grade={task.grade}")

            elif old_status == StatusTask.closed and new_status == StatusTask.closed:
                if data.grade is None:
                    raise c_exp.GradeDataError()
                task.grade = data.grade

            elif old_status == StatusTask.closed and new_status in [
                StatusTask.open,
                StatusTask.work,
            ]:
                task.grade = None
                task.close_date = None
                logger.info(f"Task reopened: task_id={task.id}")

                if new_status == StatusTask.work:
                    task.executor_user_id = task.last_executor_user_id

                task.status = new_status
        else:
            raise c_exp.PermissionDeniedError()

        logger.debug(f"Task status updated: task_id={task.id}, status={task.status}")

        return await self.repo.update(task=task)

    async def delete_task(self):
        """
        Deletes a task permanently from a team.

        Rules:
            - only admin or team manager can delete tasks
            - task must belong to specified team

        Returns:
            dict: Confirmation message
        """

        user_id = self.ctx.current_user
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id

        logger.debug(
            f"Deleting task: task_id={task_id}, team_id={team_id}, user_id={user_id}"
        )

        await self.ctx.require_admin_or_team_role_or_executor()

        task = await self.task_stmt(task_id=task_id, team_id=team_id)

        await self.repo.delete(task=task)
        logger.debug(f"Task deleted: task_id={task_id}, team_id={team_id}")

        return {"message": "Task deleted"}
