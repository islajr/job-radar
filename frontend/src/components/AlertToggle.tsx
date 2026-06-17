import { useState } from "react";
import { toggleAlertPause } from "../api/matches";
import styles from "./AlertToggle.module.css";

interface AlertToggleProps {
  initialPaused: boolean;
  onToggle?: (paused: boolean) => void;
}

export default function AlertToggle({ initialPaused, onToggle }: AlertToggleProps) {
  const [paused, setPaused] = useState(initialPaused);
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    setLoading(true);
    const nextVal = !paused;
    try {
      await toggleAlertPause(nextVal);
      setPaused(nextVal);
      if (onToggle) onToggle(nextVal);
    } catch (e) {
      // ignore or alert
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <span className={styles.label}>
        {paused ? "⏸️ Alerts Paused" : "🔔 Alerts Active"}
      </span>
      <label className={styles.switch}>
        <input
          type="checkbox"
          checked={!paused}
          disabled={loading}
          onChange={handleToggle}
        />
        <span className={styles.slider}></span>
      </label>
    </div>
  );
}
