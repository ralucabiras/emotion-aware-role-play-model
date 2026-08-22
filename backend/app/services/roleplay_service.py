import re
from dataclasses import dataclass

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
    "colleague_feedback": RolePlayScenario(id="colleague_feedback", title="Feedback to a colleague", character="colleague", user_objective="Address an unhelpful work behaviour with a specific, respectful request.", opening_line="You said you wanted to give me some feedback. What have you noticed?", expected_skills=["specific example", "impact statement", "clear request", "non-blaming language"], difficulty_behaviors={Difficulty.BEGINNER:"Listens with curiosity", Difficulty.INTERMEDIATE:"Questions the example", Difficulty.DIFFICULT:"Becomes defensive"}, success_conditions=["concrete_request", "specific_detail", "no_blame"]),
    "deadline": RolePlayScenario(id="deadline", title="Negotiating a deadline", character="project lead", user_objective="Explain a delivery risk and propose a realistic deadline or reduced scope.", opening_line="You wanted to discuss the delivery date. What is the risk?", expected_skills=["specific evidence", "realistic proposal", "collaborative tone"], difficulty_behaviors={Difficulty.BEGINNER:"Explores options", Difficulty.INTERMEDIATE:"Asks for justification", Difficulty.DIFFICULT:"Insists the date is important"}, success_conditions=["concrete_request", "specific_detail"]),
    "household": RolePlayScenario(id="household", title="Sharing household responsibilities", character="housemate", user_objective="Ask for a fairer division of recurring responsibilities without blame.", opening_line="You said the way we divide things at home is not working. What would you like to change?", expected_skills=["I-statement", "specific responsibility", "clear agreement", "non-blaming language"], difficulty_behaviors={Difficulty.BEGINNER:"Open to a plan", Difficulty.INTERMEDIATE:"Disagrees about the current balance", Difficulty.DIFFICULT:"Minimises the problem"}, success_conditions=["concrete_request", "specific_detail", "no_blame"]),
}


@dataclass(frozen=True)
class RolePlayReplyPlan:
    action: str
    fallback_text: str
    completed: bool = False


def observe(turn: int, text: str, arousal: float) -> TurnEvidence:
    lower = text.lower()
    return TurnEvidence(
        turn=turn,
        concrete_request=any(x in lower for x in ("i need", "i want", "i would like", "could you", "please", "i can't", "i cannot", "no,")),
        excessive_apology=len(re.findall(r"\b(sorry|apologi[sz]e)\b", lower)) > 1,
        maintained_boundary=any(x in lower for x in ("i can't", "i cannot", "i won't", "not able", "my boundary", "i need to say no")),
        blame_language=any(x in lower for x in ("you always", "you never", "you don't", "your fault", "you make me")),
        specific_detail=any(x in lower for x in ("deadline", "because", "when ", "this week", "priority", "specifically", "each week", "per week", "evening", "weekend", "minutes", "hours", "meeting", "interrupt", "chores", "dishes", "cleaning", "monday", "tuesday", "wednesday", "thursday", "friday")) or bool(re.search(r"\b\d+\b", lower)),
        i_statement=bool(re.search(r"\bi (?:feel|need|want|would like|am)\b", lower)),
        arousal=arousal,
    )


