from app.models.domain import Session, SupportStrategy
from app.services.interfaces import ResponseGenerator


class TemplateResponseGenerator(ResponseGenerator):
    """Offline baseline implementing the future LLM boundary."""

    async def generate(self, session: Session, message: str, strategy: SupportStrategy) -> str:
        emotion = session.emotion_state.dominant_emotion.value
        responses = {
            SupportStrategy.VALIDATION: (
                f"It sounds like this is bringing up {emotion}. That reaction makes sense in a difficult "
                "social situation. What part feels most important to address first?"
            ),
            SupportStrategy.VALIDATE_THEN_REFRAME: (
                f"It makes sense that you feel {emotion}. I may be wrong, but there could be an assumption "
                "about how the other person will respond. What evidence supports that outcome, and what is "
                "a more balanced possibility?"
            ),
            SupportStrategy.PRACTICAL_SUGGESTION: (
                "Let’s make the next step concrete: name the situation, state what you need in one sentence, "
                "and suggest a workable next action. We can draft or practise that sentence together."
            ),
            SupportStrategy.ROLEPLAY_INVITATION: (
                "We can practise this as a role-play. Start the workload scenario below, or tell me which "
                "person and conversation you want to rehearse."
            ),
            SupportStrategy.PAUSE_DEESCALATION: (
                "This sounds intense. Before continuing, try one slow breath and notice your feet on the "
                "floor. We can pause, or take the conversation one small step at a time."
            ),
        }
        return responses.get(strategy, "Tell me a little more about what you need from this conversation.")

