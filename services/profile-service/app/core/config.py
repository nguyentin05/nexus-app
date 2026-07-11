from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True, extra="ignore")

    PROJECT_NAME: str = "Nexus Profile Service"
    VERSION: str = "0.1.0"
    DATABASE_URL: str | None = None
    JWT_SECRET: str = "dev-only-change-me"
    USER_EVENTS_QUEUE_URL: str | None = None
    AWS_REGION: str = "ap-southeast-1"
    DB_CONNECT_TIMEOUT_SECONDS: int = 5
    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None
    CLOUDINARY_FOLDER: str = "nexus/avatars"


settings = Settings()
