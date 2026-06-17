import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { updateProfile, updateNotifications } from "../api/profile";
import KeywordInput from "../components/KeywordInput";
import TelegramConnect from "../components/TelegramConnect";
import styles from "./Onboarding.module.css";

type Step = 1 | 2 | 3;

export default function Onboarding() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>(1);
  const [roleTitle, setRoleTitle] = useState("");
  const [experienceYears, setExperienceYears] = useState("1");
  const [inclusionKeywords, setInclusionKeywords] = useState<string[]>([]);
  const [exclusionKeywords, setExclusionKeywords] = useState<string[]>([]);
  const [skillsSummary, setSkillsSummary] = useState("");
  const [frequency, setFrequency] = useState("immediate");
  const [telegramConnected, setTelegramConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If not logged in, redirect to login
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // If already completed onboarding, redirect to dashboard
  if (user.onboarding_complete) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleFinish = async () => {
    setLoading(true);
    setError(null);
    try {
      // Step 1: Update Profile data
      await updateProfile({
        role_title: roleTitle,
        experience_years: parseInt(experienceYears, 10),
        inclusion_keywords: inclusionKeywords,
        exclusion_keywords: exclusionKeywords,
        skills_summary: skillsSummary,
      });

      // Step 2: Update notification settings (channel default to telegram)
      await updateNotifications({
        channels: ["telegram"],
        frequency: frequency,
      });

      // Step 3: Complete onboarding
      await updateProfile({
        onboarding_complete: true,
      });

      // Step 4: Refresh Auth Context user state & redirect
      await refreshUser();
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.detail || "Failed to save onboarding settings. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const activePercent = ((step - 1) / 2) * 100;

  return (
    <div className={styles.container}>
      <div className={`${styles.card} glass-card`}>
        <div className={styles.progress}>
          <div className={styles.progressLine}></div>
          <div className={styles.progressLineActive} style={{ width: `${activePercent}%` }}></div>
          <div className={`${styles.stepDot} ${step >= 1 ? styles.stepDotActive : ""} ${step > 1 ? styles.stepDotDone : ""}`}>
            {step > 1 ? "✓" : "1"}
          </div>
          <div className={`${styles.stepDot} ${step >= 2 ? styles.stepDotActive : ""} ${step > 2 ? styles.stepDotDone : ""}`}>
            {step > 2 ? "✓" : "2"}
          </div>
          <div className={`${styles.stepDot} ${step >= 3 ? styles.stepDotActive : ""}`}>
            3
          </div>
        </div>

        {error && <div className={styles.error} style={{ color: "var(--error)", textAlign: "center" }}>{error}</div>}

        {step === 1 && (
          <div className={styles.header}>
            <h2 className={styles.title}>What's your focus?</h2>
            <p className={styles.subtitle}>Define your desired role type and experience level</p>
          </div>
        )}

        {step === 2 && (
          <div className={styles.header}>
            <h2 className={styles.title}>Set your filters</h2>
            <p className={styles.subtitle}>List keywords to search for, and exclusions to hide roles</p>
          </div>
        )}

        {step === 3 && (
          <div className={styles.header}>
            <h2 className={styles.title}>Configure Alerts</h2>
            <p className={styles.subtitle}>Link your Telegram bot to receive matches</p>
          </div>
        )}

        <div className={styles.form}>
          {step === 1 && (
            <>
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
            </>
          )}

          {step === 2 && (
            <>
              <div className={styles.inputGroup}>
                <label className={styles.label}>Inclusion Keywords (Comma Separated)</label>
                <KeywordInput
                  value={inclusionKeywords}
                  onChange={setInclusionKeywords}
                  placeholder="e.g. python, remote, api"
                />
              </div>

              <div className={styles.inputGroup}>
                <label className={styles.label}>Exclusion Keywords (Comma Separated)</label>
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
                  placeholder="Briefly describe what you're looking for, or list your main skills (used for scoring matching listings later)."
                  value={skillsSummary}
                  onChange={(e) => setSkillsSummary(e.target.value)}
                />
              </div>
            </>
          )}

          {step === 3 && (
            <>
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

              <div className={styles.infoNote}>
                ℹ️ Alerts are delivered exclusively via Telegram. Setup the Telegram Bot below.
              </div>

              <TelegramConnect onConnected={() => setTelegramConnected(true)} />
            </>
          )}

          <div className={styles.buttonGroup}>
            {step > 1 && (
              <button className={styles.btnBack} type="button" onClick={() => setStep((step - 1) as Step)}>
                Back
              </button>
            )}

            {step < 3 ? (
              <button
                className="btn-glow"
                style={{ flex: 1 }}
                type="button"
                disabled={step === 1 && !roleTitle.trim()}
                onClick={() => setStep((step + 1) as Step)}
              >
                Next
              </button>
            ) : (
              <button
                className="btn-glow"
                style={{ flex: 1 }}
                type="button"
                disabled={!telegramConnected || loading}
                onClick={handleFinish}
              >
                {loading ? "Completing setup..." : "Finish Onboarding"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
