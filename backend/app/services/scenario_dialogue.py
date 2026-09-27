"""Versioned, deterministic character policies for optional profiled practice.

Rules detect observable language, not competence or a real person's intentions.
Saved workload-v2 and unprofiled requests continue using their original policy.
"""
import re
from dataclasses import dataclass

from app.models.domain import DialogueState, Difficulty, FeedbackMetric, RolePlayState, SessionFeedback
from app.services import workload_dialogue

VERSION = "scenario-dialogue-v3"
PROFILES = {
    "cooperative": "Open to your position and asks for a clear, practical response.",
    "rushed": "Short on time; asks for concise priorities and a workable time to talk.",
    "sceptical": "Questions the proposal, repeats pressure, and asks how a plan will be checked.",
}


@dataclass(frozen=True)
class ScenarioDefinition:
    version: str
    stages: tuple[tuple[str, str], ...]
    features: tuple[tuple[str, str], ...]
    outcome: str
    transitions: tuple[tuple[str, str], ...]
    actions: tuple[str, ...]


DEFINITIONS = {
    "workload": ScenarioDefinition("workload-v3", (("explain", "Explain the situation"), ("constraints", "Discuss constraints"), ("agree", "Agree a plan")),
        (("problem", "problem description"), ("request", "request"), ("workable_option", "workable trade-off"), ("check_in", "progress check")), "agreement",
        (("explain", "constraints"), ("constraints", "agree"), ("agree", "resolved")),
        ("ask_workload_detail", "raise_delivery_constraint", "ask_progress_check", "ask_concise_priorities", "hold_delivery_constraint", "confirm_proposal", "accept_agreement", "request_confirmation")),
    "boundary": ScenarioDefinition("boundary-v3", (("refuse", "State your boundary"), ("pressure", "Respond to pressure"), ("close", "Close respectfully")),
        (("refusal", "clear refusal"), ("held_boundary", "boundary held after pressure"), ("respectful_close", "respectful closure")), "boundary_held",
        (("refuse", "pressure"), ("pressure", "close"), ("pressure", "resolved"), ("close", "resolved"), ("close", "pressure")),
        ("ask_clear_answer", "renew_request", "clarify_boundary", "repeat_pressure", "allow_closure", "close_boundary", "request_respectful_closure")),
    "relationship": ScenarioDefinition("relationship-v3", (("explain", "Share your situation and need"), ("perspective", "Hear their perspective"), ("agree", "Choose a next step")),
        (("situation", "specific situation"), ("need", "personal need"), ("acknowledgement", "acknowledgement of perspective"), ("practical_request", "practical request")), "next_step",
        (("explain", "perspective"), ("perspective", "agree"), ("perspective", "unresolved"), ("agree", "unresolved"), ("agree", "perspective"), ("agree", "resolved")),
        ("close_unresolved", "share_perspective", "ask_situation_and_need", "offer_next_step", "hold_perspective", "confirm_next_step", "revisit_request", "ask_next_step_confirmation")),
}


def enable(state: RolePlayState, profile: str) -> None:
    if profile not in PROFILES or state.scenario_id not in DEFINITIONS:
        raise ValueError("Character profiles are available for workload, boundary and relationship practice")
    definition = DEFINITIONS[state.scenario_id]
    if state.scenario_id == "workload":
        workload_dialogue.enable(state)
    state.character_profile = profile
    state.profile_description = PROFILES[profile]
    state.scenario_version = definition.version
    state.policy_version = VERSION
    state.scoring_version = definition.version
    state.dialogue = DialogueState(stage=definition.stages[0][0], stage_labels=dict(definition.stages))
    if state.scenario:
        state.scenario = state.scenario.model_copy(deep=True)
        if state.scenario_id == "relationship":
            state.scenario.opening_line = "You wanted to talk about time together. What has been happening, and what do you need?"


