import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { logoutUser } from "../api/auth";
import ThemeToggle from "./ThemeToggle";
import styles from "./Header.module.css";

export default function Header() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    try {
      await logoutUser();
      setUser(null);
      navigate("/login");
    } catch (e) {
      // ignore
    }
  };

  const isActive = (path: string) => {
    return location.pathname === path ? styles.activeLink : "";
  };

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <Link to={user?.onboarding_complete ? "/dashboard" : "/"} className={styles.logo}>
          🔎 Job Radar
        </Link>

        <nav className={styles.nav}>
          <div className={styles.linksGroup}>
            {user ? (
              <>
                {user.onboarding_complete && (
                  <>
                    <Link to="/dashboard" className={`${styles.navLink} ${isActive("/dashboard")}`}>
                      Dashboard
                    </Link>
                    <Link to="/settings" className={`${styles.navLink} ${isActive("/settings")}`}>
                      Settings
                    </Link>
                    {user.is_admin && (
                      <Link to="/admin" className={`${styles.navLink} ${isActive("/admin")}`}>
                        Admin
                      </Link>
                    )}
                  </>
                )}
                <button onClick={handleLogout} className={styles.btnSignout}>
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link to="/" className={`${styles.navLink} ${isActive("/")}`}>
                  Home
                </Link>
                <Link to="/login" className={`${styles.navLink} ${isActive("/login")}`}>
                  Sign In
                </Link>
                <Link to="/register" className={styles.btnRegister}>
                  Sign Up
                </Link>
              </>
            )}
          </div>
          <div className={styles.divider}></div>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
