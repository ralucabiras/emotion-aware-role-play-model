import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { PostRatings, RatingInput } from './StudyRatings'
import type { Feedback, RolePlayState, Scenario } from '../types/api'

export type WorkspaceMode = 'reflect' | 'roleplay' | 'feedback'

const difficultyCopy: Record<string, string> = {
  beginner: 'Supportive responses and gentle prompts',
  intermediate: 'Some questions and realistic resistance',
  difficult: 'Stronger pushback while preserving safety',
}

export function ModeTabs({mode, roleplay, onChange, disabled=false}: {mode: WorkspaceMode; roleplay: RolePlayState | null; onChange: (mode: WorkspaceMode) => void; disabled?:boolean}) {
  const active = roleplay && ['active', 'paused'].includes(roleplay.status)
  return <nav className="mode-tabs" aria-label="Workspace mode">
    <button disabled={disabled} className={mode === 'reflect' ? 'active' : ''} aria-current={mode==='reflect'?'page':undefined} onClick={() => onChange('reflect')}>Reflect</button>
    <button disabled={disabled} className={mode === 'roleplay' ? 'active' : ''} aria-current={mode==='roleplay'?'page':undefined} onClick={() => onChange('roleplay')}>{active ? 'Active role-play' : 'Role-play'}</button>
    {roleplay?.status === 'completed' && <button disabled={disabled} className={mode === 'feedback' ? 'active' : ''} aria-current={mode==='feedback'?'page':undefined} onClick={() => onChange('feedback')}>Feedback</button>}
  </nav>
}

const customSkills = ['clear request','specific detail','boundary maintenance','I-statements','non-blaming language']