def features(scenario: str, text: str) -> list[str]:
    lower = text.lower().replace("’", "'")
    found = set(workload_dialogue.features(text)) if scenario == "workload" else set()
    positive_clauses = [clause for clause in re.split(r"[.!?;]|\bbut\b", lower)
                        if not re.search(r"\b(?:not|never|don't|cannot|can't|won't|wouldn't|couldn't|shouldn't|isn't|impossible)\b", clause)]
    affirmative = " ".join(positive_clauses)
    if any(re.search(r"\b(?:check in|check-in|review|revisit)\b", clause)
           and (scenario != "workload" or re.search(r"\b(?:monday|tuesday|wednesday|thursday|before friday|before delivery)\b", clause))
           for clause in positive_clauses):
        found.add("check_in")
    if scenario == "boundary":
        refusal = re.search(r"(?:^|[.!]\s*)no(?:[,.!]|$)|\bi (?:can't|cannot|won't|will not|am not able to) (?:do|take|help|cover|agree|accept|commit)|\bmy answer is (?:still )?no\b|\bi (?:need|have) to (?:say no|decline)\b", lower)
        reversal = re.search(r"\b(?:maybe|unless|yes|changed my mind|i (?:can|will) (?:do|help|take|cover|accept)|i'll (?:do|help|take|cover|accept)|i can't say no|i cannot say no)\b", lower)
        if reversal:
            found.add("concession_or_uncertainty")
        if refusal and not reversal:
            found.add("refusal")
        if re.search(r"\b(?:thank you|thanks|take care|wish you well|hope you (?:find|can find)|understand)\b", affirmative):
            found.add("respectful_close")
    elif scenario == "relationship":
        rules = {
            "situation": r"\b(?:when we|when you|lately|last night|this week|evenings?|weekends?)\b",
            "need": r"\bi (?:feel|need|miss|would like|want)\b",
            "acknowledgement": r"\b(?:i understand|i hear|i recognise|i recognize|makes sense|your perspective)\b",
            "practical_request": r"\b(?:could we|can we|let's|i would like us to)\b.{0,60}\b(?:talk|check in|spend|sit|walk|have dinner)\b",
            "trial": r"\b(?:try|trial|once|one time|one evening)\b",
            "unresolved": r"\b(?:leave (?:it|this) unresolved|agree to disagree|stop here|end this conversation)\b",
        }
        found.update(name for name, pattern in rules.items() if re.search(pattern, affirmative))
        # Time must belong to the practical request, not an unrelated mention.
        for clause in positive_clauses:
            request = re.search(rules["practical_request"] + r".{0,100}", clause)
            if request:
                if re.search(r"\b(?:tonight|tomorrow|saturday|sunday|weekend|monday|tuesday|wednesday|thursday|friday|\d+ minutes)\b", request.group()):
                    found.add("time")
                if re.search(r"\b(?:saturday|sunday|weekend)\b", request.group()):
                    found.add("weekend")
        found.update(f for f in workload_dialogue.features(text) if f == "commitment")
    if re.search(r"\b(?:you always|you never|your fault|idiot|stupid|shut up)\b", lower):
        found.add("hostile")
    return sorted(found)


def pressure_limit(state: RolePlayState) -> int:
    return (2 if state.difficulty_level == Difficulty.DIFFICULT else 1) + int(state.character_profile == "sceptical")


def resolve(state: RolePlayState, outcome: str) -> None:
    state.dialogue.stage = "unresolved" if outcome == "unresolved" else "resolved"
    state.dialogue.outcome = outcome


