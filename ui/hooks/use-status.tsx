"use client";
import {useEffect, useState} from "react";
import {Status} from "@/generated-api-clients/status";

export function useStatus(promptId?: string) {
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    if (!promptId) return;

    // Use correct protocol depending on page
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://localhost:19910/status/${promptId}/live`;

    console.log("Connecting to WebSocket:", wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("✅ WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data: Status = JSON.parse(event.data);
        setStatus(data);
      } catch (e) {
        console.error("❌ Failed to parse WS status message", e, event.data);
      }
    };

    ws.onerror = (err) => {
      console.error("❌ WebSocket error:", err);
    };

    ws.onclose = (ev) => {
      console.log(
        `⚠️ WebSocket closed (code=${ev.code}, reason=${ev.reason || "none"})`
      );
    };

    return () => {
      console.log("Cleaning up WebSocket");
      ws.close();
    };
  }, [promptId]);

  return status;
}
