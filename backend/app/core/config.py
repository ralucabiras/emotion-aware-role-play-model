from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


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
    transcription_enabled: bool = True
    openai_transcription_model: str = "gpt-transcribe"
    transcription_timeout_seconds: float = 30
    multimodal_inference_enabled: bool = False
    multimodal_text_model_dir: str = ""
    multimodal_audio_model_dir: str = ""
    multimodal_config_path: str = "../configs/iemocap_final_multimodal.json"
    multimodal_device: str = "auto"
    multimodal_max_audio_bytes: int = 5_000_000
    multimodal_low_confidence_threshold: float = 0.55
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_sender: str = ""
    smtp_timeout_seconds: float = 20
    email_verification_hours: int = 24
    password_reset_minutes: int = 30
    research_consent_version: str = "2026-08-18-v1"
    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ROOT / ".env", REPOSITORY_ROOT / "backend" / ".env"),
        extra="ignore",
    )


settings = Settings()