def boundary(state: RolePlayState, text: str) -> tuple[str, str, list[str]]:
    d = state.dialogue
    f = set(state.evidence[-1].language_features)
    if d.stage == "refuse":
        if "refusal" not in f or "hostile" in f:
            return "ask_clear_answer", "Can you tell me clearly whether you can take this on?", ["clear_refusal_missing"]
        d.stage, d.pressure_rounds = "pressure", 1
        d.objection = {"cooperative": "Could you reconsider just this once?", "rushed": "I need an answer now. Could you take just the first part?", "sceptical": "You helped before. Why should this time be different?"}[state.character_profile]
        return "renew_request", d.objection, ["refusal_heard", "pressure_raised"]
    if d.stage == "pressure":
        if "refusal" not in f or "hostile" in f:
            return "clarify_boundary", "Does your answer remain no? I need to know where we stand.", ["boundary_not_reaffirmed"]
        state.evidence[-1].language_features.append("held_boundary")
        if d.pressure_rounds < pressure_limit(state):
            d.pressure_rounds += 1
            d.objection = "I was relying on you. Is there any chance you will change your answer?"
            return "repeat_pressure", d.objection, ["bounded_pressure_continues"]
        d.addressed_constraints = ["renewed request answered"]
        d.stage = "close"
        if "respectful_close" not in f:
            return "allow_closure", "I am disappointed, but I have heard your answer. Is there anything you want to say before we stop?", ["boundary_held", "closure_pending"]
    if d.stage == "close":
        if "concession_or_uncertainty" in f:
            d.stage = "pressure"
            return "clarify_boundary", "That sounds like your answer may have changed. Are you taking this on, or does your boundary still stand?", ["boundary_changed_or_uncertain"]
        if "respectful_close" in f and not {"hostile", "concession_or_uncertainty"} & f:
            resolve(state, "boundary_held")
            wording = "I still wish you would help, but we can stop here." if state.character_profile == "sceptical" else "Thank you for being clear. We can leave it there."
            return "close_boundary", wording, ["boundary_held", "respectful_closure", "concession_not_required"]
        return "request_respectful_closure", "We can stop here. What would you like to say to close this conversation?", ["respectful_closure_missing"]
    raise ValueError("Unsupported boundary stage")


def relationship(state: RolePlayState, text: str) -> tuple[str, str, list[str]]:
    d = state.dialogue
    f = set(state.evidence[-1].language_features)
    if "unresolved" in f and d.stage != "explain" and "hostile" not in f:
        resolve(state, "unresolved")
        return "close_unresolved", "We have different views and have not agreed a next step. We can leave the conversation here.", ["unresolved_ending_requested"]
    if d.stage == "explain":
        if {"situation", "need"} <= f and "hostile" not in f:
            d.stage = "perspective"
            d.objection = {"cooperative": "I have been tired after work. I want time together too, but need a manageable plan.", "rushed": "I am exhausted on work nights. Tonight will not work; I could consider the weekend.", "sceptical": "We have tried plans before and dropped them. I would only consider a small trial that we review."}[state.character_profile]
            if state.difficulty_level == Difficulty.DIFFICULT and state.character_profile != "sceptical":
                d.objection += " I also want a one-time trial and a plan to review it."
            return "share_perspective", d.objection, ["situation_and_need_expressed", "other_perspective_raised"]
        return "ask_situation_and_need", "What has been happening between us, and what do you need?", ["situation_or_need_missing"]
    if d.stage == "perspective":
        required = {"acknowledgement", "practical_request", "time"}
        if state.character_profile == "rushed":
            required.add("weekend")
        if state.character_profile == "sceptical" or state.difficulty_level == Difficulty.DIFFICULT:
            required |= {"trial", "check_in"}
        if required <= f and "hostile" not in f:
            d.proposed_options.append(text)
            d.addressed_constraints = [d.objection]
            d.stage = "agree"
            return "offer_next_step", "That sounds manageable. Can you confirm the next step you proposed?", ["perspective_acknowledged", "compatible_next_step_proposed"]
        return "hold_perspective", f"{d.objection} Could you acknowledge that and suggest a time for us to talk? We can also leave this unresolved.", ["perspective_or_compatible_request_missing"]
    if d.stage == "agree":
        blocked = re.search(r"\b(?:not|no|never|nothing|can't|cannot|won't|don't|if|unless|maybe|perhaps|instead|disagree)\b|\?", text.lower().replace("’", "'"))
        if "commitment" in f and "hostile" not in f and not blocked and "practical_request" not in f:
            d.final_agreement = d.proposed_options[-1]
            resolve(state, "next_step")
            return "confirm_next_step", "Agreed. Let's try the next step we just discussed.", ["next_step_confirmed"]
        if "practical_request" in f:
            d.stage = "perspective"
            return "revisit_request", "That changes the proposal. Let's check it against what each of us needs before agreeing.", ["changed_proposal_requires_review"]
        return "ask_next_step_confirmation", "Can you confirm that next step, or would you prefer to leave this unresolved?", ["confirmation_missing"]
    raise ValueError("Unsupported relationship stage")


