import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { ThemeContext, type Theme } from "./ThemeContext";

const THEME_STORAGE_KEY = "nexus-career-theme";

function getInitialTheme(): Theme {
  let savedTheme: string | null = null;

  try {
    savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    // Continue with the operating-system preference when storage is unavailable.
  }

  const theme: Theme =
    savedTheme === "light" || savedTheme === "dark"
      ? savedTheme
      : window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";

  // Apply the attribute before the first paint to avoid a light-theme flash.
  document.documentElement.dataset.theme = theme;
  return theme;
}

export default function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;

    const themeColor = theme === "dark" ? "#0c1220" : "#f5f6fa";
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", themeColor);

    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // The selected theme still works for the current session.
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));
  }, []);

  const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
