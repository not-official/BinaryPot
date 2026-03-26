import React, { useState } from "react";
import { Card, Form, Input, Button, Typography, message, Alert } from "antd";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./Login.css";

const { Title, Text } = Typography;

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || "http://localhost:8000";

const Login = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  // ✅ NEW: inline error box (nice UX)
  const [inlineError, setInlineError] = useState("");

  // ✅ map HTTP errors to user-friendly messages
  const getNiceErrorMessage = (err) => {
    // network error (server down / CORS / connection refused)
    if (!err?.response) {
      return "Server is not reachable. Please check if backend is running and CORS is configured.";
    }

    const status = err.response.status;
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err?.response?.data?.error;

    // common auth cases
    if (status === 401) {
      // backend usually uses 401 for invalid credentials
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

  const onFinish = async (values) => {
    setLoading(true);
    setInlineError("");

    try {
      const email = values.email?.trim()?.toLowerCase();

      const res = await axios.post(
        `${API_BASE}/auth/login`,
        {
          email,
          password: values.password,
        },
        {
          headers: { "Content-Type": "application/json" },
          timeout: 15000, // ✅ NEW: prevents infinite waiting
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

      // ✅ show both: toast + inline message
      setInlineError(niceMsg);
      message.error(niceMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-bg" />

      <Card className="login-card" bordered={false}>
        <div className="login-header">
          <div className="brand-pill">BinaryPot</div>
          <Title level={3} className="login-title">
            Welcome back
          </Title>
          <Text type="secondary" className="login-subtitle">
            Sign in to access your dashboard
          </Text>
        </div>

        {/* ✅ NEW: inline error for unauthorized / pending approval */}
        {inlineError ? (
          <Alert
            style={{ marginBottom: 14 }}
            type="error"
            showIcon
            message=""
            description={inlineError}
          />
        ) : null}

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          className="login-form"
          requiredMark={false}
        >
          <Form.Item
            label="Email"
            name="email"
            rules={[
              { required: true, message: "Please enter your email" },
              { type: "email", message: "Enter a valid email address" },
            ]}
          >
            <Input placeholder="you@example.com" autoComplete="email" />
          </Form.Item>

          <Form.Item
            label="Password"
            name="password"
            rules={[{ required: true, message: "Please enter your password" }]}
          >
            <Input.Password
              placeholder="Enter password"
              autoComplete="current-password"
            />
          </Form.Item>

          <Button type="primary" htmlType="submit" block loading={loading}>
            Login
          </Button>

          <div className="login-footer">
            <Text type="secondary">Don&apos;t have an account?</Text>
            <Button
              type="link"
              className="link-btn"
              onClick={() => navigate("/signup-request")}
            >
              Request access
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
