from app.core.config import settings
from app.repositories.memory import MemoryRepository
from app.repositories.mongo import MongoRepository
from app.services.auth_service import AuthService
from app.services.conversation_service import ConversationService

repository = MongoRepository(settings.mongodb_uri, settings.mongodb_database) if settings.persistence_backend == "mongo" else MemoryRepository()
auth_service = AuthService(repository)
conversation_service = ConversationService(repository)


def get_repository(): return repository
def get_auth_service(): return auth_service
def get_conversation_service(): return conversation_service

