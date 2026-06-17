import { useState, useEffect, useRef } from "react";
import styles from "./TelegramConnect.module.css";

interface TelegramConnectProps {
  onConnected: () => void;
}

export default function TelegramConnect({ onConnected }: TelegramConnectProps) {
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "waiting" | "connected" | "timeout">("idle");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startConnect = async () => {
    try {
      const res = await fetch("/api/telegram/connect");
      const data = await res.json();
      setDeepLink(data.deep_link);
      setStatus("waiting");

      let elapsed = 0;
      if (pollRef.current) clearInterval(pollRef.current);

      pollRef.current = setInterval(async () => {
        elapsed += 3;
        if (elapsed > 120) {
          if (pollRef.current) clearInterval(pollRef.current);
          setStatus("timeout");
          return;
        }

        try {
          const statusRes = await fetch("/api/telegram/status");
          const statusData = await statusRes.json();
          if (statusData.connected) {
            if (pollRef.current) clearInterval(pollRef.current);
            setStatus("connected");
            onConnected();
          }
        } catch (e) {
          // ignore network failures during polling
        }
      }, 3000);
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return (
    <div className={styles.container}>
      {status === "idle" && (
        <>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
            Connect your Telegram account to receive instant job alerts.
          </p>
          <button className="btn-glow" onClick={startConnect}>
            Connect Telegram Bot
          </button>
        </>
      )}

      {status === "waiting" && deepLink && (
        <>
          <div className={styles.instructions}>
            <div className={styles.step}>
              <span className={styles.stepNum}>1.</span>
              <span>Click the button below to open your Telegram bot interface.</span>
            </div>
            <div className={styles.step}>
              <span className={styles.stepNum}>2.</span>
              <span>Tap the <b>Start</b> button at the bottom of the chat.</span>
            </div>
          </div>

          <a href={deepLink} target="_blank" rel="noreferrer" className={styles.btnTelegram}>
            <span>Open in Telegram</span>
          </a>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.5rem" }}>
            <div className={styles.spinner}></div>
            <p className={styles.statusText} style={{ color: "var(--primary)" }}>Waiting for bot connection...</p>
          </div>
        </>
      )}

      {status === "connected" && (
        <div className={styles.statusConnected}>
          <span>🎉 Connected! Your Telegram bot is fully linked.</span>
        </div>
      )}

      {status === "timeout" && (
        <div className={styles.statusTimeout}>
          <p>The connection attempt timed out.</p>
          <button className="btn-glow" onClick={startConnect}>
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}
