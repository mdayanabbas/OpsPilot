import smtplib
from email.mime.text import MIMEText
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# =========================
# CONFIG
# =========================

ENV_PATH = Path(__file__).resolve().parent / ".env"
if load_dotenv:
    load_dotenv(ENV_PATH)
elif ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

SENDER_EMAIL = os.getenv("EMAIL_USERNAME")  # Make sure to set this environment variable with your email address
APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")  # Make sure to set this environment variable with your app password

RECEIVER_EMAIL = os.getenv("EMAIL_RECEIVER") or os.getenv("ALERT_EMAIL_TO") or SENDER_EMAIL

if not SENDER_EMAIL or not APP_PASSWORD or not RECEIVER_EMAIL:
    raise RuntimeError(
        "Missing email config. Set EMAIL_USERNAME and EMAIL_APP_PASSWORD in .env, "
        "and optionally EMAIL_RECEIVER or ALERT_EMAIL_TO."
    )

# =========================
# DIFFERENT MAILS
# =========================

emails = [
    {
        "subject": "Users Unable to Login to Dashboard",
        "body": """
Hello Support Team,

A client reported that they are unable to log into the dashboard even after entering the correct credentials.

Please investigate the authentication issue.

Regards.
"""
    },

    {
        "subject": "Login Page Showing Invalid Credentials Error",
        "body": """
Hi Team,

Several users are receiving an 'Invalid Credentials' message despite using the correct email and password.

Kindly check if there is any issue with the login service.

Thank you.
"""
    },

    {
        "subject": "Authentication Failure After Password Reset",
        "body": """
Hello,

A customer recently reset their password but still cannot access their account.

Please verify whether the password reset changes are syncing correctly.

Regards.
"""
    },

    {
        "subject": "Users Getting Stuck After Login Attempt",
        "body": """
Dear Support,

Clients mentioned that after clicking the login button, the page keeps loading endlessly without redirecting to the dashboard.

Please investigate the issue.

Thanks.
"""
    },

    {
        "subject": "Login Session Expiring Immediately",
        "body": """
Hello Team,

Some users reported that their sessions expire immediately after successful login, forcing them to sign in repeatedly.

Could you please check the session management service?

Regards.
"""
    }
]

# =========================
# FUNCTION
# =========================

def send_email(data):

    try:
        msg = MIMEText(data["body"])

        msg["Subject"] = data["subject"]
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(
                SENDER_EMAIL,
                RECEIVER_EMAIL,
                msg.as_string()
            )

        print(f'[+] Sent: {data["subject"]}')

    except Exception as e:
        print(f'[-] Failed: {data["subject"]} -> {e}')


# =========================
# SEND ALL AT ONCE
# =========================

for email_data in emails:
    send_email(email_data)

print("All different emails sent!")
