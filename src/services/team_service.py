from src.logger.logger import logger
from src.models.model_team import TeamMember, Team
from src.scheme.schemas_admin import AdminTeamCrateSchema
from src.scheme.schemas_team import TeamRole, AddTeamMemberSchema, UpdateTeamMemberRoleSchema
from src.exceptions import exceptions as c_exp


class TeamService:
    def __init__(self, repo, context=None):
        self.repo = repo
        self.ctx = context

    async def get_team(self):
        """
        Author: NeroGeer
        GitHub: https://github.com/NeroGeer
        License: MIT

        Returns:
            Team: Team info
        """

        team_id = self.ctx.scope.team_id

        await self.ctx.require_admin_or_team_role_or_executor(team_role={TeamRole.manager, TeamRole.employee})
        result = await self.repo.get(team_id=team_id)
        if not result:
            logger.warning(f"Team no found with ID: {team_id}")
            raise c_exp.TeamNotFoundError()
        return result

    async def get_team_code(self):
        invite_code = self.ctx.filters.invite_code

        team = await self.repo.get_team_by_invite_code(invite_code)

        if not team:
            raise c_exp.TeamNotFoundError()

        return team

    async def get_members_team(self):
        """
        Returns all members of a team.

        Returns:
            list[TeamMember]: team members with loaded user relation
        """

        team_id = self.ctx.scope.team_id

        await self.ctx.require_admin_or_team_role_or_executor(team_role={TeamRole.manager, TeamRole.employee})
        result = await self.repo.get_members(team_id=team_id)
        if not result:
            logger.warning(f"Team no found with ID: {team_id}")
            raise c_exp.TeamNotFoundError()
        return result

    async def create_team(self, data: AdminTeamCrateSchema) -> Team:
        """
        Creates a new team in the system.
        Returns:
            Team: Created team instance.

        Raises:
            IntegrityError: If team name or invite code violates uniqueness constraints.
        """
        logger.info(f"Creating new team: {data.name}")
        result = await self.repo.create(Team(**data.model_dump()))
        if result is None:
            raise c_exp.TeamCreateError()
        return result

    async def join_team(self, team: Team):
        user = self.ctx.current_user

        existing = await self.repo.get_member(user_id=user.id, team_id=team.id)

        if existing:
            logger.warning(
                f"User already in team: user_id={user.id}, team_id={team.id}"
            )
            raise c_exp.TeamMemberAlreadyExistsError()

        member = TeamMember(
                user_id=user.id,
                team_id=team.id,
                role=TeamRole.employee
            )

        return await self.repo.add_member(member=member)

    async def add_members_team(
            self, data: AddTeamMemberSchema
    ):
        """
        Adds a user to a team.

        Rules:
            - user must not already be in team
            - only admin can assign roles other than employee
            - default role is employee for non-admins
        """
        team_id = self.ctx.scope.team_id

        await self.ctx.require_admin_or_team_role_or_executor()

        logger.debug(
            f"Adding member: team_id={team_id}, user_id={data.user_id}"
        )

        existing = await self.repo.get_member(user_id=data.user_id, team_id=team_id)

        if existing:
            logger.warning(
                f"User already in team: user_id={data.user_id}, team_id={team_id}"
            )
            return c_exp.TeamMemberAlreadyExistsError()

        member = TeamMember(user_id=data.user_id, team_id=team_id, role=TeamRole.employee)

        return await self.repo.add_member(member=member)

    async def update_member_role(self, data: UpdateTeamMemberRoleSchema):
        """
        Updates a team member role.

        Returns:
            TeamMember: Updated member entity

        Raises:
            HTTPException: If member is not found
        """

        team_id = self.ctx.scope.team_id
        user_id = self.ctx.scope.user_id

        logger.debug(
            f"Updating team member role: team_id={team_id}, user_id={user_id}, new_role={data.role}"
        )

        member = await self.repo.get_member(team_id=team_id, user_id=user_id)

        if member is None:
            logger.warning(
                f"Team member not found for role update: team_id={team_id}, user_id={user_id}"
            )
            raise c_exp.TeamMemberNotFoundError()

        member.role = data.role
        self.repo.update_role(member)
        return member

    async def delete_team_member(self):
        """
        Removes a user from a team.

        Rules:
            - user cannot remove themselves
            - member must exist in team

        Returns:
            dict: operation result implicitly via HTTP response
        """
        team_id = self.ctx.scope.team_id
        user_id = self.ctx.scope.user_id
        current_user = self.ctx.current_user.id

        if current_user == user_id:
            logger.warning(
                f"Self-removal attempt blocked: user_id={user_id}, "
                f"team_id={team_id}"
            )
            raise c_exp.SelfRemovalError()

        await self.ctx.require_admin_or_team_role_or_executor()

        member = await self.repo.get_member(team_id=team_id, user_id=user_id)

        if member is None:
            raise c_exp.TeamMemberNotFoundError()

        await self.repo.delete_member(member=member)

        logger.info(f"Team member deleted: team_id={team_id}, user_id={user_id}")
