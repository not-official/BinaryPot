import React, { useState } from "react";
import { Card, Form, Input, Button, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./Login.css";

const { Title, Text } = Typography;

const API_BASE =
  import.meta?.env?.VITE_API_BASE_URL || "http://localhost:8000";

const Login = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const onFinish = async (values) => {
    setLoading(true);

    try {
      const res = await axios.post(
        `${API_BASE}/auth/login`,
        {
          email: values.email.trim().toLowerCase(),
          password: values.password,
        },
        { headers: { "Content-Type": "application/json" } }
      );

      const token = res?.data?.access_token;
      if (!token) {
        message.error("Login failed: token missing");
        return;
      }

      sessionStorage.setItem("token", token);
      message.success("Login successful");
      navigate("/dashboard");
    } catch (err) {
      const apiMsg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        "Invalid email or password";
      message.error(apiMsg);
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
            <Input
              placeholder="you@example.com"
              autoComplete="email"
            />
          </Form.Item>

          <Form.Item
            label="Password"
            name="password"
            rules={[
              { required: true, message: "Please enter your password" },
            ]}
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
