import { useEffect, useState } from 'react'
import type { BranchComparison as Comparison, BranchContinuation } from '../types/api'
import { api } from '../services/api'

const words=(value:string)=>value.replaceAll('_',' ')
const observable={concrete_request:'concrete request',excessive_apology:'repeated apology',maintained_boundary:'boundary language',blame_language:'blaming language',specific_detail:'specific detail',i_statement:'I-statement'} as const

function Continuation({value,label}:{value:BranchContinuation;label:string}) {
  return <section className="comparison-continuation" aria-label={label}><h2>{label}</h2><p>Status: {words(value.status)}. Outcome: {value.outcome?words(value.outcome):'No recorded outcome'}.</p>{value.completion_reason&&<p>Ending: {words(value.completion_reason)}.</p>}{value.agreement&&<p>Recorded agreement: {value.agreement}</p>}{!value.turns.length&&<p>No new response yet. Return to Active role-play to try your alternative.</p>}
    {value.turns.map(turn=>{
      const decision=value.decisions.find(item=>item.user_turn_id===turn.id)
      const evidence=value.evidence.find(item=>item.conversation_turn_id===turn.id)
      return <article key={turn.id} className="replay-turn"><strong>{turn.role==='user'?'You':'Practice partner'}</strong><p>{turn.content}</p>{evidence&&<p>Recorded language: {[...Object.entries(observable).filter(([key])=>evidence[key as keyof typeof observable]).map(([,label])=>label),...(evidence.language_features??[]).map(words)].join(', ')||'No scenario language features recorded'}.</p>}{decision&&<><p>Stage: {decision.before.dialogue.stage_labels?.[decision.before.dialogue.stage]??words(decision.before.dialogue.stage)} → {decision.after.dialogue.stage_labels?.[decision.after.dialogue.stage]??words(decision.after.dialogue.stage)}</p><p>Action: {words(decision.action)}.</p></>}{turn.role==='assistant'&&<small>Generation: {turn.generation?.source??'unavailable'}{turn.strategy?` · Strategy: ${words(turn.strategy)}`:''}</small>}</article>
    })}
  </section>
}

export function BranchComparison({sessionId,onOriginal}:{sessionId:string;onOriginal:(id:string)=>void}) {
  const [comparison,setComparison]=useState<Comparison|null>(null)
  const [error,setError]=useState('')
  const [retry,setRetry]=useState(0)
  useEffect(()=>{let active=true;api.compareBranch(sessionId).then(value=>{if(active){setComparison(value);setError('')}}).catch(caught=>{if(active)setError(caught instanceof Error?caught.message:'Comparison could not be loaded.')});return()=>{active=false}},[sessionId,retry])
  if(error)return <section><p role="alert">{error}</p><button onClick={()=>{setError('');setRetry(value=>value+1)}}>Retry comparison</button></section>
  if(!comparison)return <p role="status">Loading saved alternatives…</p>
  return <section className="branch-comparison" aria-label="Branch comparison"><p>Compare recorded language and conversation outcomes. Neither wording guarantees a real-world result. The alternative uses deterministic responses; differences may also reflect the original’s generation settings and pacing choices.</p><details><summary>Shared context ({comparison.shared_context.length} messages)</summary>{comparison.shared_context.map(turn=><article key={turn.id} className="replay-turn"><strong>{turn.role==='user'?'You':'Practice partner'} · Shared context</strong><p>{turn.content}</p></article>)}</details><p>Shared messages are shown once and are not counted as new activity. Compare contains only the original and this alternative.</p>
    {comparison.original&&<button onClick={()=>onOriginal(comparison.original!.session_id)}>Open original rehearsal</button>}
    <div className="comparison-columns">{comparison.original?<Continuation value={comparison.original} label="Original continuation"/>:<section><h2>Original unavailable</h2><p role="status">{comparison.unavailable_reason}</p></section>}<Continuation value={comparison.alternative} label="Alternative continuation"/></div>
  </section>
}
