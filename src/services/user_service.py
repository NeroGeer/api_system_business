from src.exceptions import exceptions as c_exp
from src.logger.logger import logger
from src.core.security import hash_password as hsp
from src.core.security import jwt_token
from src.database.config import settings
from src.models.model_user import User
from src.scheme.schemas_user import CreateUserScheme, UpdateUserScheme


class UserService:
    def __init__(self, repo, context=None):
        self.repo = repo
        self.ctx = context

    async def get_user_id(self, user_id: int):
        result = await self.repo.get(user_id)
        if result is None:
            raise c_exp.UserNotFoundError()
        return result

    async def get_user(self, email: str):
        result = await self.repo.get_by_email(email)
        if result is None:
            raise c_exp.UserNotFoundError()
        return result

    async def login(self, form):
        user = await self.repo.get_by_email(form.username)
        if not user or not hsp.verify_password(
                form.password, user.hashed_password
        ):
            raise c_exp.InvalidCredentialsError()

        access_token = str(
            await jwt_token.create_token({"sub": str(user.id)})
        )
        logger.debug(f"Create access token by user id: {user.id} - {user.email}")

        return access_token, user

    async def create_user(self, data: CreateUserScheme) -> User:
        if await self.repo.get_by_email(data.email) is not None:
            raise c_exp.UserAlreadyExistsError()

        hashed_password = hsp.hash_password(data.password)

        role = await self.repo.get_default_role(
            settings.app.default_role_id
        )

        user = User(
            **data.model_dump(exclude={"password", "roles"}),
            hashed_password=hashed_password,
            roles=[role],
        )

        return await self.repo.create(user)

    async def update_user(self, data: UpdateUserScheme) -> User | None:

        user = self.ctx.current_user
        logger.info(f"Update User_id: {user.id}")
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise c_exp.EmptyDataError()

        if "email" in update_data:
            user.email = update_data["email"]

        if "password" in update_data:
            user.hashed_password = hsp.hash_password(update_data["password"])

        return await self.repo.update(user)

    async def delete_user(self):
        logger.warning(f"Deleting user: id={self.ctx.current_user.id}")
        user = await self.repo.get(self.ctx.current_user.id)
        if not user:
            raise c_exp.UserNotFoundError()
        await self.repo.delete(self.ctx.current_user)
        return {"message": "User deleted successfully"}
