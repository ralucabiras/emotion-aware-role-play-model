import { useState } from 'react'
import { api } from '../services/api'
import type { Feedback, RolePlayState, Scenario } from '../types/api'

export type WorkspaceMode = 'reflect' | 'roleplay' | 'feedback'

const difficultyCopy: Record<string, string> = {
  beginner: 'Supportive responses and gentle prompts',
  intermediate: 'Some questions and realistic resistance',
  difficult: 'Stronger pushback while preserving safety',
}

export function ModeTabs({mode, roleplay, onChange}: {mode: WorkspaceMode; roleplay: RolePlayState | null; onChange: (mode: WorkspaceMode) => void}) {
  const active = roleplay && ['active', 'paused'].includes(roleplay.status)
  return <nav className="mode-tabs" aria-label="Workspace mode">
    <button className={mode === 'reflect' ? 'active' : ''} onClick={() => onChange('reflect')}>Reflect</button>
    <button className={mode === 'roleplay' ? 'active' : ''} onClick={() => onChange('roleplay')}>{active ? 'Active role-play' : 'Role-play'}</button>
    {roleplay?.status === 'completed' && <button className={mode === 'feedback' ? 'active' : ''} onClick={() => onChange('feedback')}>Feedback</button>}
  </nav>
}

export function ScenarioSetup({scenarios, selected, difficulty, busy, onScenario, onDifficulty, onStart}: {scenarios: Scenario[]; selected: string; difficulty: string; busy: boolean; onScenario: (id: string) => void; onDifficulty: (level: string) => void; onStart: (ratings: {confidence:number;anxiety:number}) => void}) {
  const [confidence, setConfidence] = useState(4), [anxiety, setAnxiety] = useState(4)
  const scenario = scenarios.find(item => item.id === selected) ?? scenarios[0]
  if (!scenario) return <section className="scenario-setup"><p>Loading scenarios…</p></section>
  return <section className="scenario-setup">
    <div className="setup-heading"><div><p className="eyebrow">Choose a rehearsal</p><h2>What would you like to practise?</h2></div><p>Choose a situation and level. You remain in control and can pause or finish at any time.</p></div>
    <div className="scenario-cards">{scenarios.map(item => <button key={item.id} className={selected === item.id ? 'selected' : ''} onClick={() => onScenario(item.id)} aria-pressed={selected === item.id}><span className="scenario-icon">{item.title.charAt(0)}</span><strong>{item.title}</strong><small>Practise with a {item.character}</small></button>)}</div>
    <div className="scenario-brief"><div><span>Your objective</span><p>{scenario.user_objective}</p></div><div><span>Skills to practise</span><ul>{scenario.expected_skills.map(skill => <li key={skill}>{skill}</li>)}</ul></div></div>
    <fieldset className="difficulty-options"><legend>Difficulty</legend>{Object.entries(difficultyCopy).map(([level, copy]) => <label key={level} className={difficulty === level ? 'selected' : ''}><input type="radio" name="difficulty" value={level} checked={difficulty === level} onChange={() => onDifficulty(level)}/><strong>{level}</strong><small>{copy}</small></label>)}</fieldset>
    <fieldset className="study-ratings"><legend>Before you begin <small>Optional research measure</small></legend><label>How confident do you feel about this conversation?<input type="range" min="1" max="7" value={confidence} onChange={event => setConfidence(Number(event.target.value))}/><span>{confidence} / 7</span></label><label>How anxious do you feel about this conversation?<input type="range" min="1" max="7" value={anxiety} onChange={event => setAnxiety(Number(event.target.value))}/><span>{anxiety} / 7</span></label></fieldset>
    <button className="primary start-rehearsal" disabled={busy} onClick={() => onStart({confidence, anxiety})}>{busy ? 'Preparing…' : `Begin with the ${scenario.character}`}</button>
  </section>
}

