export type Role = 'user' | 'assistant'
export interface EmotionState { dominant_emotion: string; valence: number; arousal: number; confidence: number; trend: string }
export interface ConversationTurn { id: string; role: Role; content: string; created_at: string }
export interface RolePlayState { scenario_id: string; status: string; difficulty_level: string; turn: number; success_progress: number; completion_reason?: string | null }
export interface Feedback { session_id?: string|null; scenario_id: string; observed: string[]; strengths: string[]; suggestions: string[]; generation_source: string; metrics: { name: string; score: number; evidence_turns?: number[] }[] }
export interface ChatResponse { turn: ConversationTurn; decision: { emotion_state: EmotionState; strategy: string; cognitive_assessment: { possible_distortion: string|null; possible_cause: string|null; intent: string }; decision_reasons: string[]; analyzer_version: string }; roleplay: RolePlayState | null; feedback: Feedback | null }
export interface Scenario { id: string; title: string; character: string; user_objective: string; expected_skills: string[] }
export interface SessionResponse { session_id: string; turns: ConversationTurn[]; emotion_state: EmotionState; roleplay: RolePlayState | null; feedback: Feedback | null }
export interface SessionSummary { session_id: string; updated_at: string; turn_count: number; roleplay?: RolePlayState | null }
export interface UserProfile { id: string; email: string; first_name: string; last_name: string; preferred_name: string; country: string; timezone: string; email_verified: boolean }
export interface ModelInfo { trained_model: boolean; multimodal_model: string | null; multimodal_status: string; transcription_available: boolean; transcription_model: string | null; disclaimer: string }
export interface MultimodalAffect { label: string; confidence: number; distribution: Record<string,number>; text_label: string; text_confidence: number; text_distribution: Record<string,number>; audio_label: string; audio_confidence: number; audio_distribution: Record<string,number>; modalities_agree: boolean; confidence_level: 'low'|'moderate'|'high'; low_confidence_threshold: number; model_version: string; latency_ms: number; queue_ms: number; audio_persisted: false; disclaimer: string }
export interface AudioTranscription { text: string; model: string; latency_ms: number; audio_persisted: false }
export interface StudyQuestionnaire { phase: 'pre'|'post'; confidence?: number|null; anxiety?: number|null; realism?: number|null; usefulness?: number|null; submitted_at: string }
export interface ResearchExport { schema_version: string; participant_id: string; contains_conversation_text: false; consent: {version:string;accepted_at:string}; sessions: unknown[] }
