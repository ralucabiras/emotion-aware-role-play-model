import type { StudyProgress, AudioTranscription, ChatResponse, EmotionState, ModelInfo, MultimodalAffect, ResearchDashboardData, ResearchExport, Scenario, SessionResponse, SessionSummary, StudyInformation, StudyQuestionnaire, StudyWithdrawal, UserProfile } from '../types/api'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'
let accessToken = sessionStorage.getItem('access_token')
let refreshPromise: Promise<AuthResponse> | null = null

async function request<T>(path: string, init?: RequestInit, retry = true): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...init, credentials: 'include', headers: { 'Content-Type': 'application/json', ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}), ...init?.headers } })
  if (response.status === 401 && retry && path !== '/auth/refresh') {
    try { await refreshAccess(); return request<T>(path, init, false) } catch { api.clearToken() }
  }
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? 'Request failed') }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

type AuthResponse = { access_token: string; user: UserProfile }
function acceptAuth(result: AuthResponse) { accessToken = result.access_token; sessionStorage.setItem('access_token', accessToken); return result }
function refreshAccess() {
  if (!refreshPromise) refreshPromise = request<AuthResponse>('/auth/refresh', { method: 'POST' }, false).then(acceptAuth).finally(() => { refreshPromise = null })
  return refreshPromise
}

async function download(path:string,retry=true):Promise<Blob> {
  const response=await fetch(`${API_URL}${path}`,{credentials:'include',headers:{...(accessToken?{Authorization:`Bearer ${accessToken}`}:{})}})
  if(response.status===401&&retry){await refreshAccess();return download(path,false)}
  if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail??'Download failed')}
  return response.blob()
}

