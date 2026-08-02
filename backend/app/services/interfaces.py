from abc import ABC, abstractmethod

from app.models.domain import CognitiveAssessment, EmotionState, Session, SupportStrategy


class EmotionAnalyzer(ABC):
    @abstractmethod
    def analyze(self, text: str) -> EmotionState: ...


class StrategySelector(ABC):
    @abstractmethod
    def select(self, state: EmotionState, assessment: CognitiveAssessment) -> SupportStrategy: ...


class ResponseGenerator(ABC):
    @abstractmethod
    async def generate(self, session: Session, message: str, strategy: SupportStrategy) -> str: ...

