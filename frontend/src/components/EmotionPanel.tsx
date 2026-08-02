import type { EmotionState } from '../types/api'

export function EmotionPanel({ state }: { state: EmotionState | null }) {
  return (
    <aside className="emotion-panel" aria-label="Estimated emotional state">
      <p className="eyebrow">Current estimate</p>
      <h2>{state?.dominant_emotion ?? 'Listening'}</h2>
      <div className="metric"><span>Valence</span><strong>{state?.valence.toFixed(2) ?? '—'}</strong></div>
      <div className="metric"><span>Arousal</span><strong>{state?.arousal.toFixed(2) ?? '—'}</strong></div>
      <div className="metric"><span>Confidence</span><strong>{state ? `${Math.round(state.confidence * 100)}%` : '—'}</strong></div>
      <p className="uncertainty">These are uncertain signals, not facts or diagnoses.</p>
    </aside>
  )
}

