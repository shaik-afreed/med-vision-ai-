import { useState } from "react";
import { loginUser } from "../api/api";

function Login({ onLogin }) {

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  async function handleSubmit(event) {

    event.preventDefault();

    setError("");
    setLoading(true);

    try {

      const data = await loginUser(
        email,
        password
      );

      localStorage.setItem(
        "access_token",
        data.access_token
      );

      onLogin();

    } catch (error) {

      if (error.response) {

        setError(
          error.response.data?.detail ||
          "Invalid email or password."
        );

      } else {

        setError(
          "Unable to connect to the server."
        );

      }

    } finally {

      setLoading(false);

    }
  }


  return (
    <div className="login-page">

      <div className="login-card">

        <div className="login-brand">

          <div className="login-logo">
            M
          </div>

          <div>
            <h1>MediVision</h1>
            <p>AI Healthcare Platform</p>
          </div>

        </div>


        <div className="login-heading">

          <h2>Welcome back</h2>

          <p>
            Sign in to access your healthcare dashboard.
          </p>

        </div>


        <form onSubmit={handleSubmit}>

          <div className="form-group">

            <label>
              Email
            </label>

            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              required
            />

          </div>


          <div className="form-group">

            <label>
              Password
            </label>

            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              required
            />

          </div>


          {error && (
            <div className="login-error">
              {error}
            </div>
          )}


          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >

            {loading
              ? "Signing in..."
              : "Sign In"
            }

          </button>

        </form>


        <div className="login-notice">

          <strong>🔒 Secure access</strong>

          <span>
            Your account is protected using
            token-based authentication.
          </span>

        </div>

      </div>

    </div>
  );
}

export default Login;