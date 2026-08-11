export type Role = 'user' | 'assistant'
export interface EmotionState { dominant_emotion: string; valence: number; arousal: number; confidence: number; trend: string }
export interface ConversationTurn { id: string; role: Role; content: string; created_at: string }
export interface RolePlayState { scenario_id: string; status: string; difficulty_level: string; turn: number; success_progress: number }
export interface Feedback { scenario_id: string; observed: string[]; strengths: string[]; suggestions: string[]; generation_source: string; metrics: { name: string; score: number }[] }
export interface ChatResponse { turn: ConversationTurn; decision: { emotion_state: EmotionState; strategy: string; cognitive_assessment: { possible_distortion: string|null; possible_cause: string|null; intent: string }; decision_reasons: string[]; analyzer_version: string }; roleplay: RolePlayState | null; feedback: Feedback | null }
export interface Scenario { id: string; title: string; character: string; user_objective: string; expected_skills: string[] }
export interface SessionResponse { session_id: string; turns: ConversationTurn[]; emotion_state: EmotionState; roleplay: RolePlayState | null; feedback: Feedback | null }
export interface UserProfile { id: string; email: string; first_name: string; last_name: string; preferred_name: string; country: string; timezone: string; email_verified: boolean }
