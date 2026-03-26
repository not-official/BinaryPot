import React, { useState } from "react";
import { message } from "antd";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./Login.css";

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || "http://localhost:8000";

const Login = () => {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [inlineError, setInlineError] = useState("");

  const getNiceErrorMessage = (err) => {
    if (!err?.response) {
      return "Server is not reachable. Please check if backend is running and CORS is configured.";
    }

    const status = err.response.status;
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err?.response?.data?.error;

    if (status === 401) {
      return detail || "Unauthorized: Invalid email or password, or your account is not approved yet.";
    }

    if (status === 403) {
      return detail || "Forbidden: Your account is not allowed to access the system.";
    }

    if (status === 404) {
      return detail || "Account not found. Please request access first.";
    }

    if (status === 409) {
      return detail || "Conflict: Account state issue. Try again or contact admin.";
    }

    if (status === 422) {
      return "Invalid input. Please check your email and password fields.";
    }

    if (status === 429) {
      return "Too many attempts. Please wait a bit and try again.";
    }

    if (status >= 500) {
      return "Server error. Please try again later.";
    }

    return detail || "Login failed. Please try again.";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setInlineError("");

    try {
      const cleanedEmail = email.trim().toLowerCase();

      const res = await axios.post(
        `${API_BASE}/auth/login`,
        {
          email: cleanedEmail,
          password,
        },
        {
          headers: { "Content-Type": "application/json" },
          timeout: 15000,
        }
      );

      const token = res?.data?.access_token;

      if (!token) {
        const msg = "Login failed: token missing from response.";
        setInlineError(msg);
        message.error(msg);
        return;
      }

      sessionStorage.setItem("token", token);
      message.success("Login successful");
      navigate("/dashboard");
    } catch (err) {
      console.error("LOGIN ERROR →", err?.response?.data || err?.message || err);
      const niceMsg = getNiceErrorMessage(err);
      setInlineError(niceMsg);
      message.error(niceMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="loginOverlay">
      <div className="loginBox">
        <div className="loginHeader">
          <div className="loginDots">
            <span className="dotR"></span>
            <span className="dotY"></span>
            <span className="dotG"></span>
          </div>
          <div className="loginTitle">binarypot — /auth/login</div>
        </div>

        <div className="loginBody">
          <div className="loginLogo">
            <h1>⬡ BinaryPot</h1>
            <p>LLM-POWERED SSH HONEYPOT v1.0.0</p>
          </div>

          {inlineError ? (
            <div className="loginHint loginErrorText">
              {inlineError}
            </div>
          ) : null}

          <form onSubmit={handleSubmit}>
            <div className="loginField">
              <label>EMAIL</label>
              <input
                type="email"
                value={email}
                placeholder="you@example.com"
                autoComplete="email"
                onChange={(e) => setEmail(e.target.value)}
                className={inlineError ? "inputError" : ""}
              />
            </div>

            <div className="loginField">
              <label>PASSWORD</label>
              <input
                type="password"
                value={password}
                placeholder="Enter password"
                autoComplete="current-password"
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button type="submit" className="loginBtn" disabled={loading}>
              {loading ? "AUTHENTICATING..." : "AUTHENTICATE →"}
            </button>
          </form>

          <div className="loginFooterText">
            <span>DON&apos;T HAVE AN ACCOUNT? </span>
            <button
              type="button"
              className="loginLinkBtn"
              onClick={() => navigate("/signup-request")}
            >
              REQUEST ACCESS
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;