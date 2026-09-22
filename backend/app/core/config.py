from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "AffectLab API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    cors_allowed_origins: str = ""
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    enforce_https: bool = False
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
    study_protocol_version: str = "affectlab-feasibility-v1.0"
    study_participant_target: int = 30
    study_completer_target: int = 24
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
    supported_language: str = "English"
    minimum_participant_age: int = 18
    geographic_scope: str = "Romania"
    emergency_limitations: str = "AffectLab is not monitored, cannot contact emergency services, and does not know your location. In an emergency, call 112 in Romania or your local emergency number."
    offline_demo_mode: bool = False
    offline_demo_email: str = "demo@example.com"
    offline_demo_password: str = "affectlab-offline-demo"
    rate_limit_enabled: bool = False
    rate_limit_auth_per_minute: int = 10
    rate_limit_email_per_hour: int = 5
    rate_limit_transcription_per_minute: int = 10
    rate_limit_model_per_minute: int = 30
    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ROOT / ".env", REPOSITORY_ROOT / "backend" / ".env"),
        extra="ignore",
    )

    @property
    def production(self) -> bool:
        return self.environment.strip().lower() in {"production", "pilot", "staging"}

    @property
    def allowed_origins(self) -> list[str]:
        raw = self.cors_allowed_origins or self.frontend_origin
        return [value.strip().rstrip("/") for value in raw.split(",") if value.strip()]

    @property
    def allowed_hosts(self) -> list[str]:
        return [value.strip() for value in self.trusted_hosts.split(",") if value.strip()]

    @model_validator(mode="after")
    def validate_deployment_security(self):
        if not self.production:
            return self
        if self.offline_demo_mode:
            raise ValueError("OFFLINE_DEMO_MODE cannot be enabled outside local development")
        weak = {
            "development-only-change-me-at-least-32-bytes",
            "replace-with-a-long-random-secret",
            "changeme",
            "secret",
        }
        if len(self.jwt_secret.encode()) < 32 or self.jwt_secret.strip().lower() in weak:
            raise ValueError("Production JWT_SECRET must be a unique random value of at least 32 bytes")
        if not self.allowed_origins or any(
            origin == "*" or not origin.startswith("https://") for origin in self.allowed_origins
        ):
            raise ValueError("Production CORS_ALLOWED_ORIGINS must contain only explicit HTTPS origins")
        if not self.allowed_hosts or "*" in self.allowed_hosts:
            raise ValueError("Production TRUSTED_HOSTS must be an explicit host list")
        if not self.enforce_https:
            raise ValueError("ENFORCE_HTTPS must be true in production")
        if not self.rate_limit_enabled:
            raise ValueError("RATE_LIMIT_ENABLED must be true in production")
        return self


settings = Settings()
