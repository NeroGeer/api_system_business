from sqlalchemy import exists, select

from src.database.database import SessionDep
from src.models.model_team import TeamMember, Team
from src.models.model_tasks import Task


class ContextRepository:
    def __init__(self, session: SessionDep):
        self.session = session

    async def get_team(self, team_id: int) -> Team | None:
        return await self.session.scalar(
            select(Team).where(Team.id == team_id)
        )

    async def get_team_role(
            self,
            user_id: int,
            team_id: int) -> bool:

        return await self.session.scalar(
            select(TeamMember.role).where(
                TeamMember.user_id == user_id, TeamMember.team_id == team_id
            )
        )

    async def check_executor(self, task_id: int, team_id: int, user_id: int):
        return self.session.scalar(
            select(
                exists().where(
                    Task.id == task_id,
                    Task.team_id == team_id,
                    Task.executor_user_id == user_id,
                )
            )
        )
