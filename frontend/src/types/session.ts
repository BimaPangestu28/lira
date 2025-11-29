/**
 * Session-related types matching the backend models.
 */

export type AgentMode = "free_talk" | "corrective" | "roleplay" | "guided";

export type CEFRLevel = "A2" | "B1" | "B2" | "C1";

export interface SessionCreate {
  mode?: AgentMode;
  level?: CEFRLevel;
}

export interface SessionResponse {
  session_id: string;
  mode: AgentMode;
  level: CEFRLevel;
  livekit_token: string;
  livekit_url: string;
}

export interface SessionMetrics {
  words_spoken: number;
  mistakes_detected: number;
}

export interface Session {
  session_id: string;
  mode: AgentMode;
  level: CEFRLevel;
  history: Array<{ role: "user" | "assistant"; text: string }>;
  metrics: SessionMetrics;
}
