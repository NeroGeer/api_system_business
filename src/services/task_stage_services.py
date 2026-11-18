from typing import Iterable

from src.exceptions import exceptions as c_exp
from src.logger.logger import logger
from src.scheme.schemas_team import TeamRole
from src.models.model_tasks import TeamTaskStage
from src.scheme.schemas_task_stage import StageCreate, StageSchemaRead, UpdateStageRename, StageType, TransitionItem
from src.database.database import RedisStageService


class StageManagementService:
    """
    Manages a team's workflow definition only.

    It deliberately does NOT implement task transitions. A separate transition
    service should consume this configuration later.
    """

    def __init__(self, repo, context=None):
        self.repo = repo
        self.ctx = context

    @staticmethod
    def validate_structure(stages: list[TeamTaskStage]) -> None:
        """
        O(n) validation. The list must already be ordered by position.
        """
        if len(stages) < 2:
            raise c_exp.InvalidWorkflowStructureError("Workflow needs OPEN and END")

        if stages[0].stage_type != StageType.OPEN:
            raise c_exp.InvalidWorkflowStructureError("Position 0 must be OPEN")

        if stages[-1].stage_type != StageType.END:
            raise c_exp.InvalidWorkflowStructureError("Last position must be END")

        open_count = 0
        end_count = 0

        for expected_position, stage in enumerate(stages):
            if stage.position != expected_position:
                raise c_exp.InvalidWorkflowStructureError(
                    f"Expected position {expected_position}, got {stage.position}"
                )

            if stage.stage_type == StageType.OPEN:
                open_count += 1
                if expected_position != 0:
                    raise c_exp.InvalidWorkflowStructureError("OPEN must be first")

            elif stage.stage_type == StageType.END:
                end_count += 1
                if expected_position != len(stages) - 1:
                    raise c_exp.InvalidWorkflowStructureError("END must be last")

            elif stage.stage_type != StageType.MIDDLE:
                raise c_exp.InvalidWorkflowStructureError("Unknown stage type")

        if open_count != 1 or end_count != 1:
            raise c_exp.InvalidWorkflowStructureError("Exactly one OPEN and one END required")

    async def get_stages_by_team_id(self):

        await self.ctx.require_admin_or_team_role_or_executor(
            team_role={TeamRole.manager, TeamRole.employee}
        )
        team_id = self.ctx.scope.team_id

        result = await self.repo.get(team_id)
        if not result:
            logger.warning(f"Team no found with ID: {team_id}")
            raise c_exp.TeamNotFoundError()

        return list(result.scalars().all())

    async def get_stages_id_by_team_id(self):

        await self.ctx.require_admin_or_team_role_or_executor(
            team_role={TeamRole.manager, TeamRole.employee}
        )
        team_id = self.ctx.scope.team_id
        stage_id = self.ctx.scope.stage_id
        result = await self.repo.get_stage_id(team_id=team_id, stage_id=stage_id)

        if result is None:
            logger.warning(f"Stage {stage_id} not found")
            raise c_exp.StageNotFoundError(f"Stage {stage_id} not found")

        return result.scalars().all()

    async def create_middle_stage(self, data: StageCreate) -> StageSchemaRead:

        team_id = self.ctx.scope.team_id

        permission_check = await self.ctx.require_admin_or_team_role_or_executor()
        is_privileged = permission_check.is_admin or permission_check.is_team_role

        if is_privileged:

            result_team = await self.repo.check_team(team_id)
            if not result_team:
                logger.warning(f"Team no found with ID: {team_id}")
                raise c_exp.TeamNotFoundError()

            stages_result = await self.repo.get(team_id)
            stages = stages_result.scalars().all()
            if stages is None:
                logger.warning(f"Stage not found")
                raise c_exp.StageNotFoundError(f"Stage  not found")

            self.validate_structure(stages)

            end_position = stages[-1].position
            position = (
                end_position if data.position is None else data.position
            )

            # Valid insertion points are after OPEN and at/before END.
            if position < 1 <= end_position:
                raise c_exp.InvalidStageOperationError(
                    "MIDDLE can only be inserted after OPEN"
                )

            await self.repo.update_positions_up(team_id, position)

            stage = TeamTaskStage(
                team_id=team_id,
                name=data.name,
                stage_type=StageType.MIDDLE,
                position=position,
            )

            logger.info(f"Task created: task_id={stage.id}")
            return await self.repo.create(stage=stage)

    async def update_name_stage(
            self, data: UpdateStageRename
    ) -> StageSchemaRead:

        team_id = self.ctx.scope.team_id
        stage_id = self.ctx.scope.stage_id

        permission_check = await self.ctx.require_admin_or_team_role_or_executor()
        is_privileged = permission_check.is_admin or permission_check.is_team_role

        if is_privileged:

            result_team = await self.repo.check_team(team_id)
            if not result_team:
                logger.warning(f"Team no found with ID: {team_id}")
                raise c_exp.TeamNotFoundError()

            stage = await self.repo.get_stage_id(team_id, stage_id)
            if stage is None:
                logger.warning(f"Stage {stage_id} not found")
                raise c_exp.StageNotFoundError(f"Stage {stage_id} not found")

            stage.name = data.name
            return await self.repo.update(data=stage)

    async def delete_middle_stage(self):

        team_id = self.ctx.scope.team_id
        stage_id = self.ctx.scope.stage_id

        permission_check = await self.ctx.require_admin_or_team_role_or_executor()
        is_privileged = permission_check.is_admin or permission_check.is_team_role

        if is_privileged:
            result_team = await self.repo.check_team(team_id)
            if not result_team:
                logger.warning(f"Team no found with ID: {team_id}")
                raise c_exp.TeamNotFoundError()

            result = await self.repo.get_stage_id(team_id, stage_id)

            if result is None:
                logger.warning(f"Stage {stage_id} not found")
                raise c_exp.StageNotFoundError(f"Stage {stage_id} not found")

            if result.stage_type != StageType.MIDDLE:
                raise c_exp.InvalidStageOperationError("OPEN and END cannot be deleted")

            task_count = await self.repo.get_count_tasks_by_stage(
                team_id=team_id,
                stage_id=stage_id,
            )
            if task_count:
                raise c_exp.StageInUseError(
                    f"Cannot delete stage {stage_id}: {task_count} task(s) use it"
                )

            deleted_position = result.position
            await self.repo.delete(result)
            await self.repo.update_positions_down(
                team_id, deleted_position
            )

            return {"message": "Stage deleted"}

    async def get_transitions(self):
        team_id = self.ctx.scope.team_id
        redis = RedisStageService(redis=self.ctx.redis)

        await self.ctx.require_admin_or_team_role_or_executor(
            team_role={TeamRole.manager, TeamRole.employee}
        )

        result_team = await self.repo.check_team(team_id)
        if not result_team:
            logger.warning(f"Team no found with ID: {team_id}")
            raise c_exp.TeamNotFoundError()

        stages_result = await self.repo.get(team_id)
        if stages_result is None:
            logger.warning(f"Stage not found")
            raise c_exp.StageNotFoundError(f"Stage not found")

        async def load_from_db():

            transitions_result = await self.repo.get_list_transitions(team_id=team_id)

            transitions = transitions_result.scalars().all()

            return [
                {
                    "from_stage_id": item.from_stage_id,
                    "to_stage_id": item.to_stage_id,
                }
                for item in transitions]

        return await redis.get_team_transitions(
            team_id=team_id,
            loader=load_from_db,
        )

    async def replace_transitions(
        self, transitions: Iterable[TransitionItem]
    ):

        team_id = self.ctx.scope.team_id
        redis = RedisStageService(redis=self.ctx.redis)

        permission_check = await self.ctx.require_admin_or_team_role_or_executor()
        is_privileged = permission_check.is_admin or permission_check.is_team_role

        if is_privileged:

            result_team = await self.repo.check_team(team_id)
            if not result_team:
                logger.warning(f"Team no found with ID: {team_id}")
                raise c_exp.TeamNotFoundError()

            normalized: list[tuple[int, int]] = []
            seen: set[tuple[int, int]] = set()
            for item in transitions:
                pair = (item.from_, item.to)
                if pair[0] == pair[1]:
                    raise c_exp.InvalidTransitionConfigurationError()

                if pair in seen:
                    raise c_exp.InvalidTransitionConfigurationError(
                        f"patch already: {pair[0]} -> {pair[1]}"
                    )
                seen.add(pair)
                normalized.append(pair)

            stage_result = await self.repo.get(team_id=team_id)
            valid_stage_ids = {
                stage.id
                for stage in stage_result.scalars().all()
            }

            invalid = sorted({
                stage_id
                for pair in normalized
                for stage_id in pair
                if stage_id not in valid_stage_ids
            })
            if invalid:
                raise c_exp.StageNotFoundError()

            transitions_result = await self.repo.get_transitions(team_id=team_id,
                                                                 normalized=normalized
                                                                 )
            await redis.invalidate_team_transitions(
                team_id=team_id
            )

            return transitions_result.scalars().all()
