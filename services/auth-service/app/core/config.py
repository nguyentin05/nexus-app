from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True, extra="ignore")

    PROJECT_NAME: str = "Nexus Auth Service"
    VERSION: str = "0.1.0"
    DATABASE_URL: str | None = None
    JWT_SECRET: str = "dev-only-change-me"
    USER_EVENTS_QUEUE_URL: str | None = None
    AWS_REGION: str = "ap-southeast-1"
    TOKEN_TTL_SECONDS: int = 3600
    DB_CONNECT_TIMEOUT_SECONDS: int = 5
    AIOPS_BENCHMARK_ENABLED: bool = False


settings = Settings()
