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

  const getBoardClass = (board: string) => {
    switch (board.toLowerCase()) {
      case "remoteok":
        return styles.remoteok;
      case "himalayas":
        return styles.himalayas;
      case "ycombinator":
        return styles.ycombinator;
      default:
        return "";
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.left}>
        <div className={styles.headerRow}>
          <h3 className={styles.title}>{match.title}</h3>
          <span className={`${styles.boardBadge} ${getBoardClass(match.board)}`}>
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
