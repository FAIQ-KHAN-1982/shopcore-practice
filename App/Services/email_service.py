import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Re-use MAX_LOGIN_ATTEMPTS from Security to keep settings consistent
from App.Security import MAX_LOGIN_ATTEMPTS

def send_email_template(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Email '{subject}' sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email '{subject}' to {to_email}. Error: {e}")
        print(f"\n--- MOCK EMAIL [Subject: {subject}] ---")
        print(f"To: {to_email}")
        print(f"Content:\n{body}")
        print("------------------------------------------\n")

def send_verification_email(to_email: str, token: str):
    link = f"http://localhost:5500/index.html?token={token}"
    body = f"Please verify your email by clicking on the link:\n{link}\n\nThis link is valid for 24 hours."
    send_email_template(to_email, "Verify your ShopCore Account", body)

def send_reset_password_email(to_email: str, token: str):
    link = f"http://localhost:5500/index.html?reset_token={token}"
    body = f"You requested a password reset. Click the link to reset your password:\n{link}\n\nThis link is valid for 15 minutes. If you did not request this, ignore this email."
    send_email_template(to_email, "Reset your ShopCore Password", body)

def send_new_device_login_alert(to_email: str, ip_address: str):
    body = f"We detected a login to your account from a new IP address: {ip_address}.\n\nIf this was you, no action is needed. If this wasn't you, please secure your account by changing your password immediately."
    send_email_template(to_email, "Security Alert: Login from New Device/Location", body)

def send_lockout_alert_email(to_email: str):
    body = f"Your ShopCore account has been locked due to {MAX_LOGIN_ATTEMPTS} consecutive failed login attempts.\n\nPlease contact an administrator or request a password reset to unlock your account."
    send_email_template(to_email, "Security Alert: Account Locked", body)
