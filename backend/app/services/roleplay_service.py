import re

from app.models.domain import (
    Difficulty,
    EmotionState,
    FeedbackMetric,
    RolePlayScenario,
    RolePlayState,
    RolePlayStatus,
    SessionFeedback,
    TurnEvidence,
    utcnow,
)

LEVELS = {Difficulty.BEGINNER: (0.25, 0.8), Difficulty.INTERMEDIATE: (0.5, 0.6), Difficulty.DIFFICULT: (0.75, 0.4)}
SCENARIOS = {
    "workload": RolePlayScenario(id="workload", title="Workload conversation", character="manager", user_objective="Explain the overload and ask the manager to prioritise work.", opening_line="Thanks for meeting with me. What did you want to discuss?", expected_skills=["clear request", "specific evidence", "assertiveness", "collaborative tone"], difficulty_behaviors={Difficulty.BEGINNER:"Supportive and curious", Difficulty.INTERMEDIATE:"Requests evidence", Difficulty.DIFFICULT:"Pushes back on priorities"}, success_conditions=["concrete_request", "specific_detail"]),
    "boundary": RolePlayScenario(id="boundary", title="Personal boundary", character="friend", user_objective="Decline a request clearly without excessive apologising.", opening_line="Could you please take care of this for me again? I really need you.", expected_skills=["clear refusal", "boundary maintenance", "respectful tone"], difficulty_behaviors={Difficulty.BEGINNER:"Accepts a clear no", Difficulty.INTERMEDIATE:"Asks once more", Difficulty.DIFFICULT:"Applies emotional pressure"}, success_conditions=["concrete_request", "maintained_boundary"]),
    "relationship": RolePlayScenario(id="relationship", title="Relationship need", character="partner", user_objective="Express an emotional need without blaming the other person.", opening_line="You said you wanted to talk. What is going on?", expected_skills=["I-statements", "specific need", "non-blaming language"], difficulty_behaviors={Difficulty.BEGINNER:"Listens openly", Difficulty.INTERMEDIATE:"Becomes mildly defensive", Difficulty.DIFFICULT:"Challenges the description"}, success_conditions=["concrete_request", "specific_detail", "no_blame"]),
}


def observe(turn: int, text: str, arousal: float) -> TurnEvidence:
    lower = text.lower()
    return TurnEvidence(turn=turn, concrete_request=any(x in lower for x in ("i need", "could you", "please", "i can't", "i cannot", "no,")), excessive_apology=len(re.findall(r"\b(sorry|apologi[sz]e)\b", lower)) > 1, maintained_boundary=any(x in lower for x in ("i can't", "i cannot", "i won't", "not able", "my boundary")), blame_language=any(x in lower for x in ("you always", "you never", "your fault")), specific_detail=any(x in lower for x in ("deadline", "because", "when ", "this week", "priority", "specifically")), arousal=arousal)


class RolePlayService:
    def start(self, scenario_id: str, level: Difficulty) -> tuple[RolePlayState, RolePlayScenario]:
        scenario = SCENARIOS[scenario_id]
        difficulty, cooperation = LEVELS[level]
        return RolePlayState(scenario_id=scenario_id, difficulty_level=level, difficulty=difficulty, cooperation=cooperation), scenario
    def respond(self, state: RolePlayState, message: str, emotion: EmotionState) -> str:
        if state.status != RolePlayStatus.ACTIVE: raise ValueError("Role-play is not active")
        scenario = SCENARIOS[state.scenario_id]
        state.turn += 1
        item = observe(state.turn, message, emotion.arousal)
        state.evidence.append(item)
        if emotion.arousal > 0.78:
            state.difficulty, state.cooperation = max(0.1, state.difficulty - 0.1), min(0.9, state.cooperation + 0.1)
        checks = {"concrete_request": item.concrete_request, "specific_detail": item.specific_detail, "maintained_boundary": item.maintained_boundary, "no_blame": not item.blame_language}
        state.success_progress = sum(checks.get(key, False) for key in scenario.success_conditions) / len(scenario.success_conditions)
        if state.success_progress == 1 or state.turn >= scenario.max_turns:
            self.finish(state, "success" if state.success_progress == 1 else "maximum_turns")
            return "Thank you—that gives me a clear understanding of what you need."
        if item.excessive_apology: return "You do not need to apologise. What is the request or boundary you want me to understand?"
        if not item.concrete_request: return "What specifically would you like me to do or understand?"
        if state.scenario_id == "boundary": return "Are you sure? I was really counting on you."
        if state.scenario_id == "relationship": return "Can you give me a specific example and tell me what you need instead?"
        return "Which responsibilities are most at risk, and what should I deprioritise?"
    def finish(self, state: RolePlayState, reason: str = "user_finished") -> None:
        state.status = RolePlayStatus.COMPLETED
        state.completion_reason, state.completed_at = reason, utcnow()
    def feedback(self, state: RolePlayState) -> SessionFeedback:
        evidence = state.evidence
        def metric(name: str, values: list[bool]) -> FeedbackMetric:
            hits = [item.turn for item, value in zip(evidence, values, strict=True) if value]
            return FeedbackMetric(name=name, score=len(hits) / max(len(values), 1), evidence_turns=hits)
        metrics = [metric("clarity", [e.concrete_request for e in evidence]), metric("specificity", [e.specific_detail for e in evidence]), metric("boundary maintenance", [e.maintained_boundary for e in evidence]), metric("non-blaming language", [not e.blame_language for e in evidence])]
        strengths = [f"You demonstrated {m.name}." for m in metrics if m.score >= 0.5]
        suggestions = [f"Try making your {m.name} more explicit on the next attempt." for m in metrics if m.score < 0.5]
        observed = [f"A concrete request appeared in turn {e.turn}." for e in evidence if e.concrete_request]
        if any(e.excessive_apology for e in evidence): observed.append("Repeated apology language appeared during the exercise.")
        return SessionFeedback(scenario_id=state.scenario_id, metrics=metrics, observed=observed or ["No measurable target behavior was detected."], strengths=strengths or ["You completed the practice conversation."], suggestions=suggestions or ["Repeat the scenario at a higher difficulty."], generation_source="deterministic")

