import { createContext, useContext, useEffect, useState, useCallback } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(localStorage.getItem("access_token"))
  );

  const login = useCallback((token) => {
    localStorage.setItem("access_token", token);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    setIsAuthenticated(false);
  }, []);

  // api.js dispatches this whenever a request comes back 401, so an
  // expired/invalid token logs the user out from anywhere in the app
  // instead of surfacing a raw error string.
  useEffect(() => {
    function handleUnauthorized() {
      setIsAuthenticated(false);
    }

    window.addEventListener("medivision:unauthorized", handleUnauthorized);
    return () =>
      window.removeEventListener("medivision:unauthorized", handleUnauthorized);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
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
