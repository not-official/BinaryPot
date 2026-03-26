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
# Shared HTML theme helpers
# -----------------------------
def _escape_html(value) -> str:
    if value is None:
        return "-"
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _email_shell(title: str, body_html: str) -> str:
    """
    Shared dark cyber email shell matching BinaryPot frontend theme.
    """
    return f"""
<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <meta name="color-scheme" content="dark only" />
    <meta name="supported-color-schemes" content="dark only" />
    <title>{_escape_html(title)}</title>
  </head>
  <body style="margin:0;padding:0;background:#060912;font-family:Arial,sans-serif;color:#e2e8f0;">
    <div style="margin:0;padding:32px 16px;background:#060912;">
      <div style="max-width:720px;margin:0 auto;">

        <div style="text-align:center;margin-bottom:16px;">
          <div style="
            display:inline-block;
            font-size:12px;
            color:#8892a4;
            letter-spacing:1px;
            font-weight:700;
            font-family:'IBM Plex Mono', monospace;
          ">
            BINARYPOT • LLM-POWERED SSH HONEYPOT
          </div>
        </div>

        <div style="
          background:#0f1628;
          border:1px solid rgba(0,212,255,0.25);
          border-radius:6px;
          overflow:hidden;
          box-shadow:0 0 40px rgba(0,212,255,0.10), 0 0 0 1px rgba(0,212,255,0.05);
        ">

          <!-- terminal top bar -->
          <div style="
            background:#141c30;
            border-bottom:1px solid rgba(0,212,255,0.12);
            padding:10px 16px;
          ">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
              <tr>
                <td align="left" valign="middle">
                  <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ef4444;margin-right:6px;"></span>
                  <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b;margin-right:6px;"></span>
                  <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#10b981;"></span>
                </td>
                <td align="right" valign="middle" style="
                  color:#8892a4;
                  font-size:12px;
                  font-family:'IBM Plex Mono', monospace;
                ">
                  binarypot.honeypot — /mail/system
                </td>
              </tr>
            </table>
          </div>

          <div style="padding:32px 28px;">
            <div style="text-align:center;margin-bottom:28px;">
              <div style="
                margin:0;
                font-size:30px;
                font-weight:800;
                color:#00d4ff;
                letter-spacing:-1px;
                font-family:Arial,sans-serif;
              ">
                ⬡ BinaryPot
              </div>
              <div style="
                margin-top:4px;
                font-size:11px;
                color:#4a5568;
                letter-spacing:1px;
                font-family:'IBM Plex Mono', monospace;
              ">
                SECURE ACCESS NOTIFICATION
              </div>
            </div>

            {body_html}
          </div>
        </div>

        <div style="
          text-align:center;
          color:#4a5568;
          font-size:11px;
          margin-top:12px;
          font-family:'IBM Plex Mono', monospace;
        ">
          BinaryPot • Automated email
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()


def _info_row(label: str, value: str) -> str:
    return f"""
<tr>
  <td style="
    padding:10px 12px;
    border-bottom:1px solid rgba(0,212,255,0.08);
    color:#8892a4;
    font-size:11px;
    letter-spacing:0.5px;
    font-family:'IBM Plex Mono', monospace;
    width:180px;
    vertical-align:top;
  ">
    {label}
  </td>
  <td style="
    padding:10px 12px;
    border-bottom:1px solid rgba(0,212,255,0.08);
    color:#e2e8f0;
    font-size:13px;
    font-family:'IBM Plex Mono', monospace;
    word-break:break-word;
  ">
    {value}
  </td>
