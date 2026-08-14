# import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqladmin import Admin

from src.admin.admin import setup_admin
from src.admin.class_admin.auth_class import AdminAuth
from src.database.database import engine, redis_client
from src.database.insert_perm import insert_rbac_data
from src.models.model_base import Base
from src.route.root_calendar import route_calendar
from src.route.route_admin import route_admin
from src.route.route_comment import route_comment
from src.route.route_jwt import route_jwt
from src.route.route_meeting import route_meeting
from src.route.route_task import route_task
from src.route.route_team import route_team
from src.route.route_user import route_user
from src.exceptions.exceptions import AppError
from src.database.config import settings


# from starlette.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Asynchronous lifespan context manager for the FastAPI application.

    This function is executed when the application starts and stops.
    It ensures that the database schema is freshly created and populated
    with initial data at startup, and that resources are cleaned up at shutdown.

    Workflow:
    - On startup:
        1. Open a connection to the database engine.
        2. Drop all existing tables (if any).
        3. Recreate all tables defined in SQLAlchemy Base metadata.
        4. Insert initial data into the database.
    - On shutdown:
        - Dispose of the database engine, closing all connections.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Allows FastAPI to run while the lifespan context is active.
    """
    if settings.app.debug_mode_drop_base:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            await insert_rbac_data(conn)

    try:
        await redis_client.ping()
    except Exception as e:
        print(e)

    yield

    await engine.dispose()
    await redis_client.close()


app = FastAPI(lifespan=lifespan,
              title="API System Business",
              version="1.0.0",
              contact={
                  "name": "NeroGeer",
                  "url": "https://github.com/NeroGeer",
                  "email": "nerogeerjob@gmail.com",
              },
              )

admin = Admin(app=app, engine=engine, authentication_backend=AdminAuth())
setup_admin(admin)

app.include_router(route_jwt)
app.include_router(route_admin)
app.include_router(route_user)
app.include_router(route_team)
app.include_router(route_meeting)
app.include_router(route_task)
app.include_router(route_comment)
app.include_router(route_calendar)


@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    raise HTTPException(
        status_code=exc.status_code,
        detail=exc.detail
    )

# app.mount("/images", StaticFiles(directory="/usr/share/nginx/static/images"), name="images")


# if __name__ == '__main__':
#     uvicorn.run('main:app', host='127.0.0.1', port=8000)
