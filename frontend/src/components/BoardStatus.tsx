import { useEffect, useState } from "react";
import styles from "./BoardStatus.module.css";

interface BoardStatusData {
  board: string;
  started_at: string;
  completed_at?: string;
  status: string;
}

export default function BoardStatus() {
  const [statuses, setStatuses] = useState<BoardStatusData[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/scraper-status");
      if (res.ok) {
        const data = await res.json();
        setStatuses(data);
      }
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Refresh status every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusClass = (status: string) => {
    switch (status.toLowerCase()) {
      case "success":
        return styles.success;
      case "failed":
        return styles.failed;
      default:
        return styles.running;
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.title}>Scraper Status</div>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Loading status...</p>
      </div>
    );
  }

  // Define boards we expect to monitor in Stage 1
  const boardsList = ["remoteok", "himalayas", "ycombinator"];

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Scraper Status</h3>
      <div className={styles.list}>
        {boardsList.map((board) => {
          const run = statuses.find((s) => s.board.toLowerCase() === board.toLowerCase());
          const lastRunTime = run?.completed_at || run?.started_at;
          const timeStr = lastRunTime
            ? new Date(lastRunTime).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })
            : "Never run";

          return (
            <div key={board} className={styles.item}>
              <span className={styles.boardName}>{board}</span>
              <div className={styles.statusRow}>
                <span className={styles.time}>{timeStr}</span>
                <span
                  className={`${styles.indicator} ${getStatusClass(run?.status || "never")}`}
                  title={`Status: ${run?.status || "Unknown"}`}
                ></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
