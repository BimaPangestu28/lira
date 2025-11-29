/**
 * API client for communicating with the LIRA backend.
 */

import type { SessionCreate, SessionResponse, Session, AgentMode } from "@/types/session";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, `API error: ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  /**
   * Create a new session and get LiveKit credentials.
   */
  createSession: (data?: SessionCreate): Promise<SessionResponse> =>
    request<SessionResponse>("/sessions", {
      method: "POST",
      body: JSON.stringify(data || {}),
    }),

  /**
   * Get session details.
   */
  getSession: (sessionId: string): Promise<Session> =>
    request<Session>(`/sessions/${sessionId}`),

  /**
   * Update session mode.
   */
  updateSessionMode: (sessionId: string, mode: AgentMode): Promise<{ session_id: string; mode: AgentMode }> =>
    request(`/sessions/${sessionId}/mode?mode=${mode}`, {
      method: "PATCH",
    }),

  /**
   * End a session.
   */
  endSession: (sessionId: string): Promise<{ session_id: string; status: string; metrics: Session["metrics"] }> =>
    request(`/sessions/${sessionId}`, {
      method: "DELETE",
    }),

  /**
   * Health check.
   */
  healthCheck: (): Promise<{ status: string; service: string }> =>
    request("/health"),
};
