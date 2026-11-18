from typing import Annotated

from fastapi import APIRouter, Depends

from src.repositories.team_repository import TeamRepository
from src.repositories.user_repository import UserRepository
from src.services.user_service import UserService
from src.services.team_service import TeamService
from src.scheme.schemas_team import (
    AddTeamMemberSchema,
    TeamMemberResponseSchema,
    TeamResponseSchema,
    UpdateTeamMemberRoleSchema,
)
from src.core.context.base_context import BaseContext, build_context_with_filters, build_service


route_team = APIRouter(
    prefix="/api/teams",
    tags=["Teams"],
)


@route_team.get(
    "/{team_id}/", status_code=200, response_model=TeamResponseSchema
)
async def get_team(
        ctx: Annotated[BaseContext, Depends(build_context_with_filters())],
):
    serv_fact = build_service(repository_cls=TeamRepository, service_cls=TeamService,
                              session=ctx.session, ctx=ctx)
    result = await serv_fact.get_team()
    return result


@route_team.get(
    "/{team_id}/members", status_code=200, response_model=TeamResponseSchema
)
async def get_member_team(
        ctx: Annotated[BaseContext, Depends(build_context_with_filters())],
):
    serv_fact = build_service(repository_cls=TeamRepository, service_cls=TeamService,
                              session=ctx.session, ctx=ctx)

    result = await serv_fact.get_members_team()
    return result


@route_team.post(
    "/{team_id}/members", status_code=201, response_model=TeamMemberResponseSchema
)
async def add_member_team(
        ctx: Annotated[BaseContext, Depends(build_context_with_filters())],
        data: AddTeamMemberSchema,
):
    serv_fact = build_service(service_cls=UserService, repository_cls=UserRepository, session=ctx.session)
    await serv_fact.get_user_id(data.user_id)

    serv_fact = build_service(repository_cls=TeamRepository, service_cls=TeamService,
                              session=ctx.session, ctx=ctx)
    result = await serv_fact.add_members_team(data=data)
    return result


@route_team.patch(
    "/{team_id}/members/{user_id}",
    status_code=200,
    response_model=TeamMemberResponseSchema,
)
async def update_member_role_in_team_by_id(
        ctx: Annotated[BaseContext, Depends(build_context_with_filters())],
        data: UpdateTeamMemberRoleSchema,
):
    ctx.require_admin()

    serv_fact = build_service(service_cls=UserService, repository_cls=UserRepository, session=ctx.session)
    await serv_fact.get_user_id(data.user_id)

    serv_fact = build_service(repository_cls=TeamRepository, service_cls=TeamService,
                              session=ctx.session, ctx=ctx)
    result = await serv_fact.update_member_role(data=data)
    return result


@route_team.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_member(
        ctx: Annotated[BaseContext, Depends(build_context_with_filters())],
):
    serv_fact = build_service(repository_cls=TeamRepository, service_cls=TeamService,
                              session=ctx.session, ctx=ctx)
    await serv_fact.delete_team_member()
    return {"status": "deleted"}
