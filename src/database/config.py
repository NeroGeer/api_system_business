import os
from typing import Dict

from pydantic import BaseModel, Field, PostgresDsn, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """
    PostgreSQL database configuration settings.

    This class defines all parameters required to configure SQLAlchemy
    database engine and connection pool behavior.

    Attributes:
        url (PostgresDsn):
            PostgreSQL DSN connection string.
            Example: postgresql+psycopg2://user:password@localhost:5432/db

        echo (bool):
            Enables SQL query logging.

        echo_pool (bool):
            Enables connection pool logging.

        pool_size (int):
            Number of persistent connections in the pool.

        max_overflow (int):
            Maximum additional connections beyond pool_size.

        naming_convention (Dict[str, str]):
            SQLAlchemy constraint naming rules for consistent schema generation.
    """

    url: PostgresDsn
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 50
    max_overflow: int = 10
    naming_convention: Dict[str, str] = Field(
        default_factory=lambda: {
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class JWTConfig(BaseModel):
    """
    JWT authentication configuration.

    Attributes:
        secret_key (str): Secret key used to sign tokens.
        algorithm (str): JWT signing algorithm (e.g. HS256).
        access_expire_min (int): Access token lifetime in minutes.
        refresh_expire_days (int): Refresh token lifetime in days.
    """

    secret_key: str
    algorithm: str
    access_expire_min: int
    refresh_expire_days: int


class RedisConfig(BaseModel):
    """
    Redis configuration settings.

    Attributes:
        url (str | None): Redis connection URL.
        port (int | None): Redis port (optional if URL is used).
    """

    url: str | None = None
    port: int | None = None


class AppConfig(BaseModel):
    """
    General application configuration.

    Attributes:
        base_user_role_name (str): Default role name for new users.
        default_role_id (int): Default role ID.
        log_level (str): Application logging level.

        static_folder (str): Base folder for static files.

        allowed_extensions (set[str]): Allowed file upload extensions.
    """
    debug_mode_drop_base: bool
    base_user_role_name: str
    default_role_id: int

    log_level: str = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v):
        return v.upper()

    static_folder: str = "/usr/share/nginx/static"

    @property
    def images_folder(self) -> str:
        return os.path.join(self.static_folder, "images")

    allowed_extensions: set[str] = {"png", "jpg", "jpeg", "gif"}


class Settings(BaseSettings):
    """
    Global application settings loaded from environment variables.

    Environment configuration:
        - Reads from `.env` and `.test.env` files located in `src/`
        - Uses prefix: APP_CONFIG__
        - Supports nested structures using `__` delimiter
        - Case-insensitive keys

    Example:
        APP_CONFIG__DB__URL=postgresql+psycopg2://...
        APP_CONFIG__JWT__SECRET_KEY=...
    """

    model_config = SettingsConfigDict(
        env_file=("src/.env", "src/.test.env"),
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
    )
    db: DatabaseConfig
    redis: RedisConfig = RedisConfig()
    jwt: JWTConfig
    app: AppConfig


try:
    settings = Settings()
except ValidationError as e:
    raise RuntimeError(f"Invalid configuration: {e}")
