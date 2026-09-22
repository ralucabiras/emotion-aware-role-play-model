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
    study_record_retention_days: int = 365
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6"
    openai_timeout_seconds: float = 20
    openai_roleplay_enabled: bool = True
    transcription_enabled: bool = True
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
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
    study_consent_version: str = "2026-09-21-v1"
    study_retention_period: str = "Minimized pseudonymous study records are retained for 365 days after their most recent study activity, then automatically deleted. Active conversation sessions expire separately after 30 days of inactivity."
    study_researcher_name: str = "Raluca Biras"
    study_researcher_email: str = "calmai.etherapy@gmail.com"
    study_supervisor_name: str = "To be confirmed"
    study_supervisor_email: str = "To be confirmed"
    study_institution: str = "To be confirmed"
    onboarding_version: str = "2026-08-v1"
    researcher_emails: str = ""
    pilot_access_code: str = ""
    pilot_study_label: str = "AffectLab pilot study"
    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ROOT / ".env", REPOSITORY_ROOT / "backend" / ".env"),
        extra="ignore",
    )


settings = Settings()