export function ScenarioSetup({studyTask,onFreePractice,scenarios, selected, difficulty, busy, onScenario, onDifficulty, onStart, onScenarios}: {studyTask?:string;onFreePractice?:()=>void;scenarios: Scenario[]; selected: string; difficulty: string; busy: boolean; onScenario: (id: string) => void; onDifficulty: (level: string) => void; onStart: (ratings: {confidence:number;anxiety:number}|null) => void; onScenarios:(items:Scenario[])=>void}) {
  const [confidence, setConfidence] = useState<number|null>(null), [anxiety, setAnxiety] = useState<number|null>(null)
  const [building,setBuilding]=useState(false),[saving,setSaving]=useState(false),[builderError,setBuilderError]=useState('')
  const [custom,setCustom]=useState({title:'',character:'',situation:'',user_objective:'',opening_line:'',skills:['clear request'] as string[]})
  const scenario = scenarios.find(item => item.id === selected) ?? scenarios[0]
  function field(name:string,value:string){setCustom(current=>({...current,[name]:value}))}
  function skill(value:string){setCustom(current=>({...current,skills:current.skills.includes(value)?current.skills.filter(item=>item!==value):current.skills.length<3?[...current.skills,value]:current.skills}))}
  async function create(){setSaving(true);setBuilderError('');try{const result=await api.createScenario(custom);onScenarios([...scenarios,result]);onScenario(result.id);setBuilding(false);setCustom({title:'',character:'',situation:'',user_objective:'',opening_line:'',skills:['clear request']})}catch(caught){setBuilderError(caught instanceof Error?caught.message:'Scenario could not be saved.')}finally{setSaving(false)}}
  async function remove(id:string){if(!confirm('Delete this custom scenario? Existing rehearsal history will remain available.'))return;await api.deleteScenario(id);const remaining=scenarios.filter(item=>item.id!==id);onScenarios(remaining);onScenario(remaining[0]?.id??'workload')}
  if (!scenario) return <section className="scenario-setup"><p>Loading scenarios…</p></section>
  return <section className="scenario-setup">
    <div className="setup-heading"><div><p className="eyebrow">Choose a rehearsal</p><h2>What would you like to practise?</h2></div><p>Choose a situation and level. You remain in control and can pause or finish at any time.</p></div>
    {studyTask&&<p role="note">Required study task - intermediate difficulty. <button className="text-button" onClick={onFreePractice}>Switch to additional practice</button></p>}
    <div className="scenario-cards">{scenarios.filter(item=>!studyTask||item.id===studyTask).map(item => <div className="scenario-card-wrap" key={item.id}><button className={selected === item.id ? 'selected' : ''} onClick={() => onScenario(item.id)} aria-pressed={selected === item.id}><span className="scenario-icon">{item.title.charAt(0)}</span><strong>{item.title}</strong><small>Practise with a {item.character}</small>{item.id.startsWith('custom_')&&<em>Your scenario</em>}</button>{item.id.startsWith('custom_')&&<button className="remove-scenario" onClick={()=>void remove(item.id)} aria-label={`Delete ${item.title}`}>×</button>}</div>)}</div>
    {!studyTask&&<button className="custom-scenario-toggle" onClick={()=>setBuilding(value=>!value)}>{building?'Cancel scenario builder':'+ Create your own scenario'}</button>}
    {building&&!studyTask&&<section className="scenario-builder"><div><p className="eyebrow">Custom rehearsal</p><h3>Build a situation to practise</h3><p>The conversation wording adapts, while safety and scoring remain controlled by AffectLab.</p></div><div className="builder-fields"><label>Scenario title<input value={custom.title} maxLength={80} onChange={event=>field('title',event.target.value)} placeholder="Asking for flexible hours"/></label><label>Who are you speaking with?<input value={custom.character} maxLength={50} onChange={event=>field('character',event.target.value)} placeholder="team lead"/></label><label className="wide-field">Situation<textarea value={custom.situation} maxLength={500} onChange={event=>field('situation',event.target.value)} placeholder="Briefly describe the context…"/></label><label className="wide-field">Your objective<textarea value={custom.user_objective} maxLength={300} onChange={event=>field('user_objective',event.target.value)} placeholder="What would a useful outcome be?"/></label><label className="wide-field">Their opening line<input value={custom.opening_line} maxLength={300} onChange={event=>field('opening_line',event.target.value)} placeholder="You wanted to talk—what is this about?"/></label></div><fieldset className="builder-skills"><legend>Skills to practise <small>Choose 1–3</small></legend>{customSkills.map(item=><label key={item} className={custom.skills.includes(item)?'selected':''}><input type="checkbox" checked={custom.skills.includes(item)} onChange={()=>skill(item)}/>{item}</label>)}</fieldset>{builderError&&<p className="error" role="alert">{builderError}</p>}<button className="primary" disabled={saving||!custom.title.trim()||!custom.character.trim()||custom.situation.trim().length<10||custom.user_objective.trim().length<10||custom.opening_line.trim().length<3||!custom.skills.length} onClick={()=>void create()}>{saving?'Saving…':'Save and select scenario'}</button></section>}
    <div className="scenario-brief"><div><span>Your objective</span><p>{scenario.user_objective}</p></div><div><span>Skills to practise</span><ul>{scenario.expected_skills.map(skill => <li key={skill}>{skill}</li>)}</ul></div></div>
    {!studyTask&&<fieldset className="difficulty-options"><legend>Difficulty</legend>{Object.entries(difficultyCopy).map(([level, copy]) => <label key={level} className={difficulty === level ? 'selected' : ''}><input type="radio" name="difficulty" value={level} checked={difficulty === level} onChange={() => onDifficulty(level)}/><strong>{level}</strong><small>{copy}</small></label>)}</fieldset>}
    <fieldset className="study-ratings"><legend>Before you begin <small>Optional research measure</small></legend><RatingInput label="How confident do you feel about this conversation?" value={confidence} onChange={setConfidence}/><RatingInput label="How anxious do you feel about this conversation?" value={anxiety} onChange={setAnxiety}/></fieldset>
    <button className="primary" disabled={busy||confidence===null||anxiety===null} onClick={() => onStart({confidence:confidence!, anxiety:anxiety!})}>{busy ? 'Preparing...' : `Begin with the ${scenario.character}`}</button>
    <button className="secondary" disabled={busy} onClick={()=>onStart(null)}>Skip pre-ratings and begin</button>
  </section>
}

export function ActiveRolePlayHeader({scenario, state, busy, onAction, onRewind}: {scenario?: Scenario; state: RolePlayState; busy: boolean; onAction: (action: string) => void; onRewind:()=>void}) {
  const progress = Math.round(state.success_progress * 100)
  return <section className="roleplay-header" aria-label="Active role-play information">
    <div className="character-avatar">{scenario?.character?.charAt(0).toUpperCase() ?? 'R'}</div>
    <div className="roleplay-identity"><p className="eyebrow">Speaking with your {scenario?.character ?? 'practice partner'}</p><h2>{scenario?.title ?? 'Role-play'}</h2><p>{scenario?.user_objective}</p></div>
    <div className="roleplay-status"><span>{state.difficulty_level}</span><strong>Turn {state.turn}</strong></div>
    <div className="progress-track" aria-label={`${progress}% of scenario skills demonstrated`}><i style={{width:`${progress}%`}}/></div>
    <div className="roleplay-actions"><button disabled={busy||state.turn===0} onClick={onRewind}>Retry last turn</button>{state.status === 'active' ? <button disabled={busy} onClick={() => onAction('pause')}>Pause</button> : <button disabled={busy} onClick={() => onAction('resume')}>Resume</button>}<button className="finish" disabled={busy} onClick={() => onAction('finish')}>Finish & review</button></div>
  </section>
}

