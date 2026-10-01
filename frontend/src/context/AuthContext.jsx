import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getProfile } from "../api/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(localStorage.getItem("access_token"))
  );
  const [user, setUser] = useState(null);

  const login = useCallback((token) => {
    localStorage.setItem("access_token", token);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    setIsAuthenticated(false);
    setUser(null);
  }, []);

  // api.js dispatches this whenever a request comes back 401, so an
  // expired/invalid token logs the user out from anywhere in the app
  // instead of surfacing a raw error string.
  useEffect(() => {
    function handleUnauthorized() {
      setIsAuthenticated(false);
      setUser(null);
    }

    window.addEventListener("medivision:unauthorized", handleUnauthorized);
    return () =>
      window.removeEventListener("medivision:unauthorized", handleUnauthorized);
  }, []);

  // The signed-in user's name/email, for the sidebar and greetings. A
  // failure here is cosmetic: the UI falls back to generic wording.
  useEffect(() => {
    if (!isAuthenticated) return undefined;

    let cancelled = false;
    getProfile()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}

export function initialsOf(name) {
  if (!name) return "DR";
  const parts = name.replace(/^dr\.?\s+/i, "").trim().split(/\s+/);
  return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase() || "DR";
}
