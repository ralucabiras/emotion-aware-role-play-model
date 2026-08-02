from app.models.domain import EmotionState, RolePlayScenario, RolePlayState

SCENARIOS = {
    "workload": RolePlayScenario(
        id="workload",
        title="Workload conversation",
        character="manager",
        user_objective="Explain the overload and ask the manager to prioritise work.",
        opening_line="Thanks for meeting with me. What did you want to discuss?",
        expected_skills=["clear request", "specific evidence", "assertiveness", "collaborative tone"],
    )
}


class RolePlayService:
    def start(self, scenario_id: str) -> tuple[RolePlayState, RolePlayScenario]:
        scenario = SCENARIOS[scenario_id]
        return RolePlayState(scenario_id=scenario_id), scenario

    def respond(self, state: RolePlayState, message: str, emotion: EmotionState) -> str:
        state.turn += 1
        if emotion.arousal > 0.78:
            state.difficulty = max(0.1, state.difficulty - 0.1)
            state.cooperation = min(0.9, state.cooperation + 0.1)
        elif any(word in message.lower() for word in ("prioritise", "priority", "deadline", "need")):
            state.difficulty = min(0.8, state.difficulty + 0.05)
        if not any(word in message.lower() for word in ("ask", "need", "could", "priority", "prioritise")):
            return "I understand there is a lot going on. What specifically would you like me to do?"
        if state.turn == 1:
            return "Which responsibilities are most at risk, and what change are you asking for?"
        return "That’s clear. Give me your proposed order of priorities, and I’ll help confirm what can wait."