</tr>
""".strip()


# -----------------------------
# 1) Admin review email (Approve/Reject buttons)
# -----------------------------
def send_signup_email(payload: dict, approve_url: str, reject_url: str) -> None:
    """
    Sends admin an email with approve/reject links.
    payload: safe fields only (no password, no card)
    """
    _, _, smtp_email, _, admin_email = _smtp_config()

    full_name = _escape_html(payload.get("full_name", "-"))
    email = _escape_html(payload.get("email", "-"))
    organization = _escape_html(payload.get("organization", "-"))
    role = _escape_html(payload.get("role", "-"))
    usage = _escape_html(payload.get("usage", "-"))
    plan = _escape_html(payload.get("plan", "-"))
    submitted_at = _escape_html(datetime.utcnow().isoformat())

    safe_approve_url = _escape_html(approve_url)
    safe_reject_url = _escape_html(reject_url)

    # Plain text fallback
    text = f"""
A new admin signup request has been submitted.

--- Account ---
Full Name: {payload.get("full_name", "-")}
Email: {payload.get("email", "-")}

--- Organization ---
Organization: {payload.get("organization", "-")}
Role: {payload.get("role", "-")}
Intended Usage: {payload.get("usage", "-")}

--- Plan ---
Plan: {payload.get("plan", "-")}

Submitted At (UTC): {datetime.utcnow().isoformat()}

ACTION REQUIRED:
Approve: {approve_url}
Reject:  {reject_url}

Security note:
- Password is NOT included and is stored only as a hash.
""".strip()

    details_table = f"""
<div style="
  background:#0a0f1e;
  border:1px solid rgba(0,212,255,0.12);
  border-radius:4px;
  overflow:hidden;
  margin-bottom:18px;
">
  <div style="
    padding:10px 12px;
    border-bottom:1px solid rgba(0,212,255,0.12);
    color:#8892a4;
    background:#141c30;
    font-size:11px;
    letter-spacing:1px;
    font-family:'IBM Plex Mono', monospace;
  ">
    SIGNUP REQUEST DETAILS
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
    {_info_row("FULL NAME", full_name)}
    {_info_row("EMAIL", email)}
    {_info_row("ORGANIZATION", organization)}
    {_info_row("ROLE", role)}
    {_info_row("USAGE", usage)}
    {_info_row("PLAN", plan)}
    {_info_row("SUBMITTED AT (UTC)", submitted_at)}
  </table>
</div>
""".strip()

    body_html = f"""
<div style="
  color:#e2e8f0;
  font-size:16px;
  font-weight:700;
  margin-bottom:6px;
  font-family:Arial,sans-serif;
">
  New Admin Signup Request
</div>

<div style="
  color:#8892a4;
  font-size:12px;
  margin-bottom:18px;
  font-family:'IBM Plex Mono', monospace;
">
  An access request is waiting for admin review.
</div>

{details_table}

<div style="
  color:#8892a4;
  font-size:11px;
  letter-spacing:1px;
  margin-bottom:12px;
  font-family:'IBM Plex Mono', monospace;
">
  ACTION REQUIRED
</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:18px;">
  <tr>
    <td style="padding-bottom:12px;">
      <a href="{safe_approve_url}" style="
        display:block;
        text-align:center;
        padding:14px 16px;
        border-radius:3px;
        background:#10b981;
        color:#060912;
        text-decoration:none;
        font-weight:700;
        font-size:13px;
        letter-spacing:0.5px;
        font-family:'IBM Plex Mono', monospace;
        box-shadow:0 0 20px rgba(16,185,129,0.25);
      ">
        APPROVE REQUEST →
      </a>
    </td>
  </tr>
  <tr>
    <td>
      <a href="{safe_reject_url}" style="
        display:block;
        text-align:center;
        padding:14px 16px;
        border-radius:3px;
        background:#ef4444;
        color:#ffffff;
        text-decoration:none;
        font-weight:700;
        font-size:13px;
        letter-spacing:0.5px;
        font-family:'IBM Plex Mono', monospace;
        box-shadow:0 0 20px rgba(239,68,68,0.25);
      ">
        REJECT REQUEST →
      </a>
    </td>
  </tr>
</table>

<div style="
  background:#0a0f1e;
  border:1px solid rgba(0,212,255,0.12);
  border-radius:4px;
  padding:14px;
  margin-bottom:16px;
