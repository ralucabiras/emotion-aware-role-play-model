import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../services/api'
import type { ConversationTurn, EmotionState, Feedback, MultimodalAffect, RolePlayState, Scenario, SessionResponse, SessionSummary, UserProfile } from '../types/api'
import { StudyChecklist } from './StudyChecklist'
import { notifyStudyProgress } from '../services/studyProgress'
import type { StudyTask } from '../types/api'
import { EmotionPanel } from './EmotionPanel'
import { ActiveRolePlayHeader, FeedbackScreen, ModeTabs, ScenarioSetup } from './RolePlayWorkspace'
import type { WorkspaceMode } from './RolePlayWorkspace'
import { VoiceCapture } from './VoiceCapture'
import type { VoiceSample } from './VoiceCapture'
import { goalLabel, recommendedScenario } from '../practiceGoals'

function MultimodalPanel({result}: {result: MultimodalAffect}) {
  const sorted = Object.entries(result.distribution).sort((left, right) => right[1] - left[1])
  const low = result.confidence_level === 'low'
  return <section className={`multimodal-panel confidence-${result.confidence_level}`} aria-label="Voice and text affect estimate"><p className="eyebrow">Voice + text estimate</p><h2>{low ? 'Uncertain estimate' : result.label}</h2><strong>{Math.round(result.confidence * 100)}% confidence · {result.confidence_level}</strong>{low && <p className="confidence-warning">No single label reached the display threshold. Treat the leading possibilities as tentative.</p>}<div className="modality-comparison"><article><span>Text signal</span><strong>{result.text_label}</strong><small>{Math.round(result.text_confidence * 100)}%</small></article><article><span>Voice signal</span><strong>{result.audio_label}</strong><small>{Math.round(result.audio_confidence * 100)}%</small></article></div><p className={`agreement ${result.modalities_agree ? 'agree' : 'disagree'}`}>{result.modalities_agree ? 'Text and voice point to the same leading label.' : 'Text and voice point to different leading labels; the fused result is less straightforward.'}</p><div className="distribution">{sorted.map(([label, probability]) => <div key={label}><span>{label}</span><div><i style={{width:`${probability * 100}%`}}/></div><small>{Math.round(probability * 100)}%</small></div>)}</div><p>{result.disclaimer} Audio was not stored. Inference took {(result.latency_ms / 1000).toFixed(1)}s{result.queue_ms > 50 ? ` after ${(result.queue_ms / 1000).toFixed(1)}s queued` : ''}.</p></section>
}

