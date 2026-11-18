from typing import Annotated

from fastapi import APIRouter, Depends

from src.repositories.task_stage_repository import StageRepository
from src.services.task_stage_services import StageManagementService
from src.scheme.schemas_task_stage import (
    StageSchema,
    StageSchemaRead,
    StageCreate,
    UpdateStageRename,
    ConfigRead,
    TransitionReplaceRequest,
)
from src.core.context.base_context import (
    BaseContext,
    build_context_with_filters,
    build_service)

route_stage = APIRouter(prefix="/api/teams/{team_id}/stage", tags=["Stage"])


@route_stage.get("", status_code=200, response_model=StageSchema)
async def get_all_stage(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
):
    serv_fact = build_service(repository_cls=StageRepository,
                              service_cls=StageManagementService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.get_stages_by_team_id()


@route_stage.get("/{stage_id}", status_code=200, response_model=StageSchema)
async def get_stage_by_id(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
):
    serv_fact = build_service(repository_cls=StageRepository,
                              service_cls=StageManagementService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.get_stages_id_by_team_id()


@route_stage.post("/create-stage", status_code=201, response_model=StageSchemaRead)
async def create_new_stage(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
        data: StageCreate,
):
    serv_fact = build_service(repository_cls=StageRepository,
                              service_cls=StageManagementService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.create_middle_stage(data=data)


@route_stage.patch("/update-stage/{stage_id}", status_code=200, response_model=StageSchemaRead)
async def update_task_by_id(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
        data: UpdateStageRename,
):
    serv_fact = build_service(repository_cls=StageRepository,
                              service_cls=StageManagementService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.update_name_stage(data=data)


@route_stage.delete("/delete-stage/{stage_id}", status_code=204)
async def delete_stage_by_id(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
):
    serv_fact = build_service(repository_cls=StageRepository,
                              service_cls=StageManagementService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.delete_middle_stage()


@route_stage.get("/stage/config", response_model=ConfigRead)
async def get_stage_config(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
):
    serv_fact = build_service(repository_cls=StageRepository,
                              service_cls=StageManagementService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.get_config()


@route_stage.put("/stage/transitions", response_model=ConfigRead)
async def replace_transitions_task_stage(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
        data: TransitionReplaceRequest,
):
    serv_fact = build_service(repository_cls=StageRepository,
                              service_cls=StageManagementService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.replace_transitions(transitions=data)