def workload(state: RolePlayState, text: str) -> tuple[str, str, list[str]]:
    d = state.dialogue
    before = d.stage
    f = state.evidence[-1].language_features
    extra_check = state.character_profile == "sceptical" or state.difficulty_level == Difficulty.DIFFICULT
    if before == "constraints" and extra_check and "check_in" not in f:
        return "ask_progress_check", f"{d.objection} Could we check progress on Thursday, or another day before Friday?", ["progress_check_missing"]
    if before == "constraints" and state.character_profile == "rushed" and len(text.split()) > 45:
        return "ask_concise_priorities", "I have very little time. Can you give me the delivery and trade-off in a few sentences?", ["concise_priorities_needed"]
    action, wording, reasons = workload_dialogue.advance(state, text)
    if action == "raise_delivery_constraint":
        prefix = {"cooperative": "Let's find a workable balance. ", "rushed": "I have two minutes; please keep the priorities brief. ", "sceptical": "I am not convinced this plan will hold. "}[state.character_profile]
        if extra_check:
            wording += " Include a progress check before delivery."
        d.objection = prefix + wording
        wording = d.objection
    if d.stage == "resolved":
        d.outcome = "agreement"
    return action, wording, reasons


def advance(state: RolePlayState, text: str) -> tuple[str, str, list[str]]:
    before = state.dialogue.stage
    definition = DEFINITIONS[state.scenario_id]
    action, wording, reasons = {"workload": workload, "boundary": boundary, "relationship": relationship}[state.scenario_id](state, text)
    after = state.dialogue.stage
    if action not in definition.actions or (before != after and (before, after) not in definition.transitions):
        raise ValueError("Scenario policy produced an unsupported action or transition")
    return action, wording, [f"profile_{state.character_profile}", f"difficulty_{state.difficulty_level}", *reasons]


def progress(state: RolePlayState) -> float:
    if state.dialogue.stage == "resolved":
        return 1
    if state.dialogue.stage == "unresolved":
        return state.success_progress
    stages = [key for key, _ in DEFINITIONS[state.scenario_id].stages]
    return stages.index(state.dialogue.stage) / len(stages)


def feedback(state: RolePlayState) -> SessionFeedback:
    metrics, observed = [], []
    for feature, label in DEFINITIONS[state.scenario_id].features:
        if feature == "check_in" and state.character_profile != "sceptical" and state.difficulty_level != Difficulty.DIFFICULT:
            continue
        hits = [e.turn for e in state.evidence if feature in e.language_features]
        metrics.append(FeedbackMetric(name=label, score=float(bool(hits)), evidence_turns=hits))
        observed.extend(f"Language indicating {label} appeared in turn {turn}." for turn in hits)
    if state.dialogue.outcome == "unresolved":
        observed.append("The conversation ended with a recorded disagreement, without an agreed next step. This is not a personal failure.")
    return SessionFeedback(scenario_id=state.scenario_id, metrics=metrics, observed=observed,
        strengths=[f"Observed {m.name}." for m in metrics if m.score] or ["You practised the conversation."],
        suggestions=[f"Try making the {m.name} explicit." for m in metrics if not m.score] or ["Try another profile or wording."],
        generation_source=f"deterministic_{state.scenario_id}_v3")