export function FeedbackScreen({scenario, feedback, state, postToken, onRetry, onRewind, onConversation}: {scenario?: Scenario; feedback: Feedback; state: RolePlayState | null; postToken?:string|null; onRetry: () => void; onRewind:()=>void; onConversation: () => void}) {
  const [note,setNote]=useState(''),[noteState,setNoteState]=useState('')
  useEffect(()=>{if(!feedback.session_id)return;let active=true;void api.getSession(feedback.session_id).then(session=>active&&setNote(session.takeaway));return()=>{active=false}},[feedback.session_id])

  return <section className="feedback-screen">
    <div className="feedback-hero"><span className="completion-mark">✓</span><p className="eyebrow">Rehearsal complete</p><h2>{scenario?.title ?? 'Role-play feedback'}</h2><p>{state?.completion_reason === 'success' ? 'You demonstrated the scenario’s target skills.' : state?.completion_reason === 'maximum_turns' ? 'You reached the final turn. Review what appeared and what to try next.' : 'You chose to finish the rehearsal. Here is the evidence collected so far.'}</p></div>
    <div className="feedback-metrics">{feedback.metrics.map(metric => <article key={metric.name}><div><strong>{metric.name}</strong><span>{Math.round(metric.score * 100)}%</span></div><div className="metric-track"><i style={{width:`${metric.score * 100}%`}}/></div><small>{metric.evidence_turns?.length ? `Observed in turn${metric.evidence_turns.length > 1 ? 's' : ''} ${metric.evidence_turns.join(', ')}` : 'Not yet observed'}</small></article>)}</div>
    {feedback.comparisons.length>0&&<section className="feedback-comparison"><div><p className="eyebrow">Compared with your previous attempt</p><h3>What changed this time</h3><p>Same scenario, using the same observable skill measures.</p></div><div>{feedback.comparisons.map(item=>{const points=Math.round(item.change*100),direction=Math.abs(points)<5?'About the same':points>0?`${points} points higher`:`${Math.abs(points)} points lower`;return <article key={item.name}><strong>{item.name}</strong><div className="comparison-bars"><span>Previous <i><b style={{width:`${item.previous_score*100}%`}}/></i><em>{Math.round(item.previous_score*100)}%</em></span><span>This time <i><b style={{width:`${item.current_score*100}%`}}/></i><em>{Math.round(item.current_score*100)}%</em></span></div><small className={points>4?'up':points < -4?'down':'stable'}>{direction}</small></article>})}</div><small>Differences describe observed language in these two attempts. They do not measure personal or clinical improvement.</small></section>}
    <div className="feedback-columns"><article><p className="eyebrow">Strengths</p><ul>{feedback.strengths.map(item => <li key={item}>{item}</li>)}</ul></article><article><p className="eyebrow">Try next</p><ul>{feedback.suggestions.map(item => <li key={item}>{item}</li>)}</ul></article></div>
    <section className="feedback-evidence"><p className="eyebrow">Evidence from this attempt</p>{feedback.observed.map(item => <p key={item}>{item}</p>)}<small>Generated from deterministic communication features. Source: {feedback.generation_source.replaceAll('_', ' ')}.</small></section>
    <section className="takeaway-card"><p className="eyebrow">Your takeaway</p><h3>What do you want to remember?</h3><p>Write this in your own words. It will be saved with this session and shown on your dashboard.</p><label className="sr-only" htmlFor="takeaway-note">Personal takeaway</label><textarea id="takeaway-note" maxLength={500} rows={3} value={note} onChange={event=>{setNote(event.target.value);setNoteState('')}} placeholder="For example: Lead with the concrete request, then explain why."/><div><small>{note.length} / 500</small><button className="secondary" disabled={noteState==='saving'||!feedback.session_id} aria-busy={noteState==='saving'} onClick={async()=>{if(!feedback.session_id)return;setNoteState('saving');try{await api.saveTakeaway(feedback.session_id,note);setNoteState('saved')}catch{setNoteState('error')}}}>{noteState==='saving'?'Saving…':noteState==='saved'?'Saved':noteState==='error'?'Try saving again':'Save takeaway'}</button></div><span className="sr-only" aria-live="polite">{noteState==='saved'?'Takeaway saved.':noteState==='error'?'Takeaway could not be saved.':''}</span></section>
    {feedback.session_id&&<PostRatings key={feedback.session_id} sessionId={feedback.session_id} token={postToken}/>}
    <div className="feedback-actions"><button className="secondary" disabled={!state?.turn} onClick={onRewind}>Retry last turn</button><button className="secondary" onClick={onConversation}>Return to conversation</button><button className="primary" onClick={onRetry}>Practise again</button></div>
  </section>
}
