from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from src.database.database import SessionDep
from src.models.model_team import Team, TeamMember


class TeamRepository:
    def __init__(self, session: SessionDep):
        self.session = session

    async def get(self, team_id: int) -> Team | None:
        return await self.session.scalar(
            select(Team).where(Team.id == team_id)
        )

    async def get_team_by_invite_code(self, code: str) -> Team | None:
        result = await self.session.execute(
            select(Team).where(Team.invite_code == code)
        )
        return result.scalar()

    async def get_member(self, team_id: int, user_id: int) -> TeamMember | None:
        return await self.session.scalar(
            select(TeamMember).where(
                TeamMember.user_id == user_id, TeamMember.team_id == team_id
            )
        )

    async def get_members(self, team_id: int) -> Team | None:
        stmt = (
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        return await self.session.scalar(stmt)

    async def create(self, team: Team) -> Team | None:
        if (
            await self.session.execute(
                select(Team).where(
                    or_(
                        Team.name == team.name,
                        Team.invite_code == team.invite_code
                    )
                )
            )
        ).scalar_one_or_none():
            return None

        self.session.add(team)
        await self.session.commit()
        await self.session.refresh(team)
        return team

    async def add_member(self, member: TeamMember):
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)

        return member

    async def update_role(self, member: TeamMember):
        await self.session.commit()
        await self.session.refresh(member)

    async def delete_member(self, member: TeamMember):
        await self.session.delete(member)
        await self.session.commit()
