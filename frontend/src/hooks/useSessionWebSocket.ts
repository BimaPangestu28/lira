"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface TranscriptionEvent {
  type: "transcription";
  text: string;
  is_final: boolean;
}

interface ResponseEvent {
  type: "response";
  text: string;
}

interface ModeChangedEvent {
  type: "mode_changed";
  mode: string;
}

type WebSocketEvent = TranscriptionEvent | ResponseEvent | ModeChangedEvent;

interface UseSessionWebSocketOptions {
  sessionId: string;
  onTranscription?: (text: string, isFinal: boolean) => void;
  onResponse?: (text: string) => void;
  onModeChanged?: (mode: string) => void;
}

export function useSessionWebSocket({
  sessionId,
  onTranscription,
  onResponse,
  onModeChanged,
}: UseSessionWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Store callbacks in refs to avoid reconnection on callback changes
  const callbacksRef = useRef({ onTranscription, onResponse, onModeChanged });
  callbacksRef.current = { onTranscription, onResponse, onModeChanged };

  const setMode = useCallback((mode: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "set_mode", mode }));
    }
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    const wsUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://localhost:8011/api"}/sessions/${sessionId}/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data: WebSocketEvent = JSON.parse(event.data);
      const callbacks = callbacksRef.current;

      switch (data.type) {
        case "transcription":
          callbacks.onTranscription?.(data.text, data.is_final);
          break;
        case "response":
          callbacks.onResponse?.(data.text);
          break;
        case "mode_changed":
          callbacks.onModeChanged?.(data.mode);
          break;
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  return {
    isConnected,
    setMode,
  };
}
