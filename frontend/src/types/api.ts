export type Role = 'user' | 'assistant'

export interface EmotionState {
  dominant_emotion: string
  valence: number
  arousal: number
  confidence: number
  trend: string
}

export interface ConversationTurn {
  id: string
  role: Role
  content: string
  created_at: string
}

export interface ChatResponse {
  turn: ConversationTurn
  decision: { emotion_state: EmotionState; strategy: string }
  roleplay: { active: boolean; turn: number; difficulty: number } | null
}

