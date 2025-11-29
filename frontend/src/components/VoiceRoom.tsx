"use client";

import { useCallback, useEffect, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
  MediaDeviceMenu,
} from "@livekit/components-react";
import { useSessionWebSocket } from "@/hooks/useSessionWebSocket";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  text: string;
}

interface VoiceRoomProps {
  token: string;
  serverUrl: string;
  sessionId: string;
  selectedDeviceId?: string;
  onDisconnect?: () => void;
}

interface RoomContentProps {
  sessionId: string;
}

function RoomContent({ sessionId }: RoomContentProps) {
  const room = useRoomContext();
  const [isMuted, setIsMuted] = useState(false);
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>("");

  const { isConnected } = useSessionWebSocket({
    sessionId,
    onTranscription: (text, isFinal) => {
      setCurrentTranscript(text);
      if (isFinal) {
        setMessages((prev) => [...prev, { role: "user", text }]);
        setCurrentTranscript("");
      }
    },
    onResponse: (text) => {
      setMessages((prev) => [...prev, { role: "assistant", text }]);
    },
  });

  // Load available audio devices (only once on mount)
  useEffect(() => {
    let mounted = true;

    async function loadDevices() {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        if (!mounted) return;

        const audioInputs = devices.filter((d) => d.kind === "audioinput");
        setAudioDevices(audioInputs);

        // Set default device only if not already set
        if (audioInputs.length > 0) {
          const defaultDevice = audioInputs.find((d) => d.deviceId === "default") || audioInputs[0];
          setSelectedDevice((prev) => prev || defaultDevice.deviceId);
        }
      } catch (err) {
        console.error("Failed to load audio devices:", err);
      }
    }

    loadDevices();

    return () => {
      mounted = false;
    };
  }, []);

  // Switch microphone (only when user explicitly selects)
  const switchMicrophone = useCallback(
    async (deviceId: string) => {
      if (deviceId === selectedDevice) return; // Prevent duplicate switches

      setSelectedDevice(deviceId);
      try {
        await room.switchActiveDevice("audioinput", deviceId);
        console.log("Switched to microphone:", deviceId);
      } catch (err) {
        console.error("Failed to switch microphone:", err);
      }
    },
    [room, selectedDevice]
  );

  const toggleMute = useCallback(async () => {
    const localParticipant = room.localParticipant;
    await localParticipant.setMicrophoneEnabled(isMuted);
    setIsMuted(!isMuted);
  }, [room, isMuted]);

  useEffect(() => {
    room.localParticipant.setMicrophoneEnabled(true);
  }, [room]);

  return (
    <div className="flex flex-col gap-6">
      {/* Status */}
      <div className="flex items-center justify-center gap-3">
        <Badge variant={isMuted ? "destructive" : "default"} className="gap-1.5">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              isMuted ? "bg-destructive-foreground" : "bg-primary-foreground animate-pulse"
            )}
          />
          {isMuted ? "Muted" : "Listening"}
        </Badge>
        <Badge variant={isConnected ? "secondary" : "outline"} className="gap-1.5">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              isConnected ? "bg-blue-500" : "bg-muted-foreground"
            )}
          />
          {isConnected ? "Connected" : "Connecting..."}
        </Badge>
      </div>

      {/* Microphone Selection */}
      {audioDevices.length > 1 && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">Microphone</label>
          <Select value={selectedDevice} onValueChange={switchMicrophone}>
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
        </div>
      )}

      {/* Messages */}
      <div className="h-64 overflow-y-auto rounded-lg border bg-muted/30 p-4">
        {messages.length === 0 && !currentTranscript ? (
          <p className="text-center text-sm text-muted-foreground">
            Start speaking to begin...
          </p>
        ) : (
          <div className="space-y-3">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[80%] rounded-lg px-3 py-2 text-sm",
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  )}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {currentTranscript && (
              <div className="flex justify-end">
                <div className="max-w-[80%] rounded-lg bg-primary/50 px-3 py-2 text-sm text-primary-foreground">
                  {currentTranscript}...
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Mute Button */}
      <Button
        variant={isMuted ? "default" : "destructive"}
        size="lg"
        className="w-full"
        onClick={toggleMute}
      >
        {isMuted ? "Unmute Microphone" : "Mute Microphone"}
      </Button>

      <RoomAudioRenderer />
    </div>
  );
}

export function VoiceRoom({ token, serverUrl, sessionId, selectedDeviceId, onDisconnect }: VoiceRoomProps) {
  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect={true}
      audio={{ deviceId: selectedDeviceId }}
      video={false}
      onDisconnected={onDisconnect}
    >
      <RoomContent sessionId={sessionId} />
    </LiveKitRoom>
  );
}
