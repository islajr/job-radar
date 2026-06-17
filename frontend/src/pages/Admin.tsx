import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getAdminUsers, getScraperRuns, triggerScraper, type AdminUser, type ScraperRun } from "../api/admin";
import styles from "./Admin.module.css";

export default function Admin() {
  const navigate = useNavigate();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [runs, setRuns] = useState<ScraperRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const loadAdminData = async () => {
    try {
      const usersData = await getAdminUsers();
      const runsData = await getScraperRuns();
      setUsers(usersData);
      setRuns(runsData);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
    // Poll data every 10 seconds
    const interval = setInterval(loadAdminData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleTriggerScraper = async () => {
    setTriggering(true);
    setMsg(null);
    try {
      await triggerScraper();
      setMsg({ text: "GitHub workflow dispatched successfully! Run started.", type: "success" });
      loadAdminData();
    } catch (err: any) {
      setMsg({ text: err?.detail || "Failed to trigger scraper workflow. Verify GITHUB_DISPATCH_TOKEN.", type: "error" });
    } finally {
      setTriggering(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "success":
        return <span className={`${styles.badge} ${styles.badgeSuccess}`}>Success</span>;
      case "failed":
        return <span className={`${styles.badge} ${styles.badgeError}`}>Failed</span>;
      case "partial":
        return <span className={`${styles.badge} ${styles.badgeWarning}`}>Partial</span>;
      default:
        return <span className={`${styles.badge} ${styles.badgeWarning}`}>Running</span>;
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <div style={{ border: "4px solid rgba(255,255,255,0.1)", borderLeftColor: "#6366f1", borderRadius: "50%", width: "40px", height: "40px", animation: "spin 1s linear infinite" }}></div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Admin Panel</h1>
          <p style={{ color: "var(--text-secondary)" }}>Monitor scraper health and user status</p>
        </div>
        <button className={styles.btnBack} onClick={() => navigate("/dashboard")}>
          Back to Dashboard
        </button>
      </header>

      {/* Scraper manual trigger section */}
      <section className={styles.triggerSection}>
        <div className={styles.triggerText}>
          <span className={styles.triggerTitle}>Manual Scraper Execution</span>
          <span className={styles.triggerDesc}>Dispatch the GitHub Actions workflow immediately</span>
        </div>
        <button
          className="btn-glow"
          onClick={handleTriggerScraper}
          disabled={triggering}
        >
          {triggering ? "Dispatching..." : "Run Scraper Now"}
        </button>
      </section>

      {msg && (
        <div className={`${styles.message} ${msg.type === "success" ? styles.successMessage : styles.errorMessage}`} style={{ padding: "1rem", borderRadius: "8px", border: "1px solid", textAlign: "center" }}>
          {msg.text}
        </div>
      )}

      <div className={styles.sectionsGrid}>
        {/* Scraper Run History */}
        <div className={`${styles.card} glass-card`}>
          <h2 className={styles.sectionHeader}>Scraper Execution Log</h2>
          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Board</th>
                  <th>Started At</th>
                  <th>Completed At</th>
                  <th>Found</th>
                  <th>New</th>
                  <th>Status</th>
                  <th>Errors</th>
                </tr>
              </thead>
              <tbody>
                {runs.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", color: "var(--text-secondary)" }}>
                      No runs recorded yet.
                    </td>
                  </tr>
                ) : (
                  runs.map((run) => (
                    <tr key={run.id}>
                      <td style={{ textTransform: "capitalize", fontWeight: 600 }}>{run.board}</td>
                      <td>{new Date(run.started_at).toLocaleString()}</td>
                      <td>{run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}</td>
                      <td>{run.listings_found}</td>
                      <td>{run.new_listings}</td>
                      <td>{getStatusBadge(run.status)}</td>
                      <td className={styles.errorText} title={run.errors || ""}>
                        {run.errors || "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* User list summary */}
        <div className={`${styles.card} glass-card`}>
          <h2 className={styles.sectionHeader}>Registered Users</h2>
          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Registered At</th>
                  <th>Alerts</th>
                  <th>Telegram Connected</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td style={{ fontWeight: 600 }}>{user.full_name}</td>
                    <td>{user.email}</td>
                    <td>{new Date(user.created_at).toLocaleDateString()}</td>
                    <td>{user.alerts_paused ? "⏸️ Paused" : "🔔 Active"}</td>
                    <td>
                      {user.telegram_connected ? (
                        <span className={`${styles.badge} ${styles.badgeSuccess}`}>Connected</span>
                      ) : (
                        <span className={`${styles.badge} ${styles.badgeError}`}>Disconnected</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
