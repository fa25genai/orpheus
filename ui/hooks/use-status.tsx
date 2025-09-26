// hooks/useStatusWebSocket.ts
import { useEffect, useState } from "react";
import { Status } from "@/generated-api-clients/status";

export function useStatus(promptId?: string) {
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    if (!promptId) return;

    const ws = new WebSocket(`ws://localhost:19910/status/${promptId}/live`);

    ws.onmessage = (event) => {
      try {
        const data: Status = JSON.parse(event.data);
        setStatus(data);
      } catch (e) {
        console.error("Failed to parse WS status message", e);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed");
    };

    return () => {
      ws.close();
    };
  }, [promptId]);

  return status;
}
