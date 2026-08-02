import type { ChatResponse, ConversationTurn, EmotionState } from '../types/api'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) throw new Error((await response.json()).detail ?? 'Request failed')
  return response.json() as Promise<T>
}

export const api = {
  createSession: () => request<{ session_id: string; emotion_state: EmotionState }>('/sessions', { method: 'POST' }),
  sendMessage: (sessionId: string, message: string) =>
    request<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify({ session_id: sessionId, message }) }),
  startRoleplay: (sessionId: string) =>
    request<{ opening_turn: ConversationTurn }>(`/sessions/${sessionId}/roleplay`, {
      method: 'POST', body: JSON.stringify({ scenario_id: 'workload' }),
    }),
  deleteSession: (sessionId: string) => fetch(`${API_URL}/sessions/${sessionId}`, { method: 'DELETE' }),
}

