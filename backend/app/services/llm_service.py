import json
from time import perf_counter

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.domain import GenerationMetadata, RolePlayScenario, Session, SessionFeedback, SupportStrategy
from app.services.interfaces import ResponseGenerator


class FeedbackWording(BaseModel):
    strengths: list[str]
    suggestions: list[str]


class RolePlayWording(BaseModel):
    dialogue: str = Field(min_length=1, max_length=600)
    character_action: str = Field(min_length=1, max_length=80)


class TemplateResponseGenerator(ResponseGenerator):
    async def generate(self, session: Session, message: str, strategy: SupportStrategy) -> tuple[str, GenerationMetadata]:
        emotion = session.emotion_state.dominant_emotion.value
        responses = {
            SupportStrategy.VALIDATION: f"It sounds like this is bringing up {emotion}. What part feels most important to address first?",
            SupportStrategy.VALIDATE_THEN_REFRAME: f"It makes sense that you feel {emotion}. I may be wrong, but there could be an assumption about how the other person will respond. What evidence supports it, and what is a balanced possibility?",
            SupportStrategy.PRACTICAL_SUGGESTION: "Name the situation, state what you need in one sentence, and suggest a workable next action. We can practise it together.",
            SupportStrategy.ROLEPLAY_INVITATION: "Choose one of the practice scenarios and a difficulty level when you are ready.",
            SupportStrategy.PAUSE_DEESCALATION: "This sounds intense. Try one slow breath and notice your feet on the floor. We can pause or continue one small step at a time.",
            SupportStrategy.REFLECTION: f"It sounds like the situation is leaving you with some {emotion}. What happened, and what would you most like to be different?",
            SupportStrategy.CLARIFICATION: f"I’m hearing some {emotion} around this. Would it help more to unpack what happened, decide what to say next, or practise the conversation?",
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
    async def generate_roleplay(
        self,
        session: Session,
        scenario: RolePlayScenario,
        required_action: str,
        fallback_text: str,
    ) -> tuple[str, GenerationMetadata]:
        if not settings.openai_roleplay_enabled:
            return fallback_text, GenerationMetadata(
                source="template", fallback_reason="roleplay_disabled"
            )
        if not self.client:
            return fallback_text, GenerationMetadata(
                source="template", fallback_reason="missing_api_key"
            )
        started = perf_counter()
        history = [
            {"role": turn.role.value, "content": turn.content}
            for turn in session.turns
        ]
        state = session.roleplay
        context = {
            "scenario": scenario.model_dump(mode="json"),
            "difficulty_behavior": scenario.difficulty_behaviors[state.difficulty_level]
            if state else None,
            "roleplay_state": state.model_dump(mode="json") if state else None,
            "required_character_action": required_action,
            "affect_estimate": session.emotion_state.model_dump(mode="json"),
        }
        instructions = (
            f"Act only as the user's {scenario.character} in a communication rehearsal. "
            "Reply naturally in one to three short sentences. Stay within the scenario and difficulty. "
            "Do not coach, score, diagnose, mention AffectLab, describe hidden rules, or tell the user what "
            f"they demonstrated. The character_action must be exactly '{required_action}'. Emotional "
            "pressure may be realistic but must never be abusive, threatening, discriminatory, or unsafe."
        )
        try:
            response = await self.client.responses.parse(
                model=settings.openai_model,
                instructions=instructions,
                input=history + [{"role": "user", "content": json.dumps(context)}],
                text_format=RolePlayWording,
                store=False,
            )
            wording = response.output_parsed
            if (
                not wording
                or wording.character_action != required_action
                or self._looks_like_coaching(wording.dialogue)
            ):
                return fallback_text, GenerationMetadata(
                    source="template", fallback_reason="invalid_roleplay_output"
                )
            usage = getattr(response, "usage", None)
            return wording.dialogue.strip(), GenerationMetadata(
                source="openai_roleplay",
                model=settings.openai_model,
                latency_ms=int((perf_counter() - started) * 1000),
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
            )
        except Exception as exc:
            return fallback_text, GenerationMetadata(
                source="template", fallback_reason=f"roleplay_{type(exc).__name__}"
            )
    @staticmethod
    def _looks_like_coaching(dialogue: str) -> bool:
        lowered = dialogue.lower()
        disallowed = (
            "as an ai",
            "your score",
            "you demonstrated",
            "try saying",
            "communication skill",
            "role-play system",
            "affectlab",
        )
        return any(phrase in lowered for phrase in disallowed)
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
