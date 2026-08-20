from typing import Annotated, List

from fastapi import APIRouter, Depends

from src.repositories.task_repository import TaskRepository
from src.services.task_service import TaskService
from src.scheme.schemas_task import (
    OutAVGGradeTaskSchema,
    TaskCreateSchema,
    TaskSchema,
    UpdateTaskSchema,
    UpdateTaskStatusSchema, UpdateTaskExecutorSchema,
)
from src.core.context.base_context import (
    BaseContext,
    build_context_with_filters,
    TaskFilter,
    DateFilter,
    build_service)

route_task = APIRouter(prefix="/api/teams/{team_id}/tasks", tags=["Tasks"])


@route_task.get("", status_code=200, response_model=List[TaskSchema])
async def get_all_task(
        ctx: Annotated[
                BaseContext[TaskFilter],
                Depends(build_context_with_filters(TaskFilter))
            ],
):
    serv_fact = build_service(repository_cls=TaskRepository,
                              service_cls=TaskService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.get_tasks_or_task_by_id()


@route_task.get("/avg_grade", status_code=200, response_model=OutAVGGradeTaskSchema)
async def get_avg_task_grade_by_user_id(
        ctx: Annotated[
            BaseContext[DateFilter],
            Depends(build_context_with_filters(DateFilter))
        ],
):
    serv_fact = build_service(repository_cls=TaskRepository,
                              service_cls=TaskService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.get_avg_grade_task_make_date_range()


@route_task.get("/{task_id}", status_code=200, response_model=TaskSchema)
async def get_task_by_id(
        ctx: Annotated[
            BaseContext[TaskFilter],
            Depends(build_context_with_filters(TaskFilter))
        ],
):
    serv_fact = build_service(repository_cls=TaskRepository,
                              service_cls=TaskService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.get_tasks_or_task_by_id()


@route_task.post("/create-task", status_code=201, response_model=TaskSchema)
async def create_new_task(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
        data: TaskCreateSchema,
):
    serv_fact = build_service(repository_cls=TaskRepository,
                              service_cls=TaskService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.create_task(data=data)


@route_task.patch("/update-task/{task_id}", status_code=200, response_model=TaskSchema)
async def update_task_by_id(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
        data: UpdateTaskSchema,
):
    serv_fact = build_service(repository_cls=TaskRepository,
                              service_cls=TaskService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.update_task(data=data)


@route_task.patch(
    "/update-task/{task_id}/status", status_code=200, response_model=TaskSchema
)
async def update_task_by_id_status(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
        data: UpdateTaskStatusSchema,
):
    serv_fact = build_service(repository_cls=TaskRepository,
                              service_cls=TaskService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.update_task_status(data=data)


@route_task.patch(
    "/update-task/{task_id}/executor", status_code=200, response_model=TaskSchema
)
async def update_task_by_id_executor(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
        data: UpdateTaskExecutorSchema,
):
    serv_fact = build_service(repository_cls=TaskRepository,
                              service_cls=TaskService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.update_task_executor(data=data)


@route_task.delete("/delete-task/{task_id}", status_code=204)
async def delete_task_by_id(
        ctx: Annotated[
            BaseContext,
            Depends(build_context_with_filters())
        ],
):
    serv_fact = build_service(repository_cls=TaskRepository,
                              service_cls=TaskService,
                              session=ctx.session,
                              ctx=ctx)
    return await serv_fact.delete_task()
