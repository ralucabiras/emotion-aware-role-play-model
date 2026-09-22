from app.core.config import Settings


def test_offline_demo_has_no_external_service_dependency():
    demo = Settings(
        _env_file=None,
        environment="development",
        persistence_backend="memory",
        offline_demo_mode=True,
        openai_api_key=None,
        openai_roleplay_enabled=False,
        transcription_enabled=False,
        multimodal_inference_enabled=False,
        smtp_host="",
        smtp_username="",
        smtp_password="",
        smtp_sender="",
    )
    assert demo.offline_demo_mode
    assert demo.persistence_backend == "memory"
    assert not demo.openai_api_key and not demo.transcription_enabled and not demo.multimodal_inference_enabled


def test_production_rejects_offline_demo_mode():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="OFFLINE_DEMO_MODE"):
        Settings(
            _env_file=None,
            environment="production",
            offline_demo_mode=True,
            jwt_secret="a-unique-production-secret-with-more-than-32-bytes",
            cors_allowed_origins="https://pilot.example.org",
            trusted_hosts="pilot.example.org",
            enforce_https=True,
            rate_limit_enabled=True,
        )
