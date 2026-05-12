import smtplib
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor

# =========================
# CONFIG
# =========================

SENDER_EMAIL = "abbas.support@gmail.com"
APP_PASSWORD = "xllvbuwsmpkgkjdd"

RECEIVER_EMAIL = "abbas.support@gmail.com"

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
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(SENDER_EMAIL, APP_PASSWORD)

        msg = MIMEText(data["body"])

        msg["Subject"] = data["subject"]
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL

        server.sendmail(
            SENDER_EMAIL,
            RECEIVER_EMAIL,
            msg.as_string()
        )

        server.quit()

        print(f'[+] Sent: {data["subject"]}')

    except Exception as e:
        print(f'[-] Failed: {data["subject"]} -> {e}')


# =========================
# SEND ALL AT ONCE
# =========================

with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(send_email, emails)

print("All different emails sent!")