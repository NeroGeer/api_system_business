from sqlalchemy import select, exists, and_, func
from datetime import datetime, UTC, date

from src.models.model_tasks import Task
from src.database.database import SessionDep
from src.models.model_team import TeamMember


class TaskRepository:
    def __init__(self, session: SessionDep):
        self.session = session

    async def validate_team(
            self,
            user_id: int,
            team_id: int,
    ) -> bool:

        return await self.session.scalar(select(
            exists().where(TeamMember.user_id == user_id, TeamMember.team_id == team_id)
        ))

    async def get(
            self,
            team_id: int,
            executor_user_id: int | None = None,
            start_dt: date | None = None,
            end_dt: date | None = None,
    ):
        stmt = select(Task).where(Task.team_id == team_id, Task.deleted_at.is_(None))

        if start_dt is not None and end_dt is not None:
            stmt = stmt.where(and_(Task.deadline >= start_dt, Task.deadline <= end_dt))

        if executor_user_id is not None:
            stmt = stmt.where(Task.executor_user_id == executor_user_id)

        result = await self.session.execute(stmt)

        return result.scalars().all()

    async def get_task_id(self, task_id: int, team_id: int) -> Task | None:

        return await self.session.scalar(
            select(Task).where(
                Task.id == task_id, Task.team_id == team_id, Task.deleted_at.is_(None),
            )
        )

    async def get_avg_grade(
            self,
            team_id: int,
            user_id: int,
            start_dt: date,
            end_dt: date
    ):

        avg_grade = await self.session.scalar(
            select(func.avg(Task.grade)).where(
                Task.team_id == team_id,
                Task.executor_user_id == user_id,
                Task.close_date >= start_dt,
                Task.close_date < end_dt,
                Task.deleted_at.is_(None),
            ))

        grade = avg_grade or 0.0
        return {"grade": round(grade, 1)}

    async def create(
            self, data: Task
    ):

        self.session.add(data)
        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def update(
            self,
            task: Task,
    ):
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        task.deleted_at = datetime.now(UTC)
        await self.session.commit()
