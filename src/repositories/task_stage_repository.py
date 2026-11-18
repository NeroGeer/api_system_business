from sqlalchemy import func, select, update, delete
from datetime import datetime, UTC

from src.models.model_tasks import Task, TeamTaskStage, TeamStageTransition
from src.models.model_team import Team
from src.database.database import SessionDep


class StageRepository:
    """
    Database access only. Business rules live in the service.

    The repository assumes PostgreSQL for deferred uniqueness and partial
    unique indexes. All position changes are set-based SQL, not Python loops.
    """

    def __init__(self, session: SessionDep):
        self.session = session

    async def check_team(self, team_id: int):
        result = await self.session.execute(
            select(Team.id).where(Team.id == team_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get(self, team_id: int):
        result = await self.session.execute(
            select(TeamTaskStage)
            .where(
                TeamTaskStage.team_id == team_id,
                TeamTaskStage.deleted_at.is_(None))
            .order_by(TeamTaskStage.position.asc())
        )
        return result

    async def get_stage_id(
        self, team_id: int, stage_id: int
    ):
        result = await self.session.execute(
            select(TeamTaskStage).where(
                TeamTaskStage.team_id == team_id,
                TeamTaskStage.id == stage_id,
                TeamTaskStage.deleted_at.is_(None)
            )
        )
        return result

    async def update_positions_up(
        self, team_id: int, from_position: int
    ) -> None:
        """
        Insert a gap at from_position:
        every stage at/after it moves one position right.
        One UPDATE statement; DB work is proportional to affected rows.
        """
        await self.session.execute(
            update(TeamTaskStage)
            .where(
                TeamTaskStage.team_id == team_id,
                TeamTaskStage.position >= from_position,
            )
            .values(position=TeamTaskStage.position + 1)
            .execution_options(synchronize_session=False)
        )
        self.session.expire_all()

    async def update_positions_down(
        self, team_id: int, after_position: int
    ) -> None:
        """
        Close the gap left by deleting after_position:
        every later stage moves one position left.
        One UPDATE statement.
        """
        await self.session.execute(
            update(TeamTaskStage)
            .where(
                TeamTaskStage.team_id == team_id,
                TeamTaskStage.position > after_position,
            )
            .values(position=TeamTaskStage.position - 1)
            .execution_options(synchronize_session="fetch")
        )
        self.session.expire_all()

    async def create(self, stage: TeamTaskStage):
        self.session.add(stage)
        await self.session.commit()
        await self.session.refresh(stage)
        return stage

    async def update(
            self,
            data: TeamTaskStage,
    ):
        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def get_count_tasks_by_stage(self, team_id: int, stage_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Task)
            .where(
                Task.team_id == team_id,
                Task.stage_id == stage_id,
                Task.deleted_at.is_(None)
            )
        )
        return int(result.scalar_one())

    async def delete(self, stage: TeamTaskStage):
        stage.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def get_list_transitions(self, team_id: int):
        result = await self.session.execute(
            select(TeamStageTransition)
            .where(TeamStageTransition.team_id == team_id)
            .order_by(
                TeamStageTransition.from_stage_id,
                TeamStageTransition.to_stage_id,
            )
        )

        return result

    async def get_transitions(
        self,  team_id: int, normalized: list[tuple[int, int]]
    ):
        async with self.session.begin_nested():
            await self.session.execute(
                delete(TeamStageTransition).where(
                    TeamStageTransition.team_id == team_id
                )
            )
            self.session.add_all([
                TeamStageTransition(
                    team_id=team_id,
                    from_stage_id=from_id,
                    to_stage_id=to_id,
                )
                for from_id, to_id in normalized
            ])

        await self.session.commit()

        return await self.get_list_transitions(team_id)
