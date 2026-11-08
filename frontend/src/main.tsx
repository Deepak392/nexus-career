import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";
import "./features/opportunities/pages/Eligibility.css";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import ThemeProvider from "./context/ThemeProvider";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>
);
