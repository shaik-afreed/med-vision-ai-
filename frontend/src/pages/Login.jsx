import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser, registerUser, pingServer, getErrorMessage } from "../api/api";
import { useAuth } from "../context/AuthContext";
import Icon from "../components/Icon";

function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState("login"); // "login" | "register"

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [slowLoading, setSlowLoading] = useState(false);
  const [error, setError] = useState("");

  // "checking" -> "ready" normally; "waking" if the server takes more than
  // a couple of seconds to answer (a sleeping free-tier backend).
  const [serverState, setServerState] = useState("checking");

  useEffect(() => {
    let cancelled = false;
    const slowTimer = setTimeout(() => {
      if (!cancelled) setServerState((state) => (state === "checking" ? "waking" : state));
    }, 2500);

    // While a sleeping host starts it answers with a temporary error, so a
    // failed ping is retried for about two minutes before giving up.
    const startedAt = Date.now();
    let retryTimer;

    const check = () => {
      pingServer()
        .then(() => !cancelled && setServerState((state) => (state === "waking" ? "woke" : "ready")))
        .catch(() => {
          if (cancelled) return;
          if (Date.now() - startedAt > 120000) {
            setServerState("unreachable");
          } else {
            setServerState("waking");
            retryTimer = setTimeout(check, 4000);
          }
        });
    };
    check();

    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
      clearTimeout(retryTimer);
    };
  }, []);

  // Tell the user why a sign-in is taking long instead of leaving a spinner.
  useEffect(() => {
    if (!loading) {
      setSlowLoading(false);
      return undefined;
    }

    const timer = setTimeout(() => setSlowLoading(true), 4000);
    return () => clearTimeout(timer);
  }, [loading]);

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
      // Any HTTP answer (even a 401) proves the server is up, so drop a stale
      // "can't reach the server" notice.
      if (error?.response) setServerState("ready");

      if (mode === "login" && error?.response?.status === 401) {
        setError(
          "Email or password not recognised. If you signed up earlier, your account may have been removed when the demo server was reset - please create it again."
        );
        return;
      }

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
      <aside className="login-hero" aria-hidden="false">
        <div className="login-hero-inner">
          <div className="login-brand login-brand-light">
            <div className="login-logo">
              <Icon name="activity" size={22} strokeWidth={2.2} />
            </div>
            <div>
              <h1>MediVision</h1>
              <p>AI Healthcare Platform</p>
            </div>
          </div>

          <h2 className="login-hero-title">
            Faster, clearer chest X-ray screening support.
          </h2>
          <p className="login-hero-copy">
            Upload an X-ray or a lab report and get an explained result in seconds, with the reasoning,
            the reliability and a printable report for the reviewing clinician.
          </p>

          <ul className="login-features">
            <li>
              <Icon name="scan" size={18} />
              <span>
                <strong>Explained AI results</strong>
                Probability, heatmap and plain-language meaning
              </span>
            </li>
            <li>
              <Icon name="fileText" size={18} />
              <span>
                <strong>Lab report analysis</strong>
                Flags values outside their reference range
              </span>
            </li>
            <li>
              <Icon name="shield" size={18} />
              <span>
                <strong>Honest by design</strong>
                Shows uncertainty and limits, never fake certainty
              </span>
            </li>
          </ul>

          <p className="login-hero-footnote">
            A screening aid for qualified professionals. Not a diagnosis.
          </p>
        </div>
      </aside>

      <main className="login-panel">
        <div className="login-card">
          <div className="login-brand login-brand-mobile">
            <div className="login-logo">
              <Icon name="activity" size={22} strokeWidth={2.2} />
            </div>
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
                  autoComplete="name"
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
                autoComplete="email"
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
                autoComplete={mode === "register" ? "new-password" : "current-password"}
              />
              {mode === "register" && <small className="field-hint">At least 8 characters.</small>}
            </div>

            {error && (
              <div className="login-error" role="alert">
                {error}
              </div>
            )}

            {serverState === "waking" && (
              <div className="server-status waking" role="status">
                <span className="spinner spinner-sm" aria-hidden="true" />
                <span>
                  Waking up the secure server. The first sign-in after a quiet period can take up to a minute.
                </span>
              </div>
            )}

            {serverState === "woke" && (
              <div className="server-status ready" role="status">
                Server is ready.
              </div>
            )}

            {serverState === "unreachable" && (
              <div className="server-status unreachable" role="status">
                Can't reach the server. Check your connection, then try signing in again.
              </div>
            )}

            <button type="submit" className="login-button" disabled={loading}>
              {loading
                ? slowLoading
                  ? "Still working - the server is waking up..."
                  : mode === "login"
                    ? "Signing in..."
                    : "Creating account..."
                : mode === "login"
                  ? "Sign In"
                  : "Create Account"}
            </button>
          </form>

          <div className="login-notice">
            <Icon name="lock" size={16} />
            <span>
              <strong>Secure access</strong>
              Your account is protected using token-based authentication.
            </span>
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
      </main>
    </div>
  );
}

export default Login;