class RolePlayService:
    def start(self, scenario_id: str, level: Difficulty) -> tuple[RolePlayState, RolePlayScenario]:
        scenario = SCENARIOS[scenario_id]
        difficulty, cooperation = LEVELS[level]
        return RolePlayState(scenario_id=scenario_id, difficulty_level=level, difficulty=difficulty, cooperation=cooperation), scenario
    def respond(self, state: RolePlayState, message: str, emotion: EmotionState) -> str:
        return self.plan_response(state, message, emotion).fallback_text
    def plan_response(self, state: RolePlayState, message: str, emotion: EmotionState) -> RolePlayReplyPlan:
        if state.status != RolePlayStatus.ACTIVE: raise ValueError("Role-play is not active")
        scenario = SCENARIOS[state.scenario_id]
        state.turn += 1
        item = observe(state.turn, message, emotion.arousal)
        state.evidence.append(item)
        if emotion.arousal > 0.78:
            state.difficulty, state.cooperation = max(0.1, state.difficulty - 0.1), min(0.9, state.cooperation + 0.1)
        checks = {
            "concrete_request": any(entry.concrete_request for entry in state.evidence),
            "specific_detail": any(entry.specific_detail for entry in state.evidence),
            "maintained_boundary": any(entry.maintained_boundary for entry in state.evidence),
            "no_blame": not item.blame_language,
        }
        if state.scenario_id == "boundary":
            required_refusals = 1 if state.difficulty_level == Difficulty.BEGINNER else 2
            refusal_count = sum(entry.maintained_boundary for entry in state.evidence)
            state.success_progress = min(1, refusal_count / required_refusals)
            succeeded = refusal_count >= required_refusals and not item.excessive_apology
        else:
            state.success_progress = sum(checks.get(key, False) for key in scenario.success_conditions) / len(scenario.success_conditions)
            succeeded = state.success_progress == 1
        if succeeded or state.turn >= scenario.max_turns:
            self.finish(state, "success" if succeeded else "maximum_turns")
            return RolePlayReplyPlan("accept_and_close", "Thank you—that gives me a clear understanding of what you need.", True)
        if item.excessive_apology: return RolePlayReplyPlan("request_clear_boundary", "You do not need to apologise. What is the request or boundary you want me to understand?")
        if not item.concrete_request:
            if state.scenario_id == "boundary": return RolePlayReplyPlan("request_clear_refusal", "It sounds like you may not have the capacity. Can you give me a clear yes or no?")
            if state.scenario_id == "relationship": return RolePlayReplyPlan("request_clear_need", "I hear that you want more connection. What would you like us to do differently?")
            return RolePlayReplyPlan("request_clarity", "What specifically would you like me to do or understand?")
        if state.scenario_id == "boundary":
            if state.difficulty_level == Difficulty.DIFFICULT: return RolePlayReplyPlan("apply_pressure", "I understand you are busy, but this puts me in a difficult position. Is your answer still no?")
            return RolePlayReplyPlan("gentle_pushback", "Are you sure? I was really counting on you.")
        if state.scenario_id in {"relationship", "household"}: return RolePlayReplyPlan("request_specific_routine", "What would that change look like in practice—for example, a particular time, task, or routine?")
        if state.scenario_id == "colleague_feedback": return RolePlayReplyPlan("request_specific_example", "Can you describe a recent example and the change you would like me to make?")
        if state.scenario_id == "deadline": return RolePlayReplyPlan("request_proposal", "What delivery date or scope change are you proposing, and what is driving it?")
        return RolePlayReplyPlan("request_prioritisation", "Which responsibilities are most at risk, and what should I deprioritise?")
    def finish(self, state: RolePlayState, reason: str = "user_finished") -> None:
        state.status = RolePlayStatus.COMPLETED
        state.completion_reason, state.completed_at = reason, utcnow()
    def feedback(self, state: RolePlayState) -> SessionFeedback:
        evidence = state.evidence
        def metric(name: str, values: list[bool]) -> FeedbackMetric:
            hits = [item.turn for item, value in zip(evidence, values, strict=True) if value]
            return FeedbackMetric(name=name, score=len(hits) / max(len(values), 1), evidence_turns=hits)
        metric_sets = {
            "workload": [
                ("clear request", [e.concrete_request for e in evidence]),
                ("specific evidence", [e.specific_detail for e in evidence]),
                ("collaborative tone", [not e.blame_language for e in evidence]),
            ],
            "boundary": [
                ("clear refusal", [e.maintained_boundary for e in evidence]),
                ("boundary maintenance", [e.maintained_boundary for e in evidence]),
                ("concise delivery", [not e.excessive_apology for e in evidence]),
            ],
            "relationship": [
                ("I-statements", [e.i_statement for e in evidence]),
                ("specific need", [e.specific_detail for e in evidence]),
                ("non-blaming language", [not e.blame_language for e in evidence]),
            ],
            "colleague_feedback": [
                ("clear request", [e.concrete_request for e in evidence]),
                ("specific example", [e.specific_detail for e in evidence]),
                ("non-blaming language", [not e.blame_language for e in evidence]),
            ],
            "deadline": [
                ("realistic proposal", [e.concrete_request for e in evidence]),
                ("specific evidence", [e.specific_detail for e in evidence]),
                ("collaborative tone", [not e.blame_language for e in evidence]),
            ],
            "household": [
                ("I-statements", [e.i_statement for e in evidence]),
                ("specific agreement", [e.specific_detail for e in evidence]),
                ("non-blaming language", [not e.blame_language for e in evidence]),
            ],
        }
        metrics = [metric(name, values) for name, values in metric_sets[state.scenario_id]]
        strengths = [f"You demonstrated {m.name}." for m in metrics if m.score >= 0.5]
        suggestions = [f"Try making your {m.name} more explicit on the next attempt." for m in metrics if m.score < 0.5]
        observed = [f"A concrete request appeared in turn {e.turn}." for e in evidence if e.concrete_request]
        observed.extend(f"An I-statement appeared in turn {e.turn}." for e in evidence if e.i_statement)
        if any(e.excessive_apology for e in evidence): observed.append("Repeated apology language appeared during the exercise.")
        if not suggestions:
            suggestions = ["Repeat the scenario at a higher difficulty."] if state.difficulty_level != Difficulty.DIFFICULT else ["Try the difficult scenario again with different wording or a more specific example."]
        return SessionFeedback(scenario_id=state.scenario_id, metrics=metrics, observed=observed or ["No measurable target behavior was detected."], strengths=strengths or ["You completed the practice conversation."], suggestions=suggestions, generation_source="deterministic")
