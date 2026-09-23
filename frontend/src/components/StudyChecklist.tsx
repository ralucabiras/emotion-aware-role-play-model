import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { openStudyTask } from '../services/studyProgress'
import type { StudyProgress, StudyTask } from '../types/api'

const labels = {not_started:'Not started',in_progress:'In progress',awaiting_ratings:'Post-ratings pending',complete:'Complete',incomplete:'Attempt recorded - incomplete'}

export function StudyChecklist({onContinue=openStudyTask,disabled=false,currentSessionId,ratingsOpen=false}:{onContinue?:(task:StudyTask)=>void;disabled?:boolean;currentSessionId?:string;ratingsOpen?:boolean}) {
  const [progress,setProgress]=useState<StudyProgress>(),[error,setError]=useState(''),[revision,setRevision]=useState(0)
  useEffect(()=>{let active=true;void api.studyProgress().then(value=>{if(active){setProgress(value);setError('')}}).catch(()=>active&&setError('Your study progress could not be loaded.'));return()=>{active=false}},[revision])
  useEffect(()=>{const refresh=()=>setRevision(value=>value+1);window.addEventListener('study-progress-updated',refresh);return()=>window.removeEventListener('study-progress-updated',refresh)},[])
  const next=progress?.tasks.find(task=>task.scenario_id===progress.next_task_id)
  const ratingHere=next?.status==='awaiting_ratings'&&next.session_id===currentSessionId&&ratingsOpen
  return <section className="study-checklist" aria-label="Your study checklist"><p className="eyebrow">Pilot study</p><h2>Your three study tasks</h2><p>Follow the order below at intermediate difficulty. Answer or skip the ratings before and after each task. You may pause or stop at any time.</p>{progress&&<><p role="status">{progress.completed_tasks} of 3 tasks complete with post-ratings</p><ol>{progress.tasks.map(task=><li key={task.scenario_id} aria-current={next?.scenario_id===task.scenario_id?'step':undefined}><strong>{task.title}</strong><span>{labels[task.status]}</span></li>)}</ol>{!progress.available?<p>Study data collection is currently closed. Your saved progress is shown above.</p>:ratingHere?<p>Answer or skip the post-ratings below before moving to the next task.</p>:next?<button className="primary" disabled={disabled||Boolean(error)} onClick={()=>onContinue(next)}>{next.status==='in_progress'?'Resume':next.status==='awaiting_ratings'?'Review':'Next task:'} {next.title}</button>:<p>Thank you - you have reached the end of the study tasks.{progress.completed_tasks<3?' Some attempts are incomplete; no missing ratings have been filled in.':''}</p>}<small>Other scenarios and difficulty levels are additional practice and do not count toward this checklist.</small></>}{!progress&&!error&&<p role="status">Loading study progress...</p>}{error&&<p role="alert">{error} <button className="text-button" onClick={()=>setRevision(value=>value+1)}>Try again</button></p>}</section>
}
