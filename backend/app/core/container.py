from app.core.config import settings
from app.repositories.memory import MemoryRepository
from app.repositories.mongo import MongoRepository
from app.services.auth_service import AuthService
from app.services.conversation_service import ConversationService
from app.services.email_service import EmailService
from app.services.multimodal_service import MultimodalAffectService

repository = MongoRepository(settings.mongodb_uri, settings.mongodb_database) if settings.persistence_backend == "mongo" else MemoryRepository()
email_service = EmailService()
auth_service = AuthService(repository, email_service)
conversation_service = ConversationService(repository)
multimodal_service = MultimodalAffectService(
    settings.multimodal_inference_enabled,
    settings.multimodal_text_model_dir,
    settings.multimodal_audio_model_dir,
    settings.multimodal_config_path,
    settings.multimodal_device,
    settings.multimodal_max_audio_bytes,
)


def get_repository(): return repository
def get_auth_service(): return auth_service
def get_conversation_service(): return conversation_service
def get_multimodal_service(): return multimodal_service
