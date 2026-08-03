from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AffectLab API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    persistence_backend: str = "memory"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "affectlab"
    jwt_secret: str = "development-only-change-me-at-least-32-bytes"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    session_retention_days: int = 30
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6"
    openai_timeout_seconds: float = 20
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
