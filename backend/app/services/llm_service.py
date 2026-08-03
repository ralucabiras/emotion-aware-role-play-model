import json
from time import perf_counter

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.models.domain import GenerationMetadata, Session, SessionFeedback, SupportStrategy
from app.services.interfaces import ResponseGenerator


class FeedbackWording(BaseModel):
    strengths: list[str]
    suggestions: list[str]


class TemplateResponseGenerator(ResponseGenerator):
    async def generate(self, session: Session, message: str, strategy: SupportStrategy) -> tuple[str, GenerationMetadata]:
        emotion = session.emotion_state.dominant_emotion.value
        responses = {
            SupportStrategy.VALIDATION: f"It sounds like this is bringing up {emotion}. What part feels most important to address first?",
            SupportStrategy.VALIDATE_THEN_REFRAME: f"It makes sense that you feel {emotion}. I may be wrong, but there could be an assumption about how the other person will respond. What evidence supports it, and what is a balanced possibility?",
            SupportStrategy.PRACTICAL_SUGGESTION: "Name the situation, state what you need in one sentence, and suggest a workable next action. We can practise it together.",
            SupportStrategy.ROLEPLAY_INVITATION: "Choose one of the practice scenarios and a difficulty level when you are ready.",
            SupportStrategy.PAUSE_DEESCALATION: "This sounds intense. Try one slow breath and notice your feet on the floor. We can pause or continue one small step at a time.",
        }
        return responses.get(strategy, "Tell me a little more about what you need from this conversation."), GenerationMetadata()


class OpenAIResponseGenerator(ResponseGenerator):
    def __init__(self, fallback: ResponseGenerator | None = None) -> None:
        self.fallback = fallback or TemplateResponseGenerator()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds) if settings.openai_api_key else None
    async def generate(self, session: Session, message: str, strategy: SupportStrategy) -> tuple[str, GenerationMetadata]:
        if not self.client: return await self._fallback(session, message, strategy, "missing_api_key")
        started = perf_counter()
        history = [{"role": turn.role.value, "content": turn.content} for turn in session.turns]
        instructions = "You are AffectLab, a research social-rehearsal coach. Never diagnose, prescribe medication, claim certainty about emotions, or encourage dependency. Follow the selected support strategy. Be warm, concise, and explicitly tentative about inferred affect."
        context = {"emotion_state": session.emotion_state.model_dump(mode="json"), "strategy": strategy.value, "roleplay": session.roleplay.model_dump(mode="json") if session.roleplay else None}
        try:
            response = await self.client.responses.create(model=settings.openai_model, instructions=instructions, input=history + [{"role":"user", "content": json.dumps({"message": message, "context": context})}])
            text = response.output_text.strip()
            if not text: return await self._fallback(session, message, strategy, "empty_or_refused")
            usage = getattr(response, "usage", None)
            return text, GenerationMetadata(source="openai", model=settings.openai_model, latency_ms=int((perf_counter()-started)*1000), input_tokens=getattr(usage, "input_tokens", None), output_tokens=getattr(usage, "output_tokens", None))
        except Exception as exc:
            return await self._fallback(session, message, strategy, type(exc).__name__)
    async def moderate(self, text: str) -> bool:
        if not self.client: return False
        try:
            result = await self.client.moderations.create(model="omni-moderation-latest", input=text)
            return bool(result.results[0].flagged)
        except Exception: return False
    async def phrase_feedback(self, feedback: SessionFeedback) -> SessionFeedback:
        if not self.client: return feedback
        try:
            response = await self.client.responses.parse(model=settings.openai_model, instructions="Rephrase only the supplied evidence-backed strengths and suggestions. Do not introduce observations, diagnoses, or personality claims.", input=json.dumps(feedback.model_dump(mode="json")), text_format=FeedbackWording)
            wording = response.output_parsed
            if wording:
                feedback.strengths, feedback.suggestions, feedback.generation_source = wording.strengths, wording.suggestions, "openai_from_deterministic_metrics"
        except Exception: pass
        return feedback
    async def _fallback(self, session: Session, message: str, strategy: SupportStrategy, reason: str):
        text, metadata = await self.fallback.generate(session, message, strategy)
        metadata.fallback_reason = reason
        return text, metadata