export const api = {
  register: (data: { email:string; password:string; consent:boolean; first_name:string; last_name:string; preferred_name:string; country:string; timezone:string }) => request<{message:string;email:string}>('/auth/register', { method: 'POST', body: JSON.stringify(data) }, false),
  login: (email: string, password: string) => request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }, false).then(acceptAuth),
  verifyEmail: (token: string) => request<{message:string}>('/auth/verify-email', { method: 'POST', body: JSON.stringify({ token }) }, false),
  resendVerification: (email: string) => request<{message:string}>('/auth/resend-verification', { method: 'POST', body: JSON.stringify({ email }) }, false),
  forgotPassword: (email: string) => request<{message:string}>('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }, false),
  resetPassword: (token: string, newPassword: string) => request<void>('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, new_password: newPassword }) }, false),
  refresh: refreshAccess,
  me: () => request<UserProfile>('/auth/me'),
  completeOnboarding: (practiceGoals: string[]) => request<UserProfile>('/auth/onboarding', { method: 'PUT', body: JSON.stringify({ practice_goals: practiceGoals }) }),
  updateProfile: (profile: Pick<UserProfile,'first_name'|'last_name'|'preferred_name'|'country'|'timezone'>) => request<UserProfile>('/auth/me', { method: 'PATCH', body: JSON.stringify(profile) }),
  changePassword: (currentPassword: string, newPassword: string) => request<void>('/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
  researchExport: () => request<ResearchExport>('/auth/research-export'),
  studyProgress: () => request<StudyProgress>('/research/progress'),
  studyInformation: () => request<StudyInformation>('/research/study-information'),
  enrollPilot: (data:{access_code:string;consent_version:string;eligibility_version:string;age_confirmed:boolean;geography_confirmed:boolean;english_confirmed:boolean;other_criteria_confirmed:boolean;information_sheet_read:boolean;research_participation_accepted:boolean;data_processing_accepted:boolean}) => request<UserProfile>('/research/enroll',{method:'POST',body:JSON.stringify(data)}),
  withdrawFromStudy: () => request<StudyWithdrawal>('/research/withdraw',{method:'POST',body:JSON.stringify({confirm_withdrawal:true})}),
  researchDashboard: () => request<ResearchDashboardData>('/research/dashboard'),
  updateResearchLifecycle: (start_date:string,end_date:string) => request('/research/lifecycle',{method:'PUT',body:JSON.stringify({start_date,end_date})}),
  updateParticipantResearch: (participantId:string,data:{excluded:boolean;exclusion_reason:string;data_quality_notes:string}) => request(`/research/participants/${participantId}`,{method:'PATCH',body:JSON.stringify(data)}),
  freezeResearchDataset: () => request<{export_id:string;schema_version:string;created_at:string;record_count:number;participant_count:number;sha256:string}>('/research/freeze',{method:'POST',body:JSON.stringify({confirm_freeze:true})}),
  researchCsv: () => download('/research/export.csv'),
  logout: async () => { await request('/auth/logout', { method: 'POST' }); api.clearToken() },
  deleteAccount: async () => { await request('/auth/me', { method: 'DELETE' }); api.clearToken() },
  clearToken: () => { accessToken = null; sessionStorage.removeItem('access_token') },
  modelInfo: () => request<ModelInfo>('/models/info'),
  transcribe: (audioWavBase64: string) => request<AudioTranscription>('/audio/transcriptions', { method: 'POST', body: JSON.stringify({ audio_wav_base64: audioWavBase64 }) }),
  multimodalAffect: (sessionId: string, message: string, audioWavBase64: string) => request<MultimodalAffect>('/affect/multimodal', { method: 'POST', body: JSON.stringify({ session_id: sessionId, message, audio_wav_base64: audioWavBase64 }) }),
  createSession: () => request<{ session_id: string; emotion_state: EmotionState }>('/sessions', { method: 'POST' }),
  getSession: (id: string) => request<SessionResponse>(`/sessions/${id}`),
  listSessions: () => request<SessionSummary[]>('/sessions'),
  renameSession: (id: string, title: string) => request<SessionSummary>(`/sessions/${id}/title`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  saveTakeaway: (id:string, takeaway:string) => request<SessionResponse>(`/sessions/${id}/takeaway`, {method:'PUT',body:JSON.stringify({takeaway})}),
  sendMessage: (sessionId: string, message: string) => request<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify({ session_id: sessionId, message }) }),
  scenarios: () => request<Scenario[]>('/roleplay/scenarios'),
  createScenario: (data: {title:string;character:string;situation:string;user_objective:string;opening_line:string;skills:string[]}) => request<Scenario>('/roleplay/scenarios', { method:'POST', body:JSON.stringify(data) }),
  deleteScenario: (id:string) => request<void>(`/roleplay/scenarios/${id}`, { method:'DELETE' }),
  startRoleplay: (sessionId: string, scenarioId: string, difficulty: string, preRatings: {confidence:number;anxiety:number}|null, attemptPurpose: "required"|"additional"|"retry" = "additional", requiredTaskId: string|null = null) => request<{ session_id: string; emotion_state: EmotionState; scenario: Scenario; opening_turn: ChatResponse['turn']; state: ChatResponse['roleplay'] }>(`/sessions/${sessionId}/roleplay`, { method: 'POST', body: JSON.stringify({ scenario_id: scenarioId, difficulty, attempt_purpose:attemptPurpose, required_task_id:requiredTaskId, pre_ratings: preRatings, pre_skipped: preRatings===null }) }),
  roleplayAction: (sessionId: string, action: string) => request<SessionResponse>(`/sessions/${sessionId}/roleplay/action`, { method: 'POST', body: JSON.stringify({ action }) }),
  rewindRoleplay: (sessionId:string) => request<{removed_message:string;session:SessionResponse}>(`/sessions/${sessionId}/roleplay/rewind`, {method:'POST'}),
  closePostQuestionnaire: (sessionId:string) => request<void>(`/sessions/${sessionId}/questionnaires/post/close`, {method:'POST',keepalive:true}),
  submitQuestionnaire: (sessionId: string, phase: 'pre'|'post', values: {confidence?:number;anxiety?:number;realism?:number;usefulness?:number;skipped?:boolean;post_token?:string}) => request<{questionnaire:StudyQuestionnaire|null}>(`/sessions/${sessionId}/questionnaires/${phase}`, { method: 'PUT', body: JSON.stringify(values) }),
  deleteSession: (id: string) => request<void>(`/sessions/${id}`, { method: 'DELETE' }),
}
