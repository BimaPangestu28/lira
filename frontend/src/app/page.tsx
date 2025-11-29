"use client";

import { useState, useEffect } from "react";
import { VoiceRoom } from "@/components/VoiceRoom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import type { AgentMode, CEFRLevel, SessionResponse } from "@/types/session";

const MODES: { value: AgentMode; label: string; description: string }[] = [
  { value: "free_talk", label: "Free Talk", description: "Natural conversation" },
  { value: "corrective", label: "Corrective", description: "Get grammar corrections" },
  { value: "roleplay", label: "Roleplay", description: "Practice scenarios" },
  { value: "guided", label: "Guided", description: "Structured practice" },
];

const LEVELS: { value: CEFRLevel; label: string }[] = [
  { value: "A2", label: "A2 - Elementary" },
  { value: "B1", label: "B1 - Intermediate" },
  { value: "B2", label: "B2 - Upper Intermediate" },
  { value: "C1", label: "C1 - Advanced" },
];

export default function Home() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<AgentMode>("free_talk");
  const [level, setLevel] = useState<CEFRLevel>("B1");
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>("");
  const [micPermission, setMicPermission] = useState<"pending" | "granted" | "denied">("pending");

  // Request microphone permission and load devices
  useEffect(() => {
    async function requestMicPermission() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop()); // Release immediately
        setMicPermission("granted");

        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = devices.filter((d) => d.kind === "audioinput");
        setAudioDevices(audioInputs);

        if (audioInputs.length > 0) {
          const defaultDevice = audioInputs.find((d) => d.deviceId === "default") || audioInputs[0];
          setSelectedDevice(defaultDevice.deviceId);
        }
      } catch {
        setMicPermission("denied");
        setError("Microphone access is required for voice practice");
      }
    }

    requestMicPermission();
  }, []);

  const startSession = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.createSession({ mode, level });
      setSession(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start session");
    } finally {
      setIsLoading(false);
    }
  };

  const endSession = async () => {
    if (session) {
      try {
        await api.endSession(session.session_id);
      } catch (err) {
        console.error("Failed to end session:", err);
      }
    }
    setSession(null);
  };

  if (session) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-background p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold">LIRA</h1>
          <div className="mt-2 flex items-center justify-center gap-2">
            <Badge variant="secondary">
              {MODES.find((m) => m.value === session.mode)?.label}
            </Badge>
            <Badge variant="outline">{session.level}</Badge>
          </div>
        </div>

        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <VoiceRoom
              token={session.livekit_token}
              serverUrl={session.livekit_url}
              sessionId={session.session_id}
              selectedDeviceId={selectedDevice}
              onDisconnect={endSession}
            />
          </CardContent>
        </Card>

        <Button variant="destructive" onClick={endSession}>
          End Session
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-background p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold">LIRA</h1>
        <p className="mt-2 text-lg text-muted-foreground">
          Real-time English Speaking Practice
        </p>
      </div>

      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Start a Session</CardTitle>
          <CardDescription>Choose your practice mode and level</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Practice Mode</label>
            <div className="grid grid-cols-2 gap-2">
              {MODES.map((m) => (
                <Button
                  key={m.value}
                  variant={mode === m.value ? "default" : "outline"}
                  className="h-auto flex-col items-start p-3"
                  onClick={() => setMode(m.value)}
                >
                  <span className="font-medium">{m.label}</span>
                  <span className="text-xs opacity-70">{m.description}</span>
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">English Level</label>
            <Select value={level} onValueChange={(v) => setLevel(v as CEFRLevel)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LEVELS.map((l) => (
                  <SelectItem key={l.value} value={l.value}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Microphone</label>
            {micPermission === "pending" ? (
              <div className="rounded-lg border bg-muted/50 p-3 text-sm text-muted-foreground">
                Requesting microphone access...
              </div>
            ) : micPermission === "denied" ? (
              <div className="rounded-lg border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
                Microphone access denied. Please enable it in your browser settings.
              </div>
            ) : audioDevices.length === 0 ? (
              <div className="rounded-lg border bg-muted/50 p-3 text-sm text-muted-foreground">
                No microphones found
              </div>
            ) : (
              <Select value={selectedDevice} onValueChange={setSelectedDevice}>
                <SelectTrigger>
                  <SelectValue placeholder="Select microphone" />
                </SelectTrigger>
                <SelectContent>
                  {audioDevices.map((device) => (
                    <SelectItem key={device.deviceId} value={device.deviceId}>
                      {device.label || `Microphone ${device.deviceId.slice(0, 8)}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {error && (
            <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <Button
            className="w-full"
            size="lg"
            onClick={startSession}
            disabled={isLoading || micPermission !== "granted"}
          >
            {isLoading ? "Starting..." : "Start Practice"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