export function ActiveRolePlayHeader({scenario, state, busy, onAction}: {scenario?: Scenario; state: RolePlayState; busy: boolean; onAction: (action: string) => void}) {
  const progress = Math.round(state.success_progress * 100)
  return <section className="roleplay-header" aria-label="Active role-play information">
    <div className="character-avatar">{scenario?.character?.charAt(0).toUpperCase() ?? 'R'}</div>
    <div className="roleplay-identity"><p className="eyebrow">Speaking with your {scenario?.character ?? 'practice partner'}</p><h2>{scenario?.title ?? 'Role-play'}</h2><p>{scenario?.user_objective}</p></div>
    <div className="roleplay-status"><span>{state.difficulty_level}</span><strong>Turn {state.turn}</strong></div>
    <div className="progress-track" aria-label={`${progress}% of scenario skills demonstrated`}><i style={{width:`${progress}%`}}/></div>
    <div className="roleplay-actions">{state.status === 'active' ? <button disabled={busy} onClick={() => onAction('pause')}>Pause</button> : <button disabled={busy} onClick={() => onAction('resume')}>Resume</button>}<button className="finish" disabled={busy} onClick={() => onAction('finish')}>Finish & review</button></div>
  </section>
}

export function FeedbackScreen({scenario, feedback, state, onRetry, onConversation}: {scenario?: Scenario; feedback: Feedback; state: RolePlayState | null; onRetry: () => void; onConversation: () => void}) {
  const [confidence, setConfidence] = useState(4), [realism, setRealism] = useState(4), [usefulness, setUsefulness] = useState(4), [submitted, setSubmitted] = useState(false), [submitting, setSubmitting] = useState(false)
  async function submitPost() { if (!feedback.session_id) return; setSubmitting(true); try { await api.submitQuestionnaire(feedback.session_id, 'post', {confidence, realism, usefulness}); setSubmitted(true) } finally { setSubmitting(false) } }
  return <section className="feedback-screen">
    <div className="feedback-hero"><span className="completion-mark">✓</span><p className="eyebrow">Rehearsal complete</p><h2>{scenario?.title ?? 'Role-play feedback'}</h2><p>{state?.completion_reason === 'success' ? 'You demonstrated the scenario’s target skills.' : state?.completion_reason === 'maximum_turns' ? 'You reached the final turn. Review what appeared and what to try next.' : 'You chose to finish the rehearsal. Here is the evidence collected so far.'}</p></div>
    <div className="feedback-metrics">{feedback.metrics.map(metric => <article key={metric.name}><div><strong>{metric.name}</strong><span>{Math.round(metric.score * 100)}%</span></div><div className="metric-track"><i style={{width:`${metric.score * 100}%`}}/></div><small>{metric.evidence_turns?.length ? `Observed in turn${metric.evidence_turns.length > 1 ? 's' : ''} ${metric.evidence_turns.join(', ')}` : 'Not yet observed'}</small></article>)}</div>
    <div className="feedback-columns"><article><p className="eyebrow">Strengths</p><ul>{feedback.strengths.map(item => <li key={item}>{item}</li>)}</ul></article><article><p className="eyebrow">Try next</p><ul>{feedback.suggestions.map(item => <li key={item}>{item}</li>)}</ul></article></div>
    <section className="feedback-evidence"><p className="eyebrow">Evidence from this attempt</p>{feedback.observed.map(item => <p key={item}>{item}</p>)}<small>Generated from deterministic communication features. Source: {feedback.generation_source.replaceAll('_', ' ')}.</small></section>
    <section className="post-study"><p className="eyebrow">Optional research measure</p><h3>How was this rehearsal?</h3>{submitted ? <p className="settings-message" role="status">Thank you. Your ratings were saved with this session.</p> : <><div className="study-ratings"><label>Confidence now<input type="range" min="1" max="7" value={confidence} onChange={event => setConfidence(Number(event.target.value))}/><span>{confidence} / 7</span></label><label>Scenario realism<input type="range" min="1" max="7" value={realism} onChange={event => setRealism(Number(event.target.value))}/><span>{realism} / 7</span></label><label>Feedback usefulness<input type="range" min="1" max="7" value={usefulness} onChange={event => setUsefulness(Number(event.target.value))}/><span>{usefulness} / 7</span></label></div><button className="secondary" disabled={submitting || !feedback.session_id} onClick={() => void submitPost()}>{submitting ? 'Saving…' : 'Save research ratings'}</button></>}</section>
    <div className="feedback-actions"><button className="secondary" onClick={onConversation}>Return to conversation</button><button className="primary" onClick={onRetry}>Practise again</button></div>
  </section>
}
