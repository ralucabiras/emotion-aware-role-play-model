import { FormEvent, useEffect, useRef, useState } from 'react'
import { EmotionPanel } from './components/EmotionPanel'
import { api } from './services/api'
import type { ConversationTurn, EmotionState } from './types/api'
import './styles.css'

export default function App() {
  const [sessionId, setSessionId] = useState<string>()
  const [turns, setTurns] = useState<ConversationTurn[]>([])
  const [emotion, setEmotion] = useState<EmotionState | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.createSession().then(({ session_id, emotion_state }) => {
      setSessionId(session_id); setEmotion(emotion_state)
    }).catch(() => setError('Could not connect to the AffectLab API.'))
  }, [])
  useEffect(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), [turns])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!sessionId || !message.trim() || busy) return
    const content = message.trim()
    setMessage(''); setBusy(true); setError('')
    setTurns((current) => [...current, { id: crypto.randomUUID(), role: 'user', content, created_at: new Date().toISOString() }])
    try {
      const result = await api.sendMessage(sessionId, content)
      setTurns((current) => [...current, result.turn]); setEmotion(result.decision.emotion_state)
    } catch { setError('The message could not be sent. Please try again.') }
    finally { setBusy(false) }
  }

  async function startRoleplay() {
    if (!sessionId || busy) return
    setBusy(true)
    try {
      const result = await api.startRoleplay(sessionId)
      setTurns((current) => [...current, result.opening_turn])
    } catch { setError('Could not start the role-play.') }
    finally { setBusy(false) }
  }

  async function clearSession() {
    if (sessionId) await api.deleteSession(sessionId)
    const next = await api.createSession()
    setSessionId(next.session_id); setEmotion(next.emotion_state); setTurns([]); setError('')
  }

  return (
    <main className="shell">
      <header><div><span className="brand-mark">A</span><span className="brand">AffectLab</span></div><button className="text-button" onClick={clearSession}>Delete session</button></header>
      <section className="intro">
        <p className="eyebrow">Reflect · Reframe · Rehearse</p>
        <h1>A calmer place to practise<br />difficult conversations.</h1>
        <p>Share what’s happening. AffectLab will reflect what it notices and help you prepare—at your pace.</p>
      </section>
      <div className="workspace">
        <section className="chat-card">
          <div className="notice"><strong>Research prototype</strong><span>AffectLab is not a therapist or medical service. In an emergency, contact local emergency services.</span></div>
          <div className="messages" aria-live="polite">
            {turns.length === 0 && <div className="empty"><span>✦</span><h2>What conversation is on your mind?</h2><p>For example: “I need to tell my manager I’m overloaded, but I’m worried how they’ll react.”</p></div>}
            {turns.map((turn) => <div key={turn.id} className={`message ${turn.role}`}><span>{turn.content}</span></div>)}
            {busy && <div className="message assistant"><span>Thinking…</span></div>}
            <div ref={endRef} />
          </div>
          {error && <p className="error">{error}</p>}
          <div className="actions"><button onClick={startRoleplay} disabled={!sessionId || busy}>Practise workload conversation</button></div>
          <form onSubmit={submit}><textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Describe the situation or how you’re feeling…" rows={2} /><button className="send" disabled={!sessionId || busy || !message.trim()} aria-label="Send message">↑</button></form>
          <p className="privacy">Text is held only in this running server session. Raw audio and video are not collected.</p>
        </section>
        <EmotionPanel state={emotion} />
      </div>
    </main>
  )
}
