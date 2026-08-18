import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../services/api'
import type { ConversationTurn, EmotionState, Feedback, MultimodalAffect, RolePlayState, Scenario, SessionResponse, UserProfile } from '../types/api'
import { EmotionPanel } from './EmotionPanel'
import { ActiveRolePlayHeader, FeedbackScreen, ModeTabs, ScenarioSetup } from './RolePlayWorkspace'
import type { WorkspaceMode } from './RolePlayWorkspace'
import { VoiceCapture } from './VoiceCapture'
import type { VoiceSample } from './VoiceCapture'

function MultimodalPanel({result}: {result: MultimodalAffect}) {
  const sorted = Object.entries(result.distribution).sort((left, right) => right[1] - left[1])
  const low = result.confidence_level === 'low'
  return <section className={`multimodal-panel confidence-${result.confidence_level}`} aria-label="Voice and text affect estimate"><p className="eyebrow">Voice + text estimate</p><h2>{low ? 'Uncertain estimate' : result.label}</h2><strong>{Math.round(result.confidence * 100)}% confidence · {result.confidence_level}</strong>{low && <p className="confidence-warning">No single label reached the display threshold. Treat the leading possibilities as tentative.</p>}<div className="modality-comparison"><article><span>Text signal</span><strong>{result.text_label}</strong><small>{Math.round(result.text_confidence * 100)}%</small></article><article><span>Voice signal</span><strong>{result.audio_label}</strong><small>{Math.round(result.audio_confidence * 100)}%</small></article></div><p className={`agreement ${result.modalities_agree ? 'agree' : 'disagree'}`}>{result.modalities_agree ? 'Text and voice point to the same leading label.' : 'Text and voice point to different leading labels; the fused result is less straightforward.'}</p><div className="distribution">{sorted.map(([label, probability]) => <div key={label}><span>{label}</span><div><i style={{width:`${probability * 100}%`}}/></div><small>{Math.round(probability * 100)}%</small></div>)}</div><p>{result.disclaimer} Audio was not stored. Inference took {(result.latency_ms / 1000).toFixed(1)}s{result.queue_ms > 50 ? ` after ${(result.queue_ms / 1000).toFixed(1)}s queued` : ''}.</p></section>
}

