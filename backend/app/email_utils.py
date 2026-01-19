# app/email_utils.py
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

def send_signup_email(payload: dict, approve_url: str, reject_url: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_email = os.getenv("SMTP_EMAIL", "binarypot101@gmail.com")
    smtp_password = os.getenv("SMTP_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL", smtp_email)

    if not smtp_password:
        raise RuntimeError("SMTP_PASSWORD env var missing (use Gmail App Password)")

    full_name = payload.get("full_name", "-")
    email = payload.get("email", "-")
    organization = payload.get("organization", "-")
    role = payload.get("role", "-")
    usage = payload.get("usage", "-")
    plan = payload.get("plan", "-")
    submitted_at = datetime.utcnow().isoformat()

    # Plain text fallback (always include)
    text = f"""
A new admin signup request has been submitted.

--- Account ---
Full Name: {full_name}
Email: {email}

--- Organization ---
Organization: {organization}
Role: {role}
Intended Usage: {usage}

--- Plan ---
Plan: {plan}

Submitted At (UTC): {submitted_at}

ACTION REQUIRED:
Approve: {approve_url}
Reject:  {reject_url}

Security note:
- Password is NOT included and is stored only as a hash.
""".strip()

    # HTML email with buttons
    html = f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,sans-serif;">
    <div style="max-width:640px;margin:0 auto;padding:24px;">
      <div style="background:#ffffff;border-radius:16px;padding:22px;border:1px solid rgba(0,0,0,0.08);
                  box-shadow:0 14px 40px rgba(17,24,39,0.10);">

        <div style="display:inline-block;font-size:12px;font-weight:800;letter-spacing:.5px;
                    padding:6px 10px;border-radius:999px;background:#eef2ff;color:#4338ca;
                    border:1px solid rgba(67,56,202,0.18);">
          BINARYPOT • ADMIN REVIEW
        </div>

        <h2 style="margin:12px 0 6px 0;font-size:20px;color:#111827;">
          New Admin Signup Request
        </h2>
        <div style="color:#6b7280;font-size:13px;margin-bottom:16px;">
          Submitted at (UTC): {submitted_at}
        </div>

        <div style="border-radius:14px;background:#f9fafb;border:1px solid rgba(0,0,0,0.06);padding:14px;">
          <div style="font-size:13px;color:#111827;line-height:1.75;">
            <b>Full Name:</b> {full_name}<br/>
            <b>Email:</b> {email}<br/>
            <b>Organization:</b> {organization}<br/>
            <b>Role:</b> {role}<br/>
            <b>Usage:</b> {usage}<br/>
            <b>Plan:</b> {plan}<br/>
          </div>
        </div>

        <div style="margin:18px 0 10px 0;color:#6b7280;font-size:12px;font-weight:700;">
          Action required:
        </div>

        <!-- Buttons: stacked + roomy -->
        <div style="margin-top:6px;">
          <a href="{approve_url}"
             style="display:block;text-align:center;
                    padding:14px 16px;border-radius:12px;
                    background:#22c55e;color:#ffffff;text-decoration:none;
                    font-weight:800;font-size:14px;
                    box-shadow:0 10px 22px rgba(34,197,94,0.22);">
             Approve Request
          </a>

          <div style="height:12px;line-height:12px;font-size:12px;">&nbsp;</div>

          <a href="{reject_url}"
             style="display:block;text-align:center;
                    padding:14px 16px;border-radius:12px;
                    background:#ef4444;color:#ffffff;text-decoration:none;
                    font-weight:800;font-size:14px;
                    box-shadow:0 10px 22px rgba(239,68,68,0.20);">
             Reject Request
          </a>
        </div>

        <div style="margin-top:18px;padding:12px;border-radius:12px;background:#0b1220;border:1px solid rgba(255,255,255,0.08);">
          <div style="font-size:12px;color:rgba(255,255,255,0.85);font-weight:700;margin-bottom:6px;">
            Fallback links (if buttons don’t work)
          </div>
          <div style="font-size:12px;color:rgba(255,255,255,0.75);line-height:1.6;word-break:break-word;">
            Approve: <a style="color:#93c5fd" href="{approve_url}">{approve_url}</a><br/>
            Reject: <a style="color:#fca5a5" href="{reject_url}">{reject_url}</a>
          </div>
        </div>

        <div style="margin-top:14px;color:#6b7280;font-size:12px;">
          <b>Security note:</b> Password is not included and is stored only as a hash.
        </div>
      </div>

      <div style="text-align:center;color:#9ca3af;font-size:11px;margin-top:12px;">
        BinaryPot • Automated email
      </div>
    </div>
  </body>
</html>
""".strip()

    msg = EmailMessage()
    msg["Subject"] = "[BinaryPot] New Admin Signup Request"
    msg["From"] = smtp_email
    msg["To"] = admin_email

    # Attach both versions
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
