"""Auditable workload policy. Features describe words, never personal competence."""
import re

from app.models.domain import DialogueState, FeedbackMetric, RolePlayState, SessionFeedback

VERSION = "workload-v2"
CONSTRAINT = "The client report must be ready by Friday."


def features(text: str) -> list[str]:
    text = text.lower().replace("’", "'")
    # Evaluate bounded clauses, excluding explicitly negated claims.
    clauses = re.split(r"[.!?;]|\bbut\b", text)
    positive = " ".join(c for c in clauses if not re.search(
        r"\b(?:not|never|no|can't|cannot|won't|don't|isn't|wouldn't|couldn't)\b", c))
    found = []
    rules = {
        "problem": r"\b(?:overload\w*|too much|too many|at risk|struggling|workload|capacity|hours of work|more work than)\b",
        "request": r"\b(?:could (?:you|we)|can (?:you|we)|please|i need|i would like|let's|help me|prioriti[sz]e)\b",
        "detail": r"\b(?:report|project|tasks?|deadline|hours?|\d+)\b",
        "acknowledgement": r"\b(?:understand|recognise|recognize|hear you|client needs|must|important|has to)\b",
        "trade_off": r"\b(?:move|postpone|defer|delegate|reassign|delay|hand off|instead|reduce|push back)\b",
        "commitment": r"^\s*(?:agreed|i agree|that works|let's do that|yes)(?:\s*$|[,])|\bi(?: will|'ll| can) (?:carry out|follow|commit to|stick to) (?:that|the|this) plan\b",
    }
    for name, pattern in rules.items():
        if re.search(pattern, positive):
            found.append(name)
    if re.search(r"\breport\b.{0,70}\b(?:by|for|on) friday\b", positive):
        found.append("report_friday")
    if re.search(
            r"\b(?:move|postpone|defer|delegate|reassign|delay|hand off|push back)\b"
            r"(?:(?!\breport\b).){0,50}\b(?:other work|internal work|admin|presentation|tasks?|project)\b"
            r".{0,40}\b(?:monday|next week|colleague|teammate|someone else)\b", positive):
        found.append("workable_option")
    return found


def advance(state: RolePlayState, text: str) -> tuple[str, str, list[str]]:
    dialogue = state.dialogue
    assert dialogue is not None
    observed = set(state.evidence[-1].language_features)
    if dialogue.stage == "explain":
        accumulated = {f for e in state.evidence for f in e.language_features}
        if {"problem", "request", "detail"} <= accumulated and observed:
            dialogue.stage = "constraints"
            dialogue.objection = CONSTRAINT
            return "raise_delivery_constraint", f"{CONSTRAINT} What could we change in the other work to protect that delivery?", ["problem_and_request_established", "objection_raised"]
        return "ask_workload_detail", "Which work is at risk, and what do you need me to prioritise?", ["opening_evidence_missing"]
    if dialogue.stage == "constraints":
        if {"acknowledgement", "report_friday", "workable_option"} <= observed:
            dialogue.addressed_constraints = [CONSTRAINT]
            dialogue.proposed_options.append(text)
            dialogue.stage = "agree"
            return "confirm_proposal", "I can support that trade-off, keeping the report due Friday. Please confirm that you can carry out the plan you just proposed.", ["delivery_constraint_addressed", "workable_trade_off_proposed"]
        return "hold_delivery_constraint", f"{CONSTRAINT} Can you acknowledge that deadline and propose which other work moves to Monday or next week, or goes to a colleague?", ["constraint_or_trade_off_missing"]
    if dialogue.stage == "agree":
        # A negative or conditional reply must never count as acceptance.
        normalized = text.lower().replace("’", "'")
        blocked = re.search(r"\b(?:not|no|nothing|never|can't|cannot|won't|don't|disagree|impossible|refuse|unless|if|maybe|perhaps|instead)\b|\?", normalized)
        if "commitment" in observed and not blocked and "trade_off" not in observed:
            dialogue.stage = "resolved"
            dialogue.final_agreement = dialogue.proposed_options[-1]
            return "accept_agreement", "Agreed. We will keep the report due Friday and use the trade-off you proposed for the other work.", ["explicit_confirmation", "agreement_reached"]
        if {"acknowledgement", "report_friday", "workable_option"} <= observed:
            dialogue.proposed_options.append(text)
            return "confirm_proposal", "I can support that revised proposal. Can you confirm you will carry it out?", ["proposal_revised", "confirmation_required"]
        return "request_confirmation", "Can you commit to the proposed plan, or do we need to revise it?", ["explicit_confirmation_missing"]
    raise ValueError("Resolved dialogue cannot advance")


def feedback(state: RolePlayState) -> SessionFeedback:
    names = {"problem": "problem description", "request": "request", "detail": "supporting detail",
             "acknowledgement": "acknowledgement of a constraint", "workable_option": "workable trade-off"}
    metrics = []
    observed = []
    for feature, label in names.items():
        hits = [e.turn for e in state.evidence if feature in e.language_features]
        metrics.append(FeedbackMetric(name=label, score=float(bool(hits)), evidence_turns=hits))
        observed.extend(f"Language indicating {label} appeared in turn {n}." for n in hits)
    agreement_hits = [state.turn] if state.dialogue and state.dialogue.final_agreement else []
    metrics.append(FeedbackMetric(name="confirmed agreement", score=float(bool(agreement_hits)), evidence_turns=agreement_hits))
    return SessionFeedback(scenario_id=state.scenario_id, metrics=metrics, observed=observed,
        strengths=[f"Observed {m.name}." for m in metrics if m.score] or ["You practised starting the conversation."],
        suggestions=[f"Try making the {m.name} explicit." for m in metrics if not m.score] or ["Try another wording for the same situation."],
        generation_source="deterministic_workload_v2")


def enable(state: RolePlayState) -> None:
    state.scenario_version = state.policy_version = state.scoring_version = VERSION
    state.dialogue = DialogueState()
    if state.scenario:
        state.scenario = state.scenario.model_copy(deep=True)
        state.scenario.opening_line = "Thanks for meeting with me. We have a client report due Friday alongside the other work. What is at risk, and what do you need?"
