import React, { useMemo, useState } from "react";
import {
  Card,
  Form,
  Input,
  Button,
  Typography,
  Select,
  Checkbox,
  Steps,
  Divider,
  Row,
  Col,
  message,
  Modal, // ✅ added
} from "antd";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./Signup.css";

const { Title, Text } = Typography;
const { Option } = Select;

const API_BASE = import.meta?.env?.VITE_API_BASE_URL || "http://localhost:8000";

const Signup = () => {
  const [current, setCurrent] = useState(0);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  // ✅ added: success modal state
  const [successOpen, setSuccessOpen] = useState(false);

  const stepFields = useMemo(
    () => [
      ["full_name", "email", "password", "confirm_password"],
      ["organization", "role", "usage"],
      ["plan", "card_name", "card_number"],
      ["terms"],
    ],
    []
  );

  const next = async () => {
    try {
      await form.validateFields(stepFields[current]);
      setCurrent((c) => c + 1);
    } catch {
      // validation failed
    }
  };

  const prev = () => setCurrent((c) => c - 1);

  const submit = async () => {
    setLoading(true);

    try {
      // Validate everything (including terms)
      await form.validateFields();

      // IMPORTANT: true = include unmounted fields
      const values = form.getFieldsValue(true);

      // remove confirm_password
      const { confirm_password, ...payload } = values;

      // safe log
      const { password, card_number, ...safeLog } = payload;
      if (import.meta?.env?.DEV) console.log("SIGNUP PAYLOAD (safe) →", safeLog);

      await axios.post(`${API_BASE}/signup-request`, payload, {
        headers: { "Content-Type": "application/json" },
      });

      message.success("Signup request submitted for review");
      form.resetFields();

      // ✅ changed: show modal instead of immediate navigation
      setSuccessOpen(true);
    } catch (err) {
      const apiMsg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        (err?.errorFields ? "Please fix the highlighted fields." : "Signup failed");

      console.error("SIGNUP ERROR →", err?.response?.data || err?.message || err);
      message.error(apiMsg);
    } finally {
      setLoading(false);
    }
  };

  const renderStep = () => {
    // STEP 1
    if (current === 0) {
      return (
        <>
          <Divider>Account Information</Divider>

          <Form.Item
            name="full_name"
            label="Full Name"
            rules={[{ required: true, message: "Please enter your full name" }]}
          >
            <Input placeholder="John Doe" autoComplete="name" />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: "Please enter your email" },
              { type: "email", message: "Enter a valid email address" },
            ]}
          >
            <Input placeholder="you@example.com" autoComplete="email" />
          </Form.Item>

          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item
                name="password"
                label="Password"
                rules={[
                  { required: true, message: "Please create a password" },
                  { min: 8, message: "Minimum 8 characters" },
                ]}
                hasFeedback
              >
                <Input.Password
                  placeholder="Minimum 8 characters"
                  autoComplete="new-password"
                />
              </Form.Item>
            </Col>

            <Col xs={24} sm={12}>
              <Form.Item
                name="confirm_password"
                label="Confirm Password"
                dependencies={["password"]}
                hasFeedback
                rules={[
                  { required: true, message: "Please confirm your password" },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue("password") === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error("Passwords do not match"));
                    },
                  }),
                ]}
              >
                <Input.Password placeholder="Re-enter password" />
              </Form.Item>
            </Col>
          </Row>
        </>
      );
    }

    // STEP 2
    if (current === 1) {
      return (
        <>
          <Divider>Organization Details</Divider>

          <Form.Item
            name="organization"
            label="Organization"
            rules={[{ required: true, message: "Please enter your organization" }]}
          >
            <Input placeholder="Uni / Company / Lab" />
          </Form.Item>

          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item
                name="role"
                label="Role"
                rules={[{ required: true, message: "Please select your role" }]}
              >
                <Select placeholder="Select role">
                  <Option value="security_engineer">Security Engineer</Option>
                  <Option value="soc_analyst">SOC Analyst</Option>
                  <Option value="researcher">Researcher</Option>
                  <Option value="student">Student</Option>
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12}>
              <Form.Item
                name="usage"
                label="Intended Usage"
                rules={[{ required: true, message: "Please select intended usage" }]}
              >
                <Select placeholder="Select usage">
                  <Option value="production">Production</Option>
                  <Option value="testing">Testing</Option>
                  <Option value="academic">Academic</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </>
      );
    }

    // STEP 3
    if (current === 2) {
      return (
        <>
          <Divider>Plan & Billing (Demo)</Divider>

          <Form.Item
            name="plan"
            label="Plan"
            rules={[{ required: true, message: "Please select a plan" }]}
          >
            <Select placeholder="Select plan">
              <Option value="free">Free</Option>
              <Option value="pro">Pro</Option>
              <Option value="enterprise">Enterprise</Option>
            </Select>
          </Form.Item>

          <div className="demo-note">
            Demo billing fields (optional). Leave blank if not needed.
          </div>

          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item name="card_name" label="Name on Card">
                <Input placeholder="Demo only" autoComplete="cc-name" />
              </Form.Item>
            </Col>

            <Col xs={24} sm={12}>
              <Form.Item
                name="card_number"
                label="Card Number"
                rules={[
                  {
                    pattern: /^[0-9 ]*$/,
                    message: "Use digits and spaces only",
                  },
                ]}
              >
                <Input
                  placeholder="4242 4242 4242 4242"
                  autoComplete="cc-number"
                />
              </Form.Item>
            </Col>
          </Row>
        </>
      );
    }

    // STEP 4 (Review) — IMPORTANT: read values from form store
    const values = form.getFieldsValue(true);

    return (
      <>
        <Divider>Review & Submit</Divider>

        <div className="review-grid">
          <div className="review-item">
            <span className="review-label">Full Name</span>
            <span className="review-value">{values.full_name || "-"}</span>
          </div>

          <div className="review-item">
            <span className="review-label">Email</span>
            <span className="review-value">{values.email || "-"}</span>
          </div>

          <div className="review-item">
            <span className="review-label">Organization</span>
            <span className="review-value">{values.organization || "-"}</span>
          </div>

          <div className="review-item">
            <span className="review-label">Role</span>
            <span className="review-value">{values.role || "-"}</span>
          </div>

          <div className="review-item">
            <span className="review-label">Usage</span>
            <span className="review-value">{values.usage || "-"}</span>
          </div>

          <div className="review-item">
            <span className="review-label">Plan</span>
            <span className="review-value">{values.plan || "-"}</span>
          </div>
        </div>

        <div className="review-box">
          <div className="review-box-title">Raw Payload Preview (safe)</div>
          <pre>
            {JSON.stringify(
              {
                ...values,
                password: values.password ? "********" : undefined,
                confirm_password: undefined,
                card_number: values.card_number ? "**** **** **** ****" : undefined,
              },
              null,
              2
            )}
          </pre>
        </div>

        <Form.Item
          name="terms"
          valuePropName="checked"
          rules={[
            {
              validator: (_, value) =>
                value
                  ? Promise.resolve()
                  : Promise.reject(new Error("You must accept the terms to continue.")),
            },
          ]}
        >
          <Checkbox>I agree to the Terms, Privacy Policy and responsible usage</Checkbox>
        </Form.Item>
      </>
    );
  };

  return (
    <div className="signup-page">
      <div className="signup-bg" />

      {/* ✅ added: Success Modal */}
      <Modal
        open={successOpen}
        title="Request sent"
        onCancel={() => setSuccessOpen(false)}
        footer={[
          <Button key="close" onClick={() => setSuccessOpen(false)}>
            Close
          </Button>,
          <Button
            key="login"
            type="primary"
            onClick={() => {
              setSuccessOpen(false);
              navigate("/login");
            }}
          >
            Continue
          </Button>,
        ]}
      >
        <Text>
          Your signup request has been sent for admin review. You’ll be notified by
          email when it’s approved or rejected.
        </Text>
      </Modal>

      <Card className="signup-card" bordered={false}>
        <div className="signup-header">
          <div className="brand-pill">BinaryPot</div>
          <Title level={3} className="signup-title">
            Admin Signup
          </Title>
          <Text type="secondary" className="signup-subtitle">
            All admin accounts require manual verification.
          </Text>
        </div>

        <Steps current={current} size="small" className="signup-steps">
          <Steps.Step title="Account" />
          <Steps.Step title="Organization" />
          <Steps.Step title="Plan" />
          <Steps.Step title="Review" />
        </Steps>

        <Form
          layout="vertical"
          form={form}
          className="signup-form"
          preserve={true}
          requiredMark={false}
        >
          {renderStep()}

          <div className="signup-buttons">
            <Button disabled={current === 0} onClick={prev}>
              Back
            </Button>

            {current < 3 ? (
              <Button type="primary" onClick={next}>
                Next
              </Button>
            ) : (
              <Button type="primary" loading={loading} onClick={submit}>
                Submit Request
              </Button>
            )}
          </div>

          <div className="footnote">
            <Text type="secondary">
              Tip: Use a real email, approval details will be sent there.
            </Text>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default Signup;