">
  <div style="
    color:#8892a4;
    font-size:11px;
    letter-spacing:1px;
    margin-bottom:8px;
    font-family:'IBM Plex Mono', monospace;
  ">
    FALLBACK LINKS
  </div>
  <div style="
    color:#e2e8f0;
    font-size:12px;
    line-height:1.7;
    word-break:break-word;
    font-family:'IBM Plex Mono', monospace;
  ">
    Approve:
    <a href="{safe_approve_url}" style="color:#00d4ff;text-decoration:none;">{safe_approve_url}</a>
    <br />
    Reject:
    <a href="{safe_reject_url}" style="color:#00d4ff;text-decoration:none;">{safe_reject_url}</a>
  </div>
</div>

<div style="
  font-size:12px;
  color:#4a5568;
  line-height:1.6;
  font-family:'IBM Plex Mono', monospace;
">
  Security note: Password is not included and is stored only as a hash.
</div>
""".strip()

    html = _email_shell("New Admin Signup Request", body_html)

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

    safe_name = _escape_html(requester_name or "there")
    safe_status = _escape_html(status)
    safe_reason = _escape_html(reason) if reason else ""
    now_utc = _escape_html(datetime.utcnow().isoformat())

    subject = (
        "[BinaryPot] Your admin account is approved ✅"
        if status == "APPROVED"
        else "[BinaryPot] Your admin signup was rejected ❌"
    )

    headline = (
        "Your request is approved"
        if status == "APPROVED"
        else "Your request was rejected"
    )

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
Time (UTC): {datetime.utcnow().isoformat()}
{("Reason: " + reason) if reason else ""}

— BinaryPot
""".strip()

    status_bg = "#10b981" if status == "APPROVED" else "#ef4444"
    status_color = "#060912" if status == "APPROVED" else "#ffffff"
    status_glow = (
        "0 0 20px rgba(16,185,129,0.22)"
        if status == "APPROVED"
        else "0 0 20px rgba(239,68,68,0.22)"
    )

    reason_block = ""
    if reason:
        reason_block = f"""
<div style="
  background:#0a0f1e;
  border:1px solid rgba(245,158,11,0.22);
  border-radius:4px;
  padding:14px;
  margin-top:16px;
  margin-bottom:16px;
">
  <div style="
    color:#8892a4;
    font-size:11px;
    letter-spacing:1px;
    margin-bottom:8px;
    font-family:'IBM Plex Mono', monospace;
  ">
    REVIEW NOTE
  </div>
  <div style="
    color:#e2e8f0;
    font-size:13px;
    line-height:1.6;
    font-family:'IBM Plex Mono', monospace;
  ">
    {safe_reason}
  </div>
</div>
""".strip()

    body_html = f"""
<div style="
  color:#e2e8f0;
  font-size:16px;
  font-weight:700;
  margin-bottom:6px;
  font-family:Arial,sans-serif;
">
  {headline}
</div>

<div style="
  color:#8892a4;
  font-size:13px;
  line-height:1.7;
  margin-bottom:18px;
  font-family:'IBM Plex Mono', monospace;
">
  Hi {safe_name},<br />
  { _escape_html(subtext) }
</div>

<div style="margin-bottom:18px;">
  <span style="
    display:inline-block;
    padding:12px 14px;
    border-radius:3px;
    background:{status_bg};
    color:{status_color};
    font-weight:700;
    font-size:13px;
    letter-spacing:0.5px;
    font-family:'IBM Plex Mono', monospace;
    box-shadow:{status_glow};
  ">
    STATUS: {safe_status}
  </span>
</div>

{reason_block}

<div style="
  background:#0a0f1e;
  border:1px solid rgba(0,212,255,0.12);
  border-radius:4px;
  overflow:hidden;
">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
    {_info_row("REQUEST STATUS", safe_status)}
    {_info_row("TIME (UTC)", now_utc)}
    {_info_row("NEXT STEP", _escape_html(subtext))}
  </table>
</div>
""".strip()

    html = _email_shell("Signup Request Status", body_html)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = requester_email

    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    _send_email(msg)