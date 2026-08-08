"""Gmail / Email Integration — Module 11."""
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from langchain.tools import tool
from config import llm
from models.schemas import EmailDraft

load_dotenv()


def extract_email_address(text: str) -> str:
    """Extract first valid email address from text, or return None."""
    if not text:
        return None
    matches = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return matches[0] if matches else None


def generate_email_draft(
    report_content: str,
    client_name: str = "Client",
    recipient: str = None,
    client_email: str = None,
) -> EmailDraft:
    """Generate a structured, professional email draft with accurate recipient resolution."""
    # 1. Check if user query mentions an email address explicitly
    explicit_email = extract_email_address(report_content)
    target_recipient = explicit_email or recipient or client_email or "manager@company.com"

    prompt = (
        f"You are an executive investment analyst at AlphaVest Capital.\n"
        f"Draft a concise, professional investment email for client '{client_name}'.\n"
        f"The recipient email address MUST be '{target_recipient}'.\n\n"
        f"Report / Context Details:\n{report_content}\n\n"
        f"Return ONLY valid JSON matching the schema with keys 'recipient', 'subject', and 'body'."
    )
    try:
        draft = llm.with_structured_output(EmailDraft).invoke(prompt)
        draft.recipient = target_recipient  # enforce resolved recipient
        return draft
    except Exception:
        # Fallback text generation
        res = llm.invoke(prompt)
        text = res.content if hasattr(res, "content") else str(res)
        return EmailDraft(
            recipient=target_recipient,
            subject=f"AlphaVest Investment Research Brief — {client_name}",
            body=text.strip(),
        )


def send_email_via_smtp(
    recipient: str,
    subject: str,
    body: str,
    sender_email: str = None,
    sender_password: str = None,
) -> dict:
    """Send a real email via Gmail/SMTP if configured, or provide clear status."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender = sender_email or os.getenv("EMAIL_SENDER", "")
    password = sender_password or os.getenv("EMAIL_PASSWORD", "")

    # Clean password of whitespace/spaces (Gmail app passwords often have spaces)
    if password:
        password = password.replace(" ", "")

    if sender and password:
        try:
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
            return {
                "status": "sent",
                "message": f"✅ Email successfully dispatched to **{recipient}** from **{sender}**!",
                "recipient": recipient,
                "subject": subject,
            }
        except smtplib.SMTPAuthenticationError:
            return {
                "status": "error",
                "message": (
                    f"❌ Gmail Authentication Failed for {sender}. "
                    "Note: Gmail requires a 16-character **Google App Password** (https://myaccount.google.com/apppasswords), "
                    "not your standard Gmail account password."
                ),
                "recipient": recipient,
                "subject": subject,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ SMTP error sending to {recipient}: {e}",
                "recipient": recipient,
                "subject": subject,
            }
    else:
        return {
            "status": "prepared",
            "message": (
                f"✉️ Email draft generated for **{recipient}**.\n\n"
                f"ℹ️ **To send real emails to your Gmail inbox:** Enter your Gmail address & 16-character Google App Password in the sidebar under **'Email & Gmail SMTP Settings'** or in `.env` (`EMAIL_SENDER` & `EMAIL_PASSWORD`)."
            ),
            "recipient": recipient,
            "subject": subject,
            "body": body,
        }


@tool
def email_report_tool(query: str) -> str:
    """Draft and dispatch investment reports to clients."""
    draft = generate_email_draft(query)
    dispatch = send_email_via_smtp(draft.recipient, draft.subject, draft.body)
    return (
        f"📧 **Subject:** {draft.subject}\n"
        f"**To:** {draft.recipient}\n\n"
        f"**Email Content:**\n\n{draft.body}\n\n"
        f"{dispatch['message']}"
    )
