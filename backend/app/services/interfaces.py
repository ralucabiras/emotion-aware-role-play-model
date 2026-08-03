from abc import ABC, abstractmethod

from app.models.domain import CognitiveAssessment, EmotionState, GenerationMetadata, Session, SupportStrategy


class EmotionAnalyzer(ABC):
    @abstractmethod
    def analyze(self, text: str) -> EmotionState: ...


class StrategySelector(ABC):
    @abstractmethod
    def select(self, state: EmotionState, assessment: CognitiveAssessment) -> SupportStrategy: ...


class CognitiveAnalyzer(ABC):
    @abstractmethod
    def analyze(self, text: str, crisis_detected: bool = False) -> CognitiveAssessment: ...


class ResponseGenerator(ABC):
    @abstractmethod
    async def generate(self, session: Session, message: str, strategy: SupportStrategy) -> tuple[str, GenerationMetadata]: ...
