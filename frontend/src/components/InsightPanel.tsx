import type { ChatResponse } from '../types/api'

export function InsightPanel({ decision }: { decision: ChatResponse['decision'] | null }) {
  if (!decision) return null
  const cognition = decision.cognitive_assessment
  return <section className="insight-panel" aria-label="Agent decision explanation">
    <p className="eyebrow">Why this response</p>
    <div className="metric"><span>Strategy</span><strong>{decision.strategy.replaceAll('_', ' ')}</strong></div>
    <div className="metric"><span>Intent</span><strong>{cognition.intent.replaceAll('_', ' ')}</strong></div>
    {cognition.possible_distortion && <p className="tentative">Tentative pattern: {cognition.possible_distortion}. This may be wrong.</p>}
    {cognition.possible_cause && <p className="tentative">Possible context: {cognition.possible_cause}</p>}
    <ul>{decision.decision_reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>
    <p className="uncertainty">Baseline: {decision.analyzer_version}. Research signals, not clinical conclusions.</p>
  </section>
}