export function Dashboard({user, initialSessionId, initialRoleplay=false, initialStudyTask, onLogout, onDashboard, onSettings}: {user: UserProfile; initialSessionId?:string; initialRoleplay?:boolean; initialStudyTask?:string; onLogout: () => void; onDashboard:()=>void; onSettings: () => void}) {
  const [sessionId, setSessionId] = useState<string>()
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [sessionTitle, setSessionTitle] = useState('New reflection')
  const [turns, setTurns] = useState<ConversationTurn[]>([])
  const [emotion, setEmotion] = useState<EmotionState|null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [studyTask,setStudyTask]=useState(user.pilot_enrolled&&['workload','boundary','relationship'].includes(initialStudyTask??'')?initialStudyTask:undefined)
  const [selected, setSelected] = useState(() => studyTask??recommendedScenario(user.practice_goals))
  const [difficulty, setDifficulty] = useState(user.pilot_enrolled?'intermediate':'beginner')
  const [roleplay, setRoleplay] = useState<RolePlayState|null>(null)
  const [feedback, setFeedback] = useState<Feedback|null>(null)
  const [postToken,setPostToken]=useState<string|null>(null)
  const [mode, setMode] = useState<WorkspaceMode>(initialRoleplay ? 'roleplay' : 'reflect')
  const [multimodalEnabled, setMultimodalEnabled] = useState(false)
  const [modelStatus, setModelStatus] = useState('unavailable')
  const microphoneEnabled = localStorage.getItem('affectlab_microphone_enabled') !== 'false'
  const [transcriptionAvailable, setTranscriptionAvailable] = useState(false)
  const [transcriptionStatus, setTranscriptionStatus] = useState<'idle'|'transcribing'|'review'|'error'>('idle')
  const [voiceSample, storeVoiceSample] = useState<VoiceSample|null>(null)
  const [multimodal, setMultimodal] = useState<MultimodalAffect|null>(null)
  const [voiceNotice, setVoiceNotice] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    void Promise.all([api.listSessions(), api.scenarios(), api.modelInfo()]).then(async ([history, choices, models]) => {
      if (!active) return
      setMultimodalEnabled(models.trained_model); setModelStatus(models.multimodal_status); setTranscriptionAvailable(models.transcription_available); setScenarios(choices); setSessions(history)
      if (initialSessionId) load(await api.getSession(initialSessionId))
      else { const session = await api.createSession(); if (!active) return; setSessionId(session.session_id); setEmotion(session.emotion_state); setSessions(await api.listSessions()) }
    }).catch(() => active && setError('Could not load your sessions.'))
    return () => { active = false }
  }, [initialSessionId])
  useEffect(() => { endRef.current?.scrollIntoView({behavior:'smooth'}) }, [turns])

  const activeScenario = roleplay?.scenario ?? scenarios.find(item => item.id === (roleplay?.scenario_id ?? selected))
  const roleplayActive = Boolean(roleplay && ['active','paused'].includes(roleplay.status))
  const inRoleplay = mode === 'roleplay' && roleplayActive
  const sendingBlocked = busy || !sessionId || transcriptionStatus === 'transcribing' || (inRoleplay && roleplay?.status === 'paused')

  function load(session: SessionResponse) {
    setSessionId(session.session_id); setSessionTitle(session.title); setTurns(session.turns); setEmotion(session.emotion_state); setRoleplay(session.roleplay); setFeedback(session.feedback); setPostToken(session.post_questionnaire_token??null)
    setMode(session.feedback ? 'feedback' : session.roleplay && ['active','paused'].includes(session.roleplay.status) ? 'roleplay' : 'reflect')
    storeVoiceSample(null); setTranscriptionStatus('idle'); setMultimodal(null); setVoiceNotice('')
  }
  async function setVoiceSample(sample: VoiceSample | null) {
    storeVoiceSample(sample); setVoiceNotice('')
    if (!sample) { setTranscriptionStatus('idle'); return }
    if (!transcriptionAvailable) { setTranscriptionStatus('error'); setVoiceNotice('Automatic transcription is unavailable. Type what you said before sending.'); return }
    setTranscriptionStatus('transcribing'); setVoiceNotice('Transcribing your recording…')
    try { const result = await api.transcribe(sample.wavBase64); setMessage(result.text); setTranscriptionStatus('review'); setVoiceNotice('Transcript ready—review or edit it before sending.') }
    catch (caught) { setTranscriptionStatus('error'); setVoiceNotice(caught instanceof Error ? `${caught.message} You can type the transcript manually.` : 'Transcription failed. You can type the transcript manually.') }
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!sessionId || !message.trim() || sendingBlocked) return
    const content = message.trim(), audio = voiceSample
    setBusy(true); setError(''); setVoiceNotice('')
    if (audio && multimodalEnabled) try { if (modelStatus !== 'ready') setVoiceNotice('Loading the trained models for the first voice analysis...'); setMultimodal(await api.multimodalAffect(sessionId, content, audio.wavBase64)); setModelStatus('ready'); setVoiceNotice('Voice and text were analysed together. The recording was not stored.') } catch { setMultimodal(null); setVoiceNotice('Voice analysis was unavailable; your message continued with text analysis only.') }
    try {
      const response = await api.sendMessage(sessionId, content)
      // Keep the draft until the server confirms the exchange. Failed sends must
      // never appear in the transcript as successfully delivered messages.
      setTurns(current => [...current, {id:crypto.randomUUID(), role:'user', content, created_at:new Date().toISOString()}, response.turn])
      setMessage(''); storeVoiceSample(null); setTranscriptionStatus('idle')
      setEmotion(response.decision.emotion_state); setRoleplay(response.roleplay); setFeedback(response.feedback); setPostToken(response.post_questionnaire_token??null)
      if (sessionTitle === 'New reflection') setSessionTitle(content.length > 57 ? `${content.slice(0,57).trim()}...` : content)
      if (response.feedback && mode !== 'reflect') setMode('feedback')
      notifyStudyProgress()
    } catch (caught) {
      setError(`${caught instanceof Error ? caught.message : 'Message could not be sent'}. Your draft is kept below. You can edit it and try sending again.`)
    } finally { setBusy(false) }
  }
  async function continueStudy(task:StudyTask){
    setError('');setBusy(true)
    try{
      if(task.session_id){load(await api.getSession(task.session_id));history.replaceState({},'',`/practice?session=${task.session_id}`)}
      else {setStudyTask(task.scenario_id);setSelected(task.scenario_id);setDifficulty('intermediate');setRoleplay(null);setFeedback(null);setPostToken(null);setMode('roleplay')}
    }catch(caught){setError(caught instanceof Error?caught.message:'The study task could not be opened.')}
    finally{setBusy(false)}
  }
  async function start(ratings: {confidence:number;anxiety:number}|null) {
    if (!sessionId) return; setBusy(true); setError('')
    try { const response = await api.startRoleplay(sessionId, selected, difficulty, ratings); setSessionId(response.session_id); history.replaceState({}, '', `/practice?session=${response.session_id}`); setEmotion(response.emotion_state); setSessionTitle(response.scenario.title); setTurns([response.opening_turn]); setRoleplay(response.state); setFeedback(null); setMultimodal(null); storeVoiceSample(null); setMessage(''); setTranscriptionStatus('idle'); setMode('roleplay'); try { setSessions(await api.listSessions()) } catch { setError('The rehearsal started, but the saved-session list could not be refreshed.') } notifyStudyProgress() } catch(caught) { setError(caught instanceof Error?caught.message:'The rehearsal could not be started.') } finally { setBusy(false) }
  }
  async function action(name: string, nextMode: WorkspaceMode = 'roleplay') { if (!sessionId) return; setBusy(true); setError(''); try { const session = await api.roleplayAction(sessionId, name); load(session); setMode(session.feedback ? 'feedback' : nextMode); notifyStudyProgress() } catch(caught) { setError(caught instanceof Error?caught.message:'The role-play could not be updated.') } finally { setBusy(false) } }
  async function rewind() { if (!sessionId) return; setBusy(true); setError(''); try { const result=await api.rewindRoleplay(sessionId); load(result.session); setMessage(result.removed_message); setMode('roleplay') } catch(caught) { setError(caught instanceof Error?caught.message:'The last turn could not be restored.') } finally { setBusy(false) } }
  async function fresh() { if (sessionId) await api.deleteSession(sessionId); const session = await api.createSession(); setSessionId(session.session_id); setSessionTitle('New reflection'); setTurns([]); setEmotion(session.emotion_state); setRoleplay(null); setFeedback(null); setMode('reflect'); storeVoiceSample(null); setTranscriptionStatus('idle'); setMultimodal(null); setSessions(await api.listSessions()) }
  function retry() { setPostToken(null); setSelected(roleplay?.scenario_id ?? selected); setDifficulty(roleplay?.difficulty_level ?? difficulty); setFeedback(null); setRoleplay(null); setMode('roleplay') }

  const composer = <><VoiceCapture enabled={(transcriptionAvailable || multimodalEnabled) && microphoneEnabled} disabled={busy || transcriptionStatus === 'transcribing'} sample={voiceSample} onChange={setVoiceSample}/><form onSubmit={submit}><textarea readOnly={busy} value={message} onChange={event => setMessage(event.target.value)} placeholder={transcriptionStatus === 'transcribing' ? 'Transcribing your recording…' : transcriptionStatus === 'review' ? 'Review or edit the transcript before sending…' : inRoleplay ? `Respond to your ${activeScenario?.character ?? 'practice partner'}…` : 'Type a message or add your voice…'} rows={2}/><button className="send" disabled={!message.trim() || sendingBlocked} aria-label="Send message">↑</button></form><p className="privacy">Session text is retained locally for up to 30 days. Optional audio may be sent to OpenAI for transcription, processed in memory, and is not stored by AffectLab.</p></>

  return <main className="shell" aria-busy={busy}>
    <header><button className="brand-link" onClick={onDashboard}><span className="brand-mark">A</span><span className="brand">AffectLab</span></button><div className="header-actions"><button className="text-button" onClick={onDashboard}>Dashboard</button><select disabled={busy} value={sessionId} aria-label="Saved session" onChange={async event => load(await api.getSession(event.target.value))}>{sessions.map(session => <option key={session.session_id} value={session.session_id}>{session.title} · {session.turn_count} turns</option>)}</select><span>{user.preferred_name || user.first_name || user.email}</span><button className="text-button" onClick={onSettings}>Settings</button><button className="text-button" onClick={async () => { await api.logout(); onLogout() }}>Sign out</button></div></header>
    <div className="workspace-title"><span>{sessionTitle}</span><button onClick={async()=>{const next=prompt('Rename this session',sessionTitle)?.trim();if(!next||!sessionId)return;const updated=await api.renameSession(sessionId,next);setSessionTitle(updated.title);setSessions(await api.listSessions())}}>Rename</button></div>
    <section className="intro"><p className="eyebrow">Reflect · Reframe · Rehearse</p><h1>{mode === 'roleplay' ? 'Practise the conversation.' : mode === 'feedback' ? 'Review your rehearsal.' : 'A calmer place to prepare.'}</h1><p>{mode === 'roleplay' ? 'Try the words, adjust your approach, and finish whenever you are ready.' : mode === 'feedback' ? 'Use observable evidence to decide what to keep and what to try next.' : 'Share what is happening and explore the conversation at your pace.'}</p></section>
    {mode === 'reflect' && user.practice_goals.length > 0 && <section className="practice-focus"><div><p className="eyebrow">Your practice focus</p><strong>{user.practice_goals.map(goalLabel).join(' · ')}</strong></div><button onClick={() => { setSelected(recommendedScenario(user.practice_goals)); setMode('roleplay') }}>Try a recommended rehearsal</button></section>}
    {user.pilot_enrolled&&<StudyChecklist onContinue={continueStudy} disabled={busy||!sessionId} currentSessionId={sessionId} ratingsOpen={mode==='feedback'&&Boolean(postToken)}/>}
    <ModeTabs disabled={busy} mode={mode} roleplay={roleplay} onChange={next => { if(next!=='feedback')setPostToken(null); if (roleplayActive && next === 'reflect' && !confirm('Pause the active role-play and return to reflection?')) return; if (roleplayActive && next === 'reflect' && roleplay?.status === 'active') { void action('pause', 'reflect'); return } setMode(next) }}/>
    {error && <p className="error" role="alert">{error}</p>}
    {mode === 'feedback' && feedback ? <FeedbackScreen scenario={activeScenario} feedback={feedback} state={roleplay} postToken={postToken} onRetry={retry} onRewind={()=>void rewind()} onConversation={() => {setPostToken(null);setMode('reflect')}}/> : mode === 'roleplay' && !roleplayActive ? <ScenarioSetup key={studyTask??'practice'} studyTask={studyTask} onFreePractice={()=>setStudyTask(undefined)} scenarios={scenarios} selected={selected} difficulty={difficulty} busy={busy||!sessionId} onScenario={setSelected} onDifficulty={setDifficulty} onStart={start} onScenarios={setScenarios}/> : <div className="workspace"><section className={`chat-card ${inRoleplay ? 'roleplay-chat' : ''}`}>{inRoleplay && roleplay && <ActiveRolePlayHeader scenario={activeScenario} state={roleplay} busy={busy} onAction={action} onRewind={()=>void rewind()}/>}<div className="notice"><strong>{inRoleplay ? 'Role-play in progress' : 'Research prototype'}</strong><span>{inRoleplay ? `The assistant is responding as your ${activeScenario?.character ?? 'practice partner'}.` : 'Not a therapist or medical service. In an emergency, contact local emergency services.'}</span></div>{mode==='reflect'&&roleplay?.status==='paused'&&<p className="voice-notice" role="status">Your rehearsal is paused. You can reflect here, then return to Active role-play to resume.</p>}<div className="messages" aria-live="polite">{turns.length === 0 && <div className="empty"><span>✦</span><h2>What conversation is on your mind?</h2><p>Your affect estimate is uncertain and is never a diagnosis.</p></div>}{turns.map(turn => <div key={turn.id} className={`message ${turn.role}`}><span>{turn.content}</span></div>)}{busy && <div className="message assistant"><span>Thinking…</span></div>}<div ref={endRef}/></div>{voiceNotice && <p className="voice-notice" role="status">{voiceNotice}</p>}{composer}</section><aside><EmotionPanel state={emotion}/>{multimodal && <MultimodalPanel result={multimodal}/>}<button className="new-session" disabled={busy} onClick={fresh}>Delete & start fresh</button></aside></div>}
  </main>
}
