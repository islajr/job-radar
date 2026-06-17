import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getProfile, updateProfile, getNotifications, updateNotifications } from "../api/profile";
import KeywordInput from "../components/KeywordInput";
import TelegramConnect from "../components/TelegramConnect";
import ThemeToggle from "../components/ThemeToggle";
import styles from "./Settings.module.css";

export default function Settings() {
  const navigate = useNavigate();

  // Role and experience state
  const [roleTitle, setRoleTitle] = useState("");
  const [experienceYears, setExperienceYears] = useState("1");
  const [roleLoading, setRoleLoading] = useState(false);
  const [roleMsg, setRoleMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Keywords and description state
  const [inclusionKeywords, setInclusionKeywords] = useState<string[]>([]);
  const [exclusionKeywords, setExclusionKeywords] = useState<string[]>([]);
  const [skillsSummary, setSkillsSummary] = useState("");
  const [kwLoading, setKwLoading] = useState(false);
  const [kwMsg, setKwMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Notifications state
  const [frequency, setFrequency] = useState("immediate");
  const [notifLoading, setNotifLoading] = useState(false);
  const [notifMsg, setNotifMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [telegramConnected, setTelegramConnected] = useState(false);

  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const profile = await getProfile();
        setRoleTitle(profile.role_title || "");
        setExperienceYears(profile.experience_years?.toString() || "1");
        setInclusionKeywords(profile.inclusion_keywords || []);
        setExclusionKeywords(profile.exclusion_keywords || []);
        setSkillsSummary(profile.skills_summary || "");

        const notif = await getNotifications();
        setFrequency(notif.frequency || "immediate");
        setTelegramConnected(notif.telegram_connected || false);
      } catch (e) {
        // ignore
      } finally {
        setPageLoading(false);
      }
    };
    loadSettings();
  }, []);

  const handleSaveRole = async (e: React.FormEvent) => {
    e.preventDefault();
    setRoleLoading(true);
    setRoleMsg(null);
    try {
      await updateProfile({
        role_title: roleTitle,
        experience_years: parseInt(experienceYears, 10),
      });
      setRoleMsg({ text: "Role & experience saved successfully!", type: "success" });
    } catch (err: any) {
      setRoleMsg({ text: err?.detail || "Failed to save role settings.", type: "error" });
    } finally {
      setRoleLoading(false);
    }
  };

  const handleSaveKeywords = async (e: React.FormEvent) => {
    e.preventDefault();
    setKwLoading(true);
    setKwMsg(null);
    try {
      await updateProfile({
        inclusion_keywords: inclusionKeywords,
        exclusion_keywords: exclusionKeywords,
        skills_summary: skillsSummary,
      });
      setKwMsg({ text: "Keywords & filters saved successfully!", type: "success" });
    } catch (err: any) {
      setKwMsg({ text: err?.detail || "Failed to save filters.", type: "error" });
    } finally {
      setKwLoading(false);
    }
  };

  const handleSaveNotifications = async (e: React.FormEvent) => {
    e.preventDefault();
    setNotifLoading(true);
    setNotifMsg(null);
    try {
      await updateNotifications({
        frequency: frequency,
      });
      setNotifMsg({ text: "Notification settings saved successfully!", type: "success" });
    } catch (err: any) {
      setNotifMsg({ text: err?.detail || "Failed to save settings.", type: "error" });
    } finally {
      setNotifLoading(false);
    }
  };

  if (pageLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <div style={{ border: "4px solid rgba(255,255,255,0.1)", borderLeftColor: "var(--primary)", borderRadius: "50%", width: "40px", height: "40px", animation: "spin 1s linear infinite" }}></div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Settings</h1>
          <p style={{ color: "var(--text-secondary)" }}>Adjust your match filters and alerts</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <ThemeToggle />
          <button className={styles.btnBack} onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </div>
      </header>

      {/* Section 1: Role & Experience */}
      <section className={`${styles.sectionCard} glass-card`}>
        <h2 className={styles.sectionTitle}>1. Target Role & Experience</h2>
        {roleMsg && (
          <div className={`${styles.message} ${roleMsg.type === "success" ? styles.successMessage : styles.errorMessage}`}>
            {roleMsg.text}
          </div>
        )}
        <form onSubmit={handleSaveRole} className={styles.formGroup}>
          <div className={styles.inputGroup}>
            <label className={styles.label} htmlFor="roleTitle">Target Job Title / Role Type</label>
            <input
              className={styles.input}
              id="roleTitle"
              type="text"
              required
              placeholder="e.g. Backend Engineer, Social Media Manager"
              value={roleTitle}
              onChange={(e) => setRoleTitle(e.target.value)}
            />
          </div>

          <div className={styles.inputGroup}>
            <label className={styles.label} htmlFor="exp">Years of Experience</label>
            <select
              className={styles.select}
              id="exp"
              value={experienceYears}
              onChange={(e) => setExperienceYears(e.target.value)}
            >
              <option value="1">0 - 1 Years</option>
              <option value="2">1 - 3 Years</option>
              <option value="4">3 - 5 Years</option>
              <option value="7">5 - 10 Years</option>
              <option value="12">10+ Years</option>
            </select>
          </div>

          <button className={`${styles.btnSave} btn-glow`} type="submit" disabled={roleLoading}>
            {roleLoading ? "Saving..." : "Save Role"}
          </button>
        </form>
      </section>

      {/* Section 2: Keywords & Filters */}
      <section className={`${styles.sectionCard} glass-card`}>
        <h2 className={styles.sectionTitle}>2. Keywords & Filters</h2>
        {kwMsg && (
          <div className={`${styles.message} ${kwMsg.type === "success" ? styles.successMessage : styles.errorMessage}`}>
            {kwMsg.text}
          </div>
        )}
        <form onSubmit={handleSaveKeywords} className={styles.formGroup}>
          <div className={styles.inputGroup}>
            <label className={styles.label}>Inclusion Keywords</label>
            <KeywordInput
              value={inclusionKeywords}
              onChange={setInclusionKeywords}
              placeholder="e.g. python, remote, api"
            />
          </div>

          <div className={styles.inputGroup}>
            <label className={styles.label}>Exclusion Keywords</label>
            <KeywordInput
              value={exclusionKeywords}
              onChange={setExclusionKeywords}
              placeholder="e.g. unpaid, hybrid, senior"
            />
          </div>

          <div className={styles.inputGroup}>
            <label className={styles.label} htmlFor="summary">Brief Description / Skills Summary</label>
            <textarea
              className={styles.textarea}
              id="summary"
              placeholder="Briefly describe what you're looking for, or list your main skills."
              value={skillsSummary}
              onChange={(e) => setSkillsSummary(e.target.value)}
            />
          </div>

          <button className={`${styles.btnSave} btn-glow`} type="submit" disabled={kwLoading}>
            {kwLoading ? "Saving..." : "Save Filters"}
          </button>
        </form>
      </section>

      {/* Section 3: Notification Settings */}
      <section className={`${styles.sectionCard} glass-card`}>
        <h2 className={styles.sectionTitle}>3. Alert Settings</h2>
        {notifMsg && (
          <div className={`${styles.message} ${notifMsg.type === "success" ? styles.successMessage : styles.errorMessage}`}>
            {notifMsg.text}
          </div>
        )}
        <form onSubmit={handleSaveNotifications} className={styles.formGroup}>
          <div className={styles.inputGroup}>
            <label className={styles.label}>Alert Frequency</label>
            <div className={styles.radioGroup}>
              <div
                className={`${styles.radioLabel} ${frequency === "immediate" ? styles.radioActive : ""}`}
                onClick={() => setFrequency("immediate")}
              >
                <span className={styles.radioTitle}>⚡ Immediate</span>
                <span className={styles.radioDesc}>Get notified as soon as matches are found</span>
              </div>
              <div
                className={`${styles.radioLabel} ${frequency === "digest" ? styles.radioActive : ""}`}
                onClick={() => setFrequency("digest")}
              >
                <span className={styles.radioTitle}>📅 Daily Digest</span>
                <span className={styles.radioDesc}>A single batched message sent every morning</span>
              </div>
            </div>
          </div>

          <button className={`${styles.btnSave} btn-glow`} type="submit" disabled={notifLoading}>
            {notifLoading ? "Saving..." : "Save Notification Settings"}
          </button>
        </form>

        <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border-color)", paddingTop: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <label className={styles.label} style={{ marginBottom: 0 }}>Telegram Bot Connection</label>
            {telegramConnected ? (
              <span style={{ fontSize: "0.85rem", color: "#10b981", backgroundColor: "rgba(16, 185, 129, 0.15)", padding: "0.25rem 0.6rem", borderRadius: "100px", border: "1px solid rgba(16, 185, 129, 0.3)", fontWeight: 500 }}>Connected</span>
            ) : (
              <span style={{ fontSize: "0.85rem", color: "#f59e0b", backgroundColor: "rgba(245, 158, 11, 0.15)", padding: "0.25rem 0.6rem", borderRadius: "100px", border: "1px solid rgba(245, 158, 11, 0.3)", fontWeight: 500 }}>Not Connected</span>
            )}
          </div>
          <TelegramConnect onConnected={() => setTelegramConnected(true)} />
        </div>
      </section>
    </div>
  );
}
