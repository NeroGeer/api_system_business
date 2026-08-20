from datetime import date
from typing import List

from sqlalchemy import select

from src.database.database import SessionDep
from src.models.model_meeting import Meeting
from src.models.model_tasks import Task
from src.models.model_team import TeamMember


class CalendarRepository:
    def __init__(self, session: SessionDep):
        self.session = session

    async def get_teams_ids(self, user_id: int):
        return (await self.session.scalars(
                select(TeamMember.team_id).where(TeamMember.user_id == user_id)
        )
                ).all()

    async def get_meetings(
            self, teams_ids: List[int], start_dt: date, end_dt: date
    ):
        meetings_stmt = select(Meeting).where(
            Meeting.team_id.in_(teams_ids),
            Meeting.start_time <= end_dt,
            Meeting.end_time >= start_dt,
        )
        return (await self.session.scalars(meetings_stmt)).all()

    async def get_tasks(
            self, teams_ids: List[int], start_dt: date, end_dt: date
    ):
        tasks_stmt = select(Task).where(
            Task.team_id.in_(teams_ids),
            Task.deadline >= start_dt,
            Task.deadline < end_dt,
            Task.deleted_at.is_(None),
        )
        return (await self.session.scalars(tasks_stmt)).all()
