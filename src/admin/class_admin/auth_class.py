from fastapi import Request, Response, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqladmin.authentication import AuthenticationBackend

from src.core.security import cookie
from src.core.security import hash_password as hsp
from src.core.security import jwt_token
from src.core.security.rbac import has_permission
from src.database.database import async_session, settings
from src.logger.logger import logger
from src.core.security.dependencies import get_user_by_id

from src.repositories.refresh_token_repository import RefreshTokenRepo
from src.repositories.user_repository import UserRepository
from src.services.refresh_token_service import RefreshTokenService
from src.services.user_service import UserService
from src.core.context.base_context import build_service


class AdminAuth(AuthenticationBackend):
    def __init__(self):
        super().__init__(secret_key=settings.jwt.secret_key)

    async def login(self, request: Request) -> bool:
        form = await request.form()

        email = form.get("username")
        password = form.get("password")

        logger.info(f"[ADMIN LOGIN] attempt email={email}")

        if not email or not password:
            logger.warning("[ADMIN LOGIN] missing credentials")
            return False

        async with async_session() as session:
            serv_fact = build_service(repository_cls=UserRepository, service_cls=UserService, session=session)
            user = await serv_fact.get_user(email)

            if not user or not hsp.verify_password(password, user.hashed_password):
                logger.warning(f"[ADMIN LOGIN] user not found email={email}")

                return False

            if not user.is_active or not has_permission(user, "admin.panel.access"):
                logger.warning(f"[ADMIN LOGIN] inactive user_id={user.id}"
                               f" no permission user_id={user.id}")
                return False

            logger.info(f"[ADMIN LOGIN] success user_id={user.id}")

            request.session["user_id"] = user.id
            request.session["user_email"] = user.email

        return True

    async def logout(self, request: Request) -> bool:

        logger.info("[ADMIN LOGOUT] attempt")

        request.session.clear()

        logger.info("[ADMIN LOGOUT] success")

        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("user_id")

        if not user_id:
            logger.debug("[ADMIN AUTH] no user_id")
            return False

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            logger.warning(
                f"[ADMIN AUTH] invalid user_id={user_id}"
            )
            return False

        async with async_session() as session:
            user = await get_user_by_id(session=session, user_id=user_id)

        if not user or not has_permission(user, "admin.panel.access"):
            logger.warning(f"[ADMIN AUTH] user not found id={user_id} "
                           f"no permission user_id={user_id}")
            return False

        logger.info(f"[ADMIN AUTH] success user_id={user.id}")

        return True
