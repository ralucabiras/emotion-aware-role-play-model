import type { StudyTask } from '../types/api'

export function notifyStudyProgress(){window.dispatchEvent(new Event('study-progress-updated'))}

export function openStudyTask(task:StudyTask){
  const query=task.session_id?`session=${encodeURIComponent(task.session_id)}`:`mode=roleplay&study=${encodeURIComponent(task.scenario_id)}`
  history.pushState({},'',`/practice?${query}`)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

