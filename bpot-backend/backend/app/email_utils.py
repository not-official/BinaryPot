# app/email_utils.py
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime


# -----------------------------
# SMTP config helpers
# -----------------------------
def _smtp_config():
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_email = os.getenv("SMTP_EMAIL", "binarypot101@gmail.com")
    smtp_password = os.getenv("SMTP_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL", smtp_email)

    if not smtp_password:
        raise RuntimeError("SMTP_PASSWORD env var missing (use Gmail App Password)")

    return smtp_host, smtp_port, smtp_email, smtp_password, admin_email


def _send_email(msg: EmailMessage) -> None:
    smtp_host, smtp_port, smtp_email, smtp_password, _admin_email = _smtp_config()
    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(smtp_email, smtp_password)
        server.send_message(msg)


# -----------------------------
# 1) Admin review email (Approve/Reject buttons)
# -----------------------------
def send_signup_email(payload: dict, approve_url: str, reject_url: str) -> None:
    """
    Sends admin an email with approve/reject links.
    payload: safe fields only (no password, no card)
    """
    _, _, smtp_email, _, admin_email = _smtp_config()

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

    # HTML email with buttons (roomy + premium purple)
    html = f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f6f3ff;font-family:Arial,sans-serif;">
    <div style="max-width:680px;margin:0 auto;padding:26px;">
      <div style="background:rgba(255,255,255,0.95);
                  border-radius:18px;padding:24px;
                  border:1px solid rgba(124,58,237,0.18);
                  box-shadow:0 18px 55px rgba(124,58,237,0.15);">

        <div style="display:inline-block;font-size:12px;font-weight:900;letter-spacing:.55px;
                    padding:7px 12px;border-radius:999px;
                    background:linear-gradient(135deg, rgba(124,58,237,0.14), rgba(167,139,250,0.16));
                    color:#4c1d95;border:1px solid rgba(124,58,237,0.26);">
          BINARYPOT • ADMIN REVIEW
        </div>

        <h2 style="margin:14px 0 6px 0;font-size:20px;color:#1f1147;">
          New Admin Signup Request
        </h2>
        <div style="color:rgba(46,16,101,0.60);font-size:13px;margin-bottom:18px;">
          Submitted at (UTC): {submitted_at}
        </div>

        <div style="border-radius:14px;background:#fbfaff;border:1px solid rgba(124,58,237,0.14);padding:14px;">
          <div style="font-size:13px;color:#1f1147;line-height:1.75;">
            <b>Full Name:</b> {full_name}<br/>
            <b>Email:</b> {email}<br/>
            <b>Organization:</b> {organization}<br/>
            <b>Role:</b> {role}<br/>
            <b>Usage:</b> {usage}<br/>
            <b>Plan:</b> {plan}<br/>
          </div>
        </div>

        <div style="margin:18px 0 10px 0;color:rgba(46,16,101,0.65);font-size:12px;font-weight:800;">
          Action required:
        </div>

        <!-- Buttons: spacious + clearly separated -->
        <div style="margin-top:8px;">
          <a href="{approve_url}"
             style="display:block;text-align:center;
                    padding:14px 16px;border-radius:14px;
                    background:linear-gradient(135deg,#22c55e,#16a34a);
                    color:#ffffff;text-decoration:none;
                    font-weight:900;font-size:14px;
                    box-shadow:0 12px 26px rgba(34,197,94,0.22);">
             ✅ Approve Request
          </a>

          <div style="height:14px;line-height:14px;font-size:14px;">&nbsp;</div>

          <a href="{reject_url}"
             style="display:block;text-align:center;
                    padding:14px 16px;border-radius:14px;
                    background:linear-gradient(135deg,#ef4444,#dc2626);
                    color:#ffffff;text-decoration:none;
                    font-weight:900;font-size:14px;
                    box-shadow:0 12px 26px rgba(239,68,68,0.20);">
             ❌ Reject Request
          </a>
        </div>

        <div style="margin-top:18px;padding:12px;border-radius:14px;
                    background:#0b1220;border:1px solid rgba(255,255,255,0.08);">
          <div style="font-size:12px;color:rgba(255,255,255,0.88);font-weight:900;margin-bottom:8px;">
            Fallback links (if buttons don’t work)
          </div>
          <div style="font-size:12px;color:rgba(255,255,255,0.75);line-height:1.7;word-break:break-word;">
            Approve: <a style="color:#c4b5fd" href="{approve_url}">{approve_url}</a><br/>
            Reject: <a style="color:#fca5a5" href="{reject_url}">{reject_url}</a>
          </div>
        </div>

        <div style="margin-top:14px;color:rgba(46,16,101,0.60);font-size:12px;">
          <b>Security note:</b> Password is not included and is stored only as a hash.
        </div>
      </div>

      <div style="text-align:center;color:rgba(46,16,101,0.45);font-size:11px;margin-top:12px;">
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

    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    _send_email(msg)


# -----------------------------
# 2) Requester notification email (Approved / Rejected)
# -----------------------------
def send_requester_status_email(
    requester_email: str,
    requester_name: str,
    status: str,
    reason: str | None = None,
) -> None:
    """
    Sends the requester an email after admin approves/rejects.
    status: "APPROVED" or "REJECTED"
    """
    _, _, smtp_email, _, _admin_email = _smtp_config()

    status = (status or "").upper().strip()
    if status not in {"APPROVED", "REJECTED"}:
        raise ValueError("status must be APPROVED or REJECTED")

    now_utc = datetime.utcnow().isoformat()

    subject = (
        "[BinaryPot] Your admin account is approved ✅"
        if status == "APPROVED"
        else "[BinaryPot] Your admin signup was rejected ❌"
    )

    headline = "Your request is approved ✅" if status == "APPROVED" else "Your request was rejected ❌"
    subtext = (
        "You can now log in using your email and password."
        if status == "APPROVED"
        else "If you think this is a mistake, please contact the project admin."
    )

    # Plain text
    text = f"""
Hi {requester_name or "there"},

{headline}

{subtext}

Status: {status}
Time (UTC): {now_utc}
{("Reason: " + reason) if reason else ""}

— BinaryPot
""".strip()

    # HTML
    badge_bg = "linear-gradient(135deg,#22c55e,#16a34a)" if status == "APPROVED" else "linear-gradient(135deg,#ef4444,#dc2626)"
    badge_border = "rgba(34,197,94,0.28)" if status == "APPROVED" else "rgba(239,68,68,0.28)"

    html_reason = f"""
      <div style="margin-top:14px;padding:12px;border-radius:14px;background:#fff7ed;border:1px solid rgba(245,158,11,0.22);color:#7a4b00;">
        <b>Reason:</b> {reason}
      </div>
    """ if reason else ""

    html = f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f6f3ff;font-family:Arial,sans-serif;">
    <div style="max-width:680px;margin:0 auto;padding:26px;">
      <div style="background:rgba(255,255,255,0.95);
                  border-radius:18px;padding:24px;
                  border:1px solid rgba(124,58,237,0.18);
                  box-shadow:0 18px 55px rgba(124,58,237,0.14);">

        <div style="display:inline-block;font-size:12px;font-weight:900;letter-spacing:.55px;
                    padding:7px 12px;border-radius:999px;
                    background:linear-gradient(135deg, rgba(124,58,237,0.14), rgba(167,139,250,0.16));
                    color:#4c1d95;border:1px solid rgba(124,58,237,0.26);">
          BINARYPOT
        </div>

        <h2 style="margin:14px 0 6px 0;font-size:20px;color:#1f1147;">
          {headline}
        </h2>
        <div style="color:rgba(46,16,101,0.62);font-size:13px;margin-bottom:14px;">
          Hi {requester_name or "there"}, {subtext}
        </div>

        <div style="display:inline-block;padding:10px 12px;border-radius:14px;
                    background:{badge_bg};color:#fff;font-weight:900;
                    border:1px solid {badge_border};">
          Status: {status}
        </div>

        {html_reason}

        <div style="margin-top:16px;color:rgba(46,16,101,0.58);font-size:12px;">
          Time (UTC): {now_utc}
        </div>
      </div>

      <div style="text-align:center;color:rgba(46,16,101,0.45);font-size:11px;margin-top:12px;">
        BinaryPot • Automated email
      </div>
    </div>
  </body>
</html>
""".strip()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = requester_email

    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    _send_email(msg)