export function Dashboard({user, onLogout, onHome, onSettings}: {user: UserProfile; onLogout: () => void; onHome: () => void; onSettings: () => void}) {
  const [sessionId, setSessionId] = useState<string>()
  const [sessions, setSessions] = useState<{session_id:string;turn_count:number}[]>([])
  const [turns, setTurns] = useState<ConversationTurn[]>([])
  const [emotion, setEmotion] = useState<EmotionState|null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [selected, setSelected] = useState('workload')
  const [difficulty, setDifficulty] = useState('beginner')
  const [roleplay, setRoleplay] = useState<RolePlayState|null>(null)
  const [feedback, setFeedback] = useState<Feedback|null>(null)
  const [mode, setMode] = useState<WorkspaceMode>('reflect')
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
      if (history[0]) load(await api.getSession(history[0].session_id))
      else { const session = await api.createSession(); if (!active) return; setSessionId(session.session_id); setEmotion(session.emotion_state); setSessions([{session_id:session.session_id, turn_count:0}]) }
    }).catch(() => active && setError('Could not load your sessions.'))
    return () => { active = false }
  }, [])
  useEffect(() => { endRef.current?.scrollIntoView({behavior:'smooth'}) }, [turns])

  const activeScenario = scenarios.find(item => item.id === (roleplay?.scenario_id ?? selected))
  const roleplayActive = Boolean(roleplay && ['active','paused'].includes(roleplay.status))

  function load(session: SessionResponse) {
    setSessionId(session.session_id); setTurns(session.turns); setEmotion(session.emotion_state); setRoleplay(session.roleplay); setFeedback(session.feedback)
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
    event.preventDefault(); if (!sessionId || !message.trim() || busy || transcriptionStatus === 'transcribing') return
    const content = message.trim(), audio = voiceSample
    setMessage(''); storeVoiceSample(null); setTranscriptionStatus('idle'); setBusy(true); setError(''); setVoiceNotice('')
    setTurns(current => [...current, {id:crypto.randomUUID(), role:'user', content, created_at:new Date().toISOString()}])
    if (audio) try { if (modelStatus !== 'ready') setVoiceNotice('Loading the trained models for the first voice analysis…'); setMultimodal(await api.multimodalAffect(sessionId, content, audio.wavBase64)); setModelStatus('ready'); setVoiceNotice('Voice and text were analysed together. The recording was not stored.') } catch { setMultimodal(null); setVoiceNotice('Voice analysis was unavailable; your message continued with text analysis only.') }
    try { const response = await api.sendMessage(sessionId, content); setTurns(current => [...current, response.turn]); setEmotion(response.decision.emotion_state); setRoleplay(response.roleplay); setFeedback(response.feedback); if (response.feedback) setMode('feedback') }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Message failed') } finally { setBusy(false) }
  }
  async function start() {
    if (!sessionId) return; setBusy(true)
    try { const response = await api.startRoleplay(sessionId, selected, difficulty); setTurns(current => [...current, response.opening_turn]); setRoleplay(response.state); setFeedback(null); setMode('roleplay') } finally { setBusy(false) }
  }
  async function action(name: string, nextMode: WorkspaceMode = 'roleplay') { if (!sessionId) return; const session = await api.roleplayAction(sessionId, name); load(session); setMode(session.feedback ? 'feedback' : nextMode) }
  async function fresh() { if (sessionId) await api.deleteSession(sessionId); const session = await api.createSession(); setSessionId(session.session_id); setTurns([]); setEmotion(session.emotion_state); setRoleplay(null); setFeedback(null); setMode('reflect'); storeVoiceSample(null); setTranscriptionStatus('idle'); setMultimodal(null); setSessions(await api.listSessions()) }
  function retry() { setSelected(roleplay?.scenario_id ?? selected); setDifficulty(roleplay?.difficulty_level ?? difficulty); setFeedback(null); setRoleplay(null); setMode('roleplay') }

  const composer = <><VoiceCapture enabled={multimodalEnabled && microphoneEnabled} disabled={busy || transcriptionStatus === 'transcribing'} sample={voiceSample} onChange={setVoiceSample}/><form onSubmit={submit}><textarea value={message} onChange={event => setMessage(event.target.value)} placeholder={transcriptionStatus === 'transcribing' ? 'Transcribing your recording…' : transcriptionStatus === 'review' ? 'Review or edit the transcript before sending…' : roleplayActive ? `Respond to your ${activeScenario?.character ?? 'practice partner'}…` : 'Type a message or add your voice…'} rows={2}/><button className="send" disabled={!message.trim() || busy || transcriptionStatus === 'transcribing' || roleplay?.status === 'paused'} aria-label="Send message">↑</button></form><p className="privacy">Session text is retained locally for up to 30 days. Optional audio may be sent to OpenAI for transcription, processed in memory, and is not stored by AffectLab.</p></>

  return <main className="shell">
    <header><button className="brand-link" onClick={onHome}><span className="brand-mark">A</span><span className="brand">AffectLab</span></button><div className="header-actions"><select value={sessionId} aria-label="Saved session" onChange={async event => load(await api.getSession(event.target.value))}>{sessions.map((session, index) => <option key={session.session_id} value={session.session_id}>Session {sessions.length-index} · {session.turn_count} turns</option>)}</select><span>{user.preferred_name || user.first_name || user.email}</span><button className="text-button" onClick={onSettings}>Settings</button><button className="text-button" onClick={async () => { await api.logout(); onLogout() }}>Sign out</button></div></header>
    <section className="intro"><p className="eyebrow">Reflect · Reframe · Rehearse</p><h1>{mode === 'roleplay' ? 'Practise the conversation.' : mode === 'feedback' ? 'Review your rehearsal.' : 'A calmer place to prepare.'}</h1><p>{mode === 'roleplay' ? 'Try the words, adjust your approach, and finish whenever you are ready.' : mode === 'feedback' ? 'Use observable evidence to decide what to keep and what to try next.' : 'Share what is happening and explore the conversation at your pace.'}</p></section>
    <ModeTabs mode={mode} roleplay={roleplay} onChange={next => { if (roleplayActive && next === 'reflect' && !confirm('Pause the active role-play and return to reflection?')) return; if (roleplayActive && next === 'reflect' && roleplay?.status === 'active') { void action('pause', 'reflect'); return } setMode(next) }}/>
    {mode === 'feedback' && feedback ? <FeedbackScreen scenario={activeScenario} feedback={feedback} state={roleplay} onRetry={retry} onConversation={() => setMode('reflect')}/> : mode === 'roleplay' && !roleplayActive ? <ScenarioSetup scenarios={scenarios} selected={selected} difficulty={difficulty} busy={busy} onScenario={setSelected} onDifficulty={setDifficulty} onStart={start}/> : <div className="workspace"><section className={`chat-card ${roleplayActive ? 'roleplay-chat' : ''}`}>{roleplayActive && roleplay && <ActiveRolePlayHeader scenario={activeScenario} state={roleplay} busy={busy} onAction={action}/>}<div className="notice"><strong>{roleplayActive ? 'Role-play in progress' : 'Research prototype'}</strong><span>{roleplayActive ? `The assistant is responding as your ${activeScenario?.character ?? 'practice partner'}.` : 'Not a therapist or medical service. In an emergency, contact local emergency services.'}</span></div><div className="messages" aria-live="polite">{turns.length === 0 && <div className="empty"><span>✦</span><h2>What conversation is on your mind?</h2><p>Your affect estimate is uncertain and is never a diagnosis.</p></div>}{turns.map(turn => <div key={turn.id} className={`message ${turn.role}`}><span>{turn.content}</span></div>)}{busy && <div className="message assistant"><span>Thinking…</span></div>}<div ref={endRef}/></div>{error && <p className="error" role="alert">{error}</p>}{voiceNotice && <p className="voice-notice" role="status">{voiceNotice}</p>}{composer}</section><aside><EmotionPanel state={emotion}/>{multimodal && <MultimodalPanel result={multimodal}/>}<button className="new-session" onClick={fresh}>Delete & start fresh</button></aside></div>}
  </main>
}
