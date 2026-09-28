import { useState } from 'react'
import type { BranchLineage, ConversationTurn, DialogueSnapshot, Feedback, RolePlayState } from '../types/api'
import { rehearsalReplay } from '../services/replay'

const words=(value:string)=>value.replaceAll('_',' ')
const stage=(snapshot:DialogueSnapshot)=>snapshot.dialogue.stage_labels?.[snapshot.dialogue.stage]??words(snapshot.dialogue.stage)
const featureNames={concrete_request:'Concrete request',excessive_apology:'Repeated apology',maintained_boundary:'Boundary language',blame_language:'Blaming language',specific_detail:'Specific detail',i_statement:'I-statement'} as const

export function ConversationReplay({turns,state,feedback,branch,onBranch,onFresh,busy=false}:{turns:ConversationTurn[];state:RolePlayState;feedback:Feedback|null;branch?:BranchLineage|null;onBranch?:(turnId:string)=>void;onFresh?:()=>void;busy?:boolean}) {
  const replay=rehearsalReplay(turns,state,branch?.copied_turn_ids)
  const exchanges=replay.turns.filter(turn=>turn.role==='user')
  const [selected,setSelected]=useState(exchanges[0]?.id??'')
  const [highlight,setHighlight]=useState('')
  const decision=replay.decisions.find(item=>item.user_turn_id===selected)
  const evidence=(state.evidence??[]).find(item=>item.conversation_turn_id===selected)
  const following=replay.turns[replay.turns.findIndex(turn=>turn.id===selected)+1]
  const features=evidence ? [...new Set([...Object.entries(featureNames).filter(([key])=>evidence[key as keyof typeof featureNames]).map(([,label])=>label),...(evidence.language_features??[]).map(words)])] : []
  const reply=decision ? replay.turns.find(turn=>turn.id===decision.assistant_turn_id) : following?.role==='assistant'?following:undefined
  const affect=decision?.affect_decision??reply?.affect_decision
  const prediction=affect?.prediction
  const visibleIds=new Set(replay.turns.map(turn=>turn.id))
  function navigate(id:string) {
    setHighlight(id)
    const element=document.getElementById(`replay-${id}`)
    element?.focus({preventScroll:true});element?.scrollIntoView({block:'center',behavior:'smooth'})
  }
  function evidenceLink(id:string,label:string) {
    return visibleIds.has(id) ? <button className="text-button" onClick={()=>navigate(id)}>{label}</button> : <span>{label}: source unavailable</span>
  }
  return <section className="conversation-replay" aria-label="Conversation replay">
    {onBranch && <div className="branch-controls">{decision && ['workload-v2','scenario-dialogue-v3'].includes(decision.policy_version) && decision.before.status==='active' && !branch?.copied_turn_ids.includes(selected) && !state.required_task_id && state.attempt_purpose!=='required' ? <><button disabled={busy} onClick={()=>onBranch(selected)}>Try a different response here</button><p>This creates a separate attempt from just before your selected reply, with deterministic character responses.</p></> : <><p>This turn cannot be branched from its saved state. Shared context and legacy turns are preserved.</p><button disabled={busy} onClick={onFresh}>Start a fresh attempt</button></>}</div>}
    <p>Review the saved rehearsal. Nothing here regenerates responses or recalculates feedback. Later reflection and removed retries are excluded.</p>
    {!replay.boundaryKnown ? <p role="status">The rehearsal boundary is unavailable in this older record. A measured replay cannot be shown reliably. The full conversation remains available in Reflect.</p> : replay.turns.length===0 ? <p role="status">No saved rehearsal turns are available.</p> : <>
      <nav className="replay-timeline" aria-label="Rehearsal timeline"><ol>{exchanges.map((turn,index)=>{
        const recorded=replay.decisions.find(item=>item.user_turn_id===turn.id)
        return <li key={turn.id}><button aria-pressed={selected===turn.id} onClick={()=>{setSelected(turn.id);navigate(turn.id)}}>Turn {index+1}{recorded ? ` · ${stage(recorded.after)}` : ' · Details unavailable'}</button></li>
      })}</ol>{exchanges.length===0&&<p>No user exchanges were recorded.</p>}</nav>
      <div className="replay-layout"><section aria-label="Saved rehearsal transcript" className="replay-transcript"><h2>Transcript</h2>{replay.turns.map(turn=><article id={`replay-${turn.id}`} tabIndex={-1} key={turn.id} className={`replay-turn ${turn.id===highlight?'evidence-highlight':''} ${turn.id===selected||turn.id===reply?.id?'selected-exchange':''}`}><strong>{turn.role==='user'?'You':'Practice partner'}{branch?.copied_turn_ids.includes(turn.id)?' ? Shared context':''}</strong><p>{turn.content}</p></article>)}</section>
      <aside aria-label="Recorded turn details" className="replay-details">
        <section><h2>Observable language</h2><p>Recorded language features, not a measure of personal competence.</p>{evidence ? <>{features.length ? <ul>{features.map(label=><li key={label}>{label}</li>)}</ul> : <p>No positive language features recorded.</p>}{evidenceLink(selected,'View this utterance')}</> : <p>No language evidence was recorded for this turn.</p>}</section>
        <section><h2>Controller action</h2>{decision ? <><p><strong>{words(decision.action)}</strong></p><p>{stage(decision.before)} → {stage(decision.after)}</p>{decision.after.dialogue.objection&&<p>Recorded objection: {words(decision.after.dialogue.objection)}</p>}<p>Response strategy: {reply?.strategy?words(reply.strategy):'unavailable'}</p><p>Recorded reasons: {decision.reason_codes.map(words).join('; ')||'unavailable'}.</p><p>Evidence available to this decision (may include earlier turns):</p><ul>{decision.evidence_turn_ids.map(id=><li key={id}>{evidenceLink(id,`View evidence ${exchanges.findIndex(turn=>turn.id===id)+1||'source'}`)}</li>)}</ul>{decision.after.dialogue.final_agreement&&<p>Recorded agreement: {decision.after.dialogue.final_agreement}</p>}</> : <p>Decision details unavailable. This session has no saved controller decision for this exchange.</p>}</section>
        <section><h2>Estimated affect and pacing</h2>{prediction ? <><p>{prediction.label}: {Math.round(prediction.confidence*100)}% model confidence ({prediction.confidence_level}).</p><p>{prediction.modalities_agree?'Text and voice estimates agree.':'Text and voice estimates disagree.'}</p>{prediction.confidence_level==='low'&&<p>Uncertain estimate; do not interpret this as distress.</p>}<dl>{Object.entries(prediction.distribution).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{Math.round(value*100)}%</dd></div>)}</dl><p>{prediction.disclaimer}</p></> : <p>No saved voice prediction for this exchange. This is a gap, not a neutral emotion estimate.</p>}{affect ? <><p>Recorded pacing: {words(affect.action)}. Preference: {words(affect.preference)}. Adaptation {affect.adaptation_enabled?'enabled':'disabled'}.</p><p>{words(affect.reason)}{affect.fallback_reason?` · ${words(affect.fallback_reason)}`:''}</p><small>Pacing is an application design choice, not a proven psychological benefit.</small></> : <p>No adaptation details recorded.</p>}</section>
        {decision&&<details><summary>Technical details</summary><p>Scenario: {decision.scenario_version}. Dialogue policy: {decision.policy_version}. Scoring: {decision.scoring_version}.</p><p>Generation: {decision.generation.source}; model: {decision.generation.model??'none'}; latency: {decision.generation.latency_ms??'unavailable'} ms; fallback: {decision.generation.fallback_reason??'none'}.</p><p>Linked turns: {decision.user_turn_id} / {decision.assistant_turn_id}</p>{affect&&<><p>Affect policy: {affect.policy_version}; source: {affect.source}; analysis: {affect.analysis_ms} ms. Audio submitted: {String(affect.audio_submitted)}; prediction available: {String(affect.audio_available)}.</p>{prediction&&<><p>Model: {prediction.model_version}; threshold: {prediction.low_confidence_threshold}; inference: {prediction.latency_ms} ms; queue: {prediction.queue_ms} ms.</p><p>Text: {prediction.text_label} ({Math.round(prediction.text_confidence*100)}%). Voice: {prediction.audio_label} ({Math.round(prediction.audio_confidence*100)}%).</p><pre>{JSON.stringify({text:prediction.text_distribution,voice:prediction.audio_distribution},null,2)}</pre></>}</>}<p>Stored state and reason codes:</p><pre>{JSON.stringify({before:decision.before,after:decision.after,reasons:decision.reason_codes},null,2)}</pre></details>}
      </aside></div>
      <section className="replay-feedback"><h2>Feedback evidence</h2>{feedback?.evidence_scope==='continuation'&&<p>These language scores use only new responses in this alternative. The outcome also depends on shared context.</p>}{(state.evidence??[]).filter(item=>!item.conversation_turn_id).map(item=><p key={item.turn}>Legacy evidence {item.turn} (source unavailable): {[...Object.entries(featureNames).filter(([key])=>item[key as keyof typeof featureNames]).map(([,label])=>label),...(item.language_features??[]).map(words)].join(", ")||"No positive language features recorded"}.</p>)}{feedback ? <>{feedback.observed.map((text,index)=><p key={index}>{text}</p>)}{feedback.metrics.map(metric=><div key={metric.name}><h3>{words(metric.name)} · {Math.round(metric.score*100)}%</h3><ul>{(metric.evidence_turns??[]).map(number=>{const source=state.evidence?.find(item=>item.turn===number)?.conversation_turn_id;return <li key={number}>{source?evidenceLink(source,`View feedback evidence ${number}`):`Evidence ${number}: source unavailable`}</li>})}</ul>{!metric.evidence_turns?.length&&<p>No evidence references recorded.</p>}</div>)}</> : <p>No saved feedback is available for this rehearsal.</p>}</section>
    </>}
  </section>
}
