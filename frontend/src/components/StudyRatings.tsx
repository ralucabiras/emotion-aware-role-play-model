import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type { StudyQuestionnaire } from '../types/api'

export function RatingInput({label,value,onChange}:{label:string;value:number|null;onChange:(value:number|null)=>void}) {
  return <label>{label}<select value={value??''} onChange={event=>onChange(event.target.value?Number(event.target.value):null)}><option value="">Choose a rating</option>{[1,2,3,4,5,6,7].map(value=><option key={value} value={value}>{value} / 7</option>)}</select></label>
}

export function PostRatings({sessionId,token}:{sessionId:string;token?:string|null}) {
  const [saved,setSaved]=useState<StudyQuestionnaire>(),[skipped,setSkipped]=useState(false),[loading,setLoading]=useState(true),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const [confidence,setConfidence]=useState<number|null>(null),[realism,setRealism]=useState<number|null>(null),[usefulness,setUsefulness]=useState<number|null>(null)
  const generation=useRef(0)
  useEffect(()=>{
    let active=true
    const current=++generation.current
    const close=()=>{void api.closePostQuestionnaire(sessionId).catch(()=>undefined)}
    // Ignore StrictMode's simulated unmount, but close on a real task-screen exit.
    const closeIfUnmounted=()=>{if(generation.current===current)close()}
    void api.getSession(sessionId).then(session=>{if(active){setSaved(session.questionnaires?.post);setSkipped(Boolean(session.questionnaire_skips?.post));setLoading(false)}}).catch(()=>{if(active){setError('Saved ratings could not be loaded. Reopen this session to review them.');setLoading(false)}})
    if(!token)close()
    window.addEventListener('pagehide',close)
    return()=>{active=false;window.removeEventListener('pagehide',close);queueMicrotask(closeIfUnmounted)}
  },[sessionId,token])
  async function submit(skip=false){
    if(!token)return
    setBusy(true);setError('')
    try{
      const result=await api.submitQuestionnaire(sessionId,'post',skip?{skipped:true,post_token:token}:{confidence:confidence!,realism:realism!,usefulness:usefulness!,post_token:token})
      if(result.questionnaire)setSaved(result.questionnaire);else setSkipped(true)
    }catch(caught){setError(caught instanceof Error?caught.message:'Ratings could not be saved. Please try again.')}
    finally{setBusy(false)}
  }
  return <section className="post-study"><p className="eyebrow">Optional research measure</p><h3>How was this rehearsal?</h3>{loading?<p role="status">Loading saved ratings...</p>:saved?<><p role="status">Your original ratings are saved and cannot be changed.</p><dl><dt>Confidence now</dt><dd>{saved.confidence??'Not answered'} / 7</dd><dt>Scenario realism</dt><dd>{saved.realism??'Not answered'} / 7</dd><dt>Feedback usefulness</dt><dd>{saved.usefulness??'Not answered'} / 7</dd></dl></>:skipped?<p role="status">You skipped these ratings. No answers were recorded.</p>:!token?<p>Ratings are closed after leaving the task screen. No retrospective answers can be added.</p>:<><p>Choose every rating, or explicitly skip. Leaving this screen closes the questionnaire.</p><div className="study-ratings"><RatingInput label="Confidence now" value={confidence} onChange={setConfidence}/><RatingInput label="Scenario realism" value={realism} onChange={setRealism}/><RatingInput label="Feedback usefulness" value={usefulness} onChange={setUsefulness}/></div><button className="secondary" disabled={busy||confidence===null||realism===null||usefulness===null} onClick={()=>void submit()}>{busy?'Saving...':'Save research ratings'}</button><button className="text-button" disabled={busy} onClick={()=>void submit(true)}>Skip post-ratings</button></>}{error&&<p className="error" role="alert">{error}</p>}</section>
}
