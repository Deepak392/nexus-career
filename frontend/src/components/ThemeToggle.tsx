import { useTheme } from "../context/ThemeContext";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const nextTheme = isDark ? "light" : "dark";

  return (
    <button
      className="theme-toggle"
      type="button"
      onClick={toggleTheme}
      aria-label={"Switch to " + nextTheme + " mode"}
      aria-pressed={isDark}
      title={"Switch to " + nextTheme + " mode"}
    >
      <span className="theme-toggle-icon" aria-hidden="true">
        {isDark ? "☀" : "☾"}
      </span>
      <span>{isDark ? "Light mode" : "Dark mode"}</span>
      <span className="theme-toggle-state">{isDark ? "On" : "Off"}</span>
    </button>
  );
}
