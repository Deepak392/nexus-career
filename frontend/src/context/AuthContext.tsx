
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  getCurrentUser,
  getAccessToken,
  clearAuthTokens,
  type AuthUser,
  type LoginRole,
} from "../services/auth";

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string, expectedRole: LoginRole) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string
  ) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      if (!getAccessToken()) {
        if (active) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const currentUser = await getCurrentUser();

        if (active) {
          setUser(currentUser);
        }
      } catch {
        clearAuthTokens();

        if (active) {
          setUser(null);
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void restoreSession();

    return () => {
      active = false;
    };
  }, []);

  async function handleLogin(
    username: string,
    password: string,
    expectedRole: LoginRole
  ) {
    const loggedInUser = await apiLogin(username, password);
    const roleLabels: Record<LoginRole, string> = {
      STUDENT: "student",
      ALUMNI: "alumni",
      RECRUITER: "recruiter",
    };

    // The selector validates the three portal types shown on the login page.
    // Privileged accounts keep their existing credential-based login flow.
    if (
      loggedInUser.role in roleLabels &&
      loggedInUser.role !== expectedRole
    ) {
      await apiLogout();

      const actualRole = roleLabels[loggedInUser.role as LoginRole];
      const expectedRoleLabel = actualRole[0].toUpperCase() + actualRole.slice(1);
      throw new Error(
        `These credentials belong to a ${actualRole} account. Select "${expectedRoleLabel}" to sign in.`
      );
    }

    setUser(loggedInUser);
  }

  async function handleRegister(
    username: string,
    email: string,
    password: string
  ) {
    const registeredUser = await apiRegister(
      username,
      email,
      password
    );

    setUser(registeredUser);
  }

  async function handleLogout() {
    await apiLogout();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: Boolean(user),
        login: handleLogin,
        register: handleRegister,
        logout: handleLogout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
