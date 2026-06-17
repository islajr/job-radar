import type { Match } from "../api/matches";
import styles from "./MatchCard.module.css";

interface MatchCardProps {
  match: Match;
}

export default function MatchCard({ match }: MatchCardProps) {
  const formattedDate = new Date(match.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const getBoardColor = (board: string) => {
    switch (board.toLowerCase()) {
      case "remoteok":
        return "rgba(255, 71, 87, 0.15)";
      case "himalayas":
        return "rgba(99, 102, 241, 0.15)";
      case "ycombinator":
        return "rgba(255, 102, 0, 0.15)";
      default:
        return "rgba(255, 255, 255, 0.05)";
    }
  };

  const getBoardBorder = (board: string) => {
    switch (board.toLowerCase()) {
      case "remoteok":
        return "rgba(255, 71, 87, 0.3)";
      case "himalayas":
        return "rgba(99, 102, 241, 0.3)";
      case "ycombinator":
        return "rgba(255, 102, 0, 0.3)";
      default:
        return "rgba(255, 255, 255, 0.1)";
    }
  };

  const getBoardTextColor = (board: string) => {
    switch (board.toLowerCase()) {
      case "remoteok":
        return "#ff4757";
      case "himalayas":
        return "#6366f1";
      case "ycombinator":
        return "#ff6600";
      default:
        return "var(--text-secondary)";
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.left}>
        <div className={styles.headerRow}>
          <h3 className={styles.title}>{match.title}</h3>
          <span
            className={styles.boardBadge}
            style={{
              backgroundColor: getBoardColor(match.board),
              borderColor: getBoardBorder(match.board),
              color: getBoardTextColor(match.board),
            }}
          >
            {match.board}
          </span>
        </div>

        <div className={styles.companyRow}>
          {match.company && <span className={styles.company}>{match.company}</span>}
          {match.location && <span style={{ color: "var(--text-muted)" }}>•</span>}
          {match.location && <span>📍 {match.location}</span>}
        </div>

        <div className={styles.metaRow}>
          {match.salary_text && (
            <div className={styles.metaItem}>
              <span>💰</span>
              <span>{match.salary_text}</span>
            </div>
          )}
          <div className={styles.metaItem}>
            <span>🕒</span>
            <span>Matched {formattedDate}</span>
          </div>
        </div>
      </div>

      <div className={styles.right}>
        <a
          href={match.url}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.btnView}
        >
          View Listing
        </a>
      </div>
    </div>
  );
}
