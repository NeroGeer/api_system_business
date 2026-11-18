from datetime import datetime, UTC

from src.database.database import RedisStageService
from src.exceptions import exceptions as c_exp
from src.logger.logger import logger

from src.models.model_tasks import Task, TeamTaskStage
from src.scheme.schemas_task import (
    TaskCreateSchema,
    UpdateTaskSchema,
    UpdateTaskExecutorSchema,
    UpdateTaskStageSchema,
)
from src.scheme.schemas_task_stage import StageType
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

    async def _get_stage(
            self,
            team_id: int,
            stage_id: int,
    ):

        result = await self.repo.get_stage_id_for_task(team_id=team_id, stage_id=stage_id)

        stage = result.scalars().first()

        if stage is None:
            raise c_exp.StageNotFoundError(
                f"Stage {stage_id} not found in team {team_id}"
            )

        return stage

    async def _get_team_stages(
            self,
            team_id: int,
    ) -> list[TeamTaskStage]:

        result = await self.repo.get_stages_for_task(team_id=team_id)
        stages = result.scalars().all()

        if not stages:
            raise c_exp.StageNotFoundError(
                f"Stages not found for team {team_id}"
            )

        return stages

    async def _get_open_stage(
            self,
            team_id: int,
    ) -> TeamTaskStage:

        stages = await self._get_team_stages(team_id)

        open_stages = [
            stage
            for stage in stages
            if stage.stage_type == StageType.OPEN
        ]

        if len(open_stages) != 1:
            raise c_exp.InvalidWorkflowStructureError(
                "Workflow must contain exactly one OPEN stage"
            )

        return open_stages[0]

    async def _get_transitions(
            self,
            team_id: int,
    ) -> list:
        result = await self.repo.get_list_transitions_for_task(
            team_id=team_id,
        )

        return result.scalars().all()

    async def _check_transition(
            self,
            team_id: int,
            from_stage_id: int,
            to_stage_id: int,
    ) -> None:
        """
        Checks whether the transition is configured
        in the team's workflow.
        """

        transitions = await self._get_transitions(team_id)

        allowed = any(
            transition.from_stage_id == from_stage_id
            and transition.to_stage_id == to_stage_id
            for transition in transitions
        )

        if not allowed:
            raise c_exp.TaskStatusError(
                f"Transition {from_stage_id} -> {to_stage_id} is not allowed"
            )

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

        tasks = await self.repo.get(
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
        open_stage = await self._get_open_stage(team_id)

        new_task = Task(
            team_id=team_id,
            stage_id=open_stage.id,
            executor_user_id=data.executor_user_id,
            title=data.title,
            description=data.description,
            deadline=data.deadline,
        )

        logger.info(
            f"Task created: task_id={new_task.id}, "
            f"stage_id={open_stage.id}"
        )

        return await self.repo.create(data=new_task)

    async def update_task(
            self,
            data: UpdateTaskSchema,
    ):
        """
        Updates task fields:
            - title
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

        await self.ctx.require_admin_or_team_role_or_executor()

        task = await self.task_stmt(task_id=task_id, team_id=team_id)

        if data.title is not None:
            task.title = data.title

        if data.description is not None:
            task.description = data.description

        if data.deadline is not None:
            task.deadline = data.deadline

        logger.info(f"Task updated: task_id={task.id}")

        return await self.repo.update(task=task)

    async def update_task_stage(
            self,
            data: UpdateTaskStageSchema,
    ):
        """
        Author: NeroGeer
        GitHub: https://github.com/NeroGeer
        License: MIT

        Changes task stage according to team's workflow.

        Rules:
            - Only configured transitions are allowed.
            - Executor can perform configured transitions.
            - Executor cannot enter END or leave END.
            - Only admin/manager can enter END.
            - Entering END requires grade.
            - Leaving END clears grade and close_date.
            - Entering END sets close_date.
            - OPEN -> MIDDLE requires an assigned executor.
        """

        user_id = self.ctx.current_user.id
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id
        redis = RedisStageService(redis=self.ctx.redis)

        if data.stage_id is None:
            raise c_exp.TaskStatusError()

        logger.debug(
            f"Updating task stage: task_id={task_id}, "
            f"user_id={user_id}, target_stage={data.stage_id}"
        )

        result = await self.ctx.require_admin_or_team_role_or_executor(check_executor=True)
        task = await self.task_stmt(task_id=task_id, team_id=team_id)

        is_executor = task.executor_user_id == user_id
        is_privileged = result.is_admin or result.is_team_role

        if not is_privileged and not is_executor:
            raise c_exp.PermissionDeniedError()

        old_stage = await self._get_stage(
            team_id=team_id,
            stage_id=task.stage_id,
        )

        new_stage = await self._get_stage(
            team_id=team_id,
            stage_id=data.stage_id,
        )

        if old_stage.id == new_stage.id:
            raise c_exp.TaskStatusError(
                "Task is already in this stage"
            )

        await self._check_transition(
            team_id=team_id,
            from_stage_id=old_stage.id,
            to_stage_id=new_stage.id,
        )

        leaving_end = old_stage.stage_type == StageType.END
        entering_end = new_stage.stage_type == StageType.END

        # Executor restrictions.
        if not is_privileged:

            if not is_executor:
                raise c_exp.PermissionDeniedError()

            if entering_end or leaving_end:
                raise c_exp.PermissionDeniedError(
                    "Only manager or administrator can close or reopen a task"
                )

        if (
                old_stage.stage_type == StageType.OPEN
                and new_stage.stage_type == StageType.MIDDLE
                and task.executor_user_id is None
        ):
            raise c_exp.ExecutorDataError()

        # Closing task.
        if entering_end:

            if not is_privileged:
                raise c_exp.PermissionDeniedError()

            if data.grade is None:
                raise c_exp.GradeDataError()

            task.grade = data.grade
            task.close_date = datetime.now(UTC)

            logger.info(
                f"Task closed: task_id={task.id}, grade={task.grade}"
            )

        elif leaving_end:

            if not is_privileged:
                raise c_exp.PermissionDeniedError()

            task.grade = None
            task.close_date = None

            logger.info(
                f"Task reopened: task_id={task.id}"
            )

        else:
            if data.grade is not None:
                raise c_exp.GradeDataError(
                    "Grade can only be assigned when entering END"
                )

        task.stage_id = new_stage.id

        logger.debug(
            f"Task stage updated: task_id={task.id}, "
            f"from={old_stage.id}, to={new_stage.id}"
        )

        await redis.delete_transactions(task_id=task.id)

        await redis.add_transaction(
            task_id=task.id,
            from_stage_id=old_stage,
            to_stage_id=new_stage,
            user_id=self.ctx.current_user.id,
        )

        return await self.repo.update(task=task)

    async def update_task_executor(
            self,
            data: UpdateTaskExecutorSchema,
    ):
        """
        Author: NeroGeer
        GitHub: https://github.com/NeroGeer
        License: MIT

        Handles task Executor transitions.
        """

        user_id = self.ctx.current_user.id
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id

        logger.debug(f"Updating task Executor: task_id={task_id}, user_id={user_id}")

        is_privileged = await self.ctx.require_admin_or_team_role_or_executor(check_executor=True)
        task = await self.task_stmt(task_id=task_id, team_id=team_id)

        current_stage = await self._get_stage(
            team_id=team_id,
            stage_id=task.stage_id,
        )

        is_current_executor = data.executor_user_id == user_id

        if is_current_executor and not is_privileged:

            if (
                    current_stage.stage_type != StageType.OPEN
                    or task.executor_user_id is not None
            ):
                raise c_exp.PermissionDeniedError()

            task.executor_user_id = user_id

        elif is_privileged:

            if current_stage.stage_type != StageType.OPEN:
                raise c_exp.TaskStatusError(
                    "Executor can only be changed in OPEN stage"
                )

            if data.executor_user_id is not None:

                await self.validate_user_in_team(
                    user_id=data.executor_user_id,
                    team_id=team_id,
                )

                task.executor_user_id = data.executor_user_id

            else:

                if task.executor_user_id is None:
                    raise c_exp.ExecutorDataError()

                task.last_executor_user_id = task.executor_user_id
                task.executor_user_id = None

        else:
            raise c_exp.PermissionDeniedError()

        logger.debug(
            f"Task executor updated: task_id={task.id}, "
            f"executor={task.executor_user_id}"
        )

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

        user_id = self.ctx.current_user.id
        team_id = self.ctx.scope.team_id
        task_id = self.ctx.scope.task_id

        logger.debug(
            f"Deleting task: task_id={task_id}, team_id={team_id}, user_id={user_id}"
        )

        await self.ctx.require_admin_or_team_role_or_executor()

        task = await self.task_stmt(task_id=task_id, team_id=team_id)

        current_stage = await self._get_stage(
            team_id=team_id,
            stage_id=task.stage_id,
        )

        if current_stage.stage_type not in (
                StageType.OPEN,
                StageType.END,
        ):
            raise c_exp.TaskStatusError(
                "Only tasks in OPEN or END can be deleted"
            )

        await self.repo.delete(task=task)

        logger.debug(
            f"Task deleted: task_id={task_id}, team_id={team_id}"
        )

        return {"message": "Task deleted"}
