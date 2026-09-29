import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser, registerUser, getErrorMessage } from "../api/api";
import { useAuth } from "../context/AuthContext";

function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState("login"); // "login" | "register"

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function switchMode(nextMode) {
    setMode(nextMode);
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      if (mode === "register") {
        await registerUser(name, email, password);
      }

      const data = await loginUser(email, password);
      login(data.access_token);
      navigate("/", { replace: true });
    } catch (error) {
      setError(
        getErrorMessage(
          error,
          mode === "register" ? "Unable to create account." : "Invalid email or password."
        )
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-logo">M</div>
          <div>
            <h1>MediVision</h1>
            <p>AI Healthcare Platform</p>
          </div>
        </div>

        <div className="login-heading">
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p>
            {mode === "login"
              ? "Sign in to access your healthcare dashboard."
              : "Register as a doctor to start using MediVision AI."}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <div className="form-group">
              <label htmlFor="login-name">Full Name</label>
              <input
                type="text"
                placeholder="Dr. Jane Smith"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                id="login-name"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={mode === "register" ? 8 : undefined}
              required
            />
          </div>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-button" disabled={loading}>
            {loading
              ? mode === "login"
                ? "Signing in..."
                : "Creating account..."
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>

        <div className="login-notice">
          <strong>🔒 Secure access</strong>
          <span>Your account is protected using token-based authentication.</span>
        </div>

        <div className="login-switch">
          {mode === "login" ? (
            <span>
              New to MediVision?{" "}
              <button type="button" onClick={() => switchMode("register")}>
                Create an account
              </button>
            </span>
          ) : (
            <span>
              Already have an account?{" "}
              <button type="button" onClick={() => switchMode("login")}>
                Sign in
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default Login;
