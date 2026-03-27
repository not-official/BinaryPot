import React, { useState } from "react";
import { message, Modal } from "antd";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import "./Signup.css";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const Signup = () => {
  const navigate = useNavigate();

  const [current, setCurrent] = useState(0);
  const [loading, setLoading] = useState(false);
  const [successOpen, setSuccessOpen] = useState(false);

  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
    organization: "",
    role: "",
    usage: "",
    plan: "",
    card_name: "",
    card_number: "",
    terms: false,
  });

  const [errors, setErrors] = useState({});

  const steps = ["Account", "Organization", "Plan", "Review"];

  const updateField = (name, value) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    setErrors((prev) => ({
      ...prev,
      [name]: "",
    }));
  };

  const validateStep = () => {
    const newErrors = {};

    if (current === 0) {
      if (!formData.full_name.trim()) newErrors.full_name = "Please enter your full name";
      if (!formData.email.trim()) {
        newErrors.email = "Please enter your email";
      } else if (!/^\S+@\S+\.\S+$/.test(formData.email)) {
        newErrors.email = "Enter a valid email address";
      }

      if (!formData.password) {
        newErrors.password = "Please create a password";
      } else if (formData.password.length < 8) {
        newErrors.password = "Minimum 8 characters";
      }

      if (!formData.confirm_password) {
        newErrors.confirm_password = "Please confirm your password";
      } else if (formData.password !== formData.confirm_password) {
        newErrors.confirm_password = "Passwords do not match";
      }
    }

    if (current === 1) {
      if (!formData.organization.trim()) newErrors.organization = "Please enter your organization";
      if (!formData.role) newErrors.role = "Please select your role";
      if (!formData.usage) newErrors.usage = "Please select intended usage";
    }

    if (current === 2) {
      if (!formData.plan) newErrors.plan = "Please select a plan";

      if (formData.card_number && !/^[0-9 ]+$/.test(formData.card_number)) {
        newErrors.card_number = "Use digits and spaces only";
      }
    }

    if (current === 3) {
      if (!formData.terms) newErrors.terms = "You must accept the terms to continue";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const next = () => {
    if (validateStep()) {
      setCurrent((prev) => prev + 1);
    }
  };

  const prev = () => {
    setCurrent((prev) => prev - 1);
  };

  const submit = async () => {
    if (!validateStep()) return;

    setLoading(true);

    try {
      const payload = {
        full_name: formData.full_name.trim(),
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
        organization: formData.organization.trim(),
        role: formData.role,
        usage: formData.usage,
        plan: formData.plan,
        card_name: formData.card_name.trim(),
        card_number: formData.card_number.trim(),
        terms: formData.terms,
      };

      await axios.post(`${API_BASE}/signup-request`, payload, {
        headers: { "Content-Type": "application/json" },
      });

      message.success("Signup request submitted for review");

      setFormData({
        full_name: "",
        email: "",
        password: "",
        confirm_password: "",
        organization: "",
        role: "",
        usage: "",
        plan: "",
        card_name: "",
        card_number: "",
        terms: false,
      });

      setCurrent(0);
      setErrors({});
      setSuccessOpen(true);
    } catch (err) {
      const apiMsg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        "Signup failed";

      console.error("SIGNUP ERROR →", err?.response?.data || err?.message || err);
      message.error(apiMsg);
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = () => {
    if (current === 0) {
      return (
        <>
          <div className="signupSectionTitle">ACCOUNT INFORMATION</div>

          <div className="signupField">
            <label>FULL NAME</label>
            <input
              type="text"
              placeholder="John Doe"
              value={formData.full_name}
              onChange={(e) => updateField("full_name", e.target.value)}
              className={errors.full_name ? "inputError" : ""}
            />
            {errors.full_name && <div className="fieldError">{errors.full_name}</div>}
          </div>

          <div className="signupField">
            <label>EMAIL</label>
            <input
              type="email"
              placeholder="you@example.com"
              value={formData.email}
              onChange={(e) => updateField("email", e.target.value)}
              className={errors.email ? "inputError" : ""}
            />
            {errors.email && <div className="fieldError">{errors.email}</div>}
          </div>

          <div className="signupGrid">
            <div className="signupField">
              <label>PASSWORD</label>
              <input
                type="password"
                placeholder="Minimum 8 characters"
                value={formData.password}
                onChange={(e) => updateField("password", e.target.value)}
                className={errors.password ? "inputError" : ""}
              />
              {errors.password && <div className="fieldError">{errors.password}</div>}
            </div>

            <div className="signupField">
              <label>CONFIRM PASSWORD</label>
              <input
                type="password"
                placeholder="Re-enter password"
                value={formData.confirm_password}
                onChange={(e) => updateField("confirm_password", e.target.value)}
                className={errors.confirm_password ? "inputError" : ""}
              />
              {errors.confirm_password && (
                <div className="fieldError">{errors.confirm_password}</div>
              )}
            </div>
          </div>
        </>
      );
    }

    if (current === 1) {
      return (
        <>
          <div className="signupSectionTitle">ORGANIZATION DETAILS</div>

          <div className="signupField">
            <label>ORGANIZATION</label>
            <input
              type="text"
              placeholder="Uni / Company / Lab"
              value={formData.organization}
              onChange={(e) => updateField("organization", e.target.value)}
              className={errors.organization ? "inputError" : ""}
            />
            {errors.organization && (
              <div className="fieldError">{errors.organization}</div>
            )}
          </div>

          <div className="signupGrid">
            <div className="signupField">
              <label>ROLE</label>
              <select
                value={formData.role}
                onChange={(e) => updateField("role", e.target.value)}
                className={errors.role ? "inputError" : ""}
              >
                <option value="">Select role</option>
                <option value="security_engineer">Security Engineer</option>
                <option value="soc_analyst">SOC Analyst</option>
                <option value="researcher">Researcher</option>
                <option value="student">Student</option>
              </select>
              {errors.role && <div className="fieldError">{errors.role}</div>}
            </div>

            <div className="signupField">
              <label>INTENDED USAGE</label>
              <select
                value={formData.usage}
                onChange={(e) => updateField("usage", e.target.value)}
                className={errors.usage ? "inputError" : ""}
              >
                <option value="">Select usage</option>
                <option value="production">Production</option>
                <option value="testing">Testing</option>
                <option value="academic">Academic</option>
              </select>
              {errors.usage && <div className="fieldError">{errors.usage}</div>}
            </div>
          </div>
        </>
      );
    }

    if (current === 2) {
      return (
        <>
          <div className="signupSectionTitle">PLAN & BILLING</div>

          <div className="signupField">
            <label>PLAN</label>
            <select
              value={formData.plan}
              onChange={(e) => updateField("plan", e.target.value)}
              className={errors.plan ? "inputError" : ""}
            >
              <option value="">Select plan</option>
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
            {errors.plan && <div className="fieldError">{errors.plan}</div>}
          </div>

          <div className="signupHint">
            Demo billing fields are optional. Leave them blank if not needed.
          </div>

          <div className="signupGrid">
            <div className="signupField">
              <label>NAME ON CARD</label>
              <input
                type="text"
                placeholder="Demo only"
                value={formData.card_name}
                onChange={(e) => updateField("card_name", e.target.value)}
              />
            </div>

            <div className="signupField">
              <label>CARD NUMBER</label>
              <input
                type="text"
                placeholder="4242 4242 4242 4242"
                value={formData.card_number}
                onChange={(e) => updateField("card_number", e.target.value)}
                className={errors.card_number ? "inputError" : ""}
              />
              {errors.card_number && <div className="fieldError">{errors.card_number}</div>}
            </div>
          </div>
        </>
      );
    }

    return (
      <>
        <div className="signupSectionTitle">REVIEW & SUBMIT</div>

        <div className="reviewGrid">
          <div className="reviewItem">
            <span className="reviewLabel">FULL NAME</span>
            <span className="reviewValue">{formData.full_name || "-"}</span>
          </div>

          <div className="reviewItem">
            <span className="reviewLabel">EMAIL</span>
            <span className="reviewValue">{formData.email || "-"}</span>
          </div>

          <div className="reviewItem">
            <span className="reviewLabel">ORGANIZATION</span>
            <span className="reviewValue">{formData.organization || "-"}</span>
          </div>

          <div className="reviewItem">
            <span className="reviewLabel">ROLE</span>
            <span className="reviewValue">{formData.role || "-"}</span>
          </div>

          <div className="reviewItem">
            <span className="reviewLabel">USAGE</span>
            <span className="reviewValue">{formData.usage || "-"}</span>
          </div>

          <div className="reviewItem">
            <span className="reviewLabel">PLAN</span>
            <span className="reviewValue">{formData.plan || "-"}</span>
          </div>
        </div>

        <div className="reviewBox">
          <div className="reviewBoxTitle">SAFE PAYLOAD PREVIEW</div>
          <pre>
{JSON.stringify(
  {
    ...formData,
    password: formData.password ? "********" : undefined,
    confirm_password: undefined,
    card_number: formData.card_number ? "**** **** **** ****" : undefined,
  },
  null,
  2
)}
          </pre>
        </div>

        <label className="signupCheckbox">
          <input
            type="checkbox"
            checked={formData.terms}
            onChange={(e) => updateField("terms", e.target.checked)}
          />
          <span>I agree to the Terms, Privacy Policy and responsible usage</span>
        </label>
        {errors.terms && <div className="fieldError">{errors.terms}</div>}
      </>
    );
  };

  return (
    <div className="signupOverlay">
      <Modal
        open={successOpen}
        title="Request sent"
        onCancel={() => setSuccessOpen(false)}
        footer={null}
        centered
      >
        <p className="signupModalText">
          Your signup request has been sent for admin review. You&apos;ll be notified
          by email when it&apos;s approved or rejected.
        </p>

        <div className="signupModalActions">
          <button
            className="signupSecondaryBtn"
            onClick={() => setSuccessOpen(false)}
          >
            CLOSE
          </button>
          <button
            className="signupPrimaryBtn"
            onClick={() => {
              setSuccessOpen(false);
              navigate("/");
            }}
          >
            CONTINUE →
          </button>
        </div>
      </Modal>

      <div className="signupBox">
        <div className="signupHeader">
          <div className="signupDots">
            <span className="dotR"></span>
            <span className="dotY"></span>
            <span className="dotG"></span>
          </div>
          <div className="signupTitle">binarypot — /auth/signup-request</div>
        </div>

        <div className="signupBody">
          <div className="signupLogo">
            <Link to="/" className="loginLogoLink">
  <h1>⬡ BinaryPot</h1>
</Link>
            <p>ADMIN ACCESS REQUEST PORTAL</p>
          </div>

          <div className="stepTracker">
            {steps.map((step, index) => (
              <div
                key={step}
                className={`stepItem ${current === index ? "active" : ""} ${
                  current > index ? "done" : ""
                }`}
              >
                <div className="stepNumber">{index + 1}</div>
                <div className="stepText">{step}</div>
              </div>
            ))}
          </div>

          <div className="signupPanel">
            {renderStepContent()}

            <div className="signupButtons">
              <button
                type="button"
                className="signupSecondaryBtn"
                onClick={() => current === 0 ? navigate("/") : prev()}
                disabled={loading}
              >
                ← BACK
              </button>

              {current < 3 ? (
                <button
                  type="button"
                  className="signupPrimaryBtn"
                  onClick={next}
                >
                  NEXT →
                </button>
              ) : (
                <button
                  type="button"
                  className="signupPrimaryBtn"
                  onClick={submit}
                  disabled={loading}
                >
                  {loading ? "SUBMITTING..." : "SUBMIT REQUEST →"}
                </button>
              )}
            </div>

            <div className="signupFooterText">
              <span>ALREADY HAVE ACCESS? </span>
              <button
                type="button"
                className="signupLinkBtn"
                onClick={() => navigate("/login")}
              >
                GO TO LOGIN
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Signup;