import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { getMatches, type Match } from "../api/matches";
import MatchCard from "../components/MatchCard";
import AlertToggle from "../components/AlertToggle";
import BoardStatus from "../components/BoardStatus";
import styles from "./Dashboard.module.css";

export default function Dashboard() {
  const { user } = useAuth();

  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMatches = async () => {
    try {
      const data = await getMatches();
      setMatches(data);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatches();
  }, []);

  // Calculate matches found this week (past 7 days)
  const getMatchesThisWeek = () => {
    const oneWeekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    return matches.filter((m) => new Date(m.created_at).getTime() > oneWeekAgo).length;
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.welcome}>
          <h1 className={styles.name}>Hello, {user?.full_name || "Seeker"}</h1>
          <p style={{ color: "var(--text-secondary)" }}>Manage your remoteness match radar</p>
        </div>
      </header>

      <div className={styles.contentGrid}>
        <main className={styles.mainSection}>
          <h2 className={styles.sectionTitle}>Recent Matches</h2>

          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}>
              <div style={{ border: "3px solid rgba(255,255,255,0.1)", borderLeftColor: "#6366f1", borderRadius: "50%", width: "32px", height: "32px", animation: "spin 1s linear infinite" }}></div>
            </div>
          ) : matches.length === 0 ? (
            <div className={`${styles.emptyState} glass-card`}>
              <span className={styles.emptyIcon}>🛰️</span>
              <h3>No matched listings found yet</h3>
              <p style={{ maxWidth: "340px" }}>
                Make sure your email alerts are enabled and check back after the next scheduled scraper run!
              </p>
            </div>
          ) : (
            <div className={styles.matchesList}>
              {matches.map((match) => (
                <MatchCard key={match.id} match={match} />
              ))}
            </div>
          )}
        </main>

        <aside className={styles.sidebar}>
          <AlertToggle initialPaused={false} />

          <div className={`${styles.statsCard} glass-card`}>
            <span className={styles.statVal}>{getMatchesThisWeek()}</span>
            <span className={styles.statLabel}>Matches This Week</span>
          </div>

          <BoardStatus />

          <div className={styles.disclaimer}>
            ⚠️ <b>Note on listings:</b> Job listings are often not taken down immediately after being filled. We show when they were found; we cannot verify if they are still active.
          </div>
        </aside>
      </div>
    </div>
  );
}
