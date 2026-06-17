import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import ThemeToggle from "../components/ThemeToggle";
import styles from "./Landing.module.css";

export default function Landing() {
  const { user } = useAuth();

  // If user is already logged in, redirect them to dashboard
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className={styles.container}>
      <nav className={styles.navbar}>
        <span className={styles.logo}>🔎 Job Radar</span>
        <ThemeToggle />
      </nav>
      <header className={styles.hero}>
        <div className={styles.badge}>Stage 1 Core Active</div>
        <h1 className={styles.title}>Your Personal Remote Job Radar</h1>
        <p className={styles.description}>
          Stop manually scanning job boards. Set your keywords, connect your Telegram bot, and get personalized remote opportunities delivered instantly to your phone.
        </p>
        <div className={styles.ctaGroup}>
          <Link to="/register" className="btn-glow">
            Get Started
          </Link>
          <Link to="/login" className={styles.btnSecondary}>
            Sign In
          </Link>
        </div>
      </header>

      <section className={styles.features}>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>🤖</div>
          <h3 className={styles.featureTitle}>Telegram Alerts</h3>
          <p className={styles.featureDesc}>
            Instant notifications directly in Telegram as soon as matching remote job listings are detected.
          </p>
        </div>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>🔍</div>
          <h3 className={styles.featureTitle}>Smart Filtering</h3>
          <p className={styles.featureDesc}>
            Precise keyword matching with inclusions and exclusions to shield you from irrelevant roles.
          </p>
        </div>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>⚡</div>
          <h3 className={styles.featureTitle}>Multi-Board Scraper</h3>
          <p className={styles.featureDesc}>
            Scrapes Y Combinator Jobs, Himalayas, and RemoteOK concurrently on a recurring schedule.
          </p>
        </div>
      </section>
    </div>
  );
}
