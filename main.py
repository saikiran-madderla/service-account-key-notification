import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from googleapiclient.discovery import build
from google.auth import default

def fetch_service_account_data():
    credentials, project_id = default()
    service = build("iam", "v1", credentials=credentials)

    accounts = service.projects().serviceAccounts().list(
        name=f"projects/{project_id}"
    ).execute()

    report = f"🚀 GCP Service Account Key Report\n📅 Timestamp: {datetime.now(timezone.utc)}\n"
    report += "-" * 80 + "\n"

    for sa in accounts.get("accounts", []):
        email = sa["email"]
        name = sa["name"]

        keys = service.projects().serviceAccounts().keys().list(name=name).execute()
        # Filter for user-managed keys only
        user_managed_keys = [
            key for key in keys.get("keys", [])
            if key.get("keyType") == "USER_MANAGED"
        ]

        if not user_managed_keys:
            report += f"🔹 {email} — No user-managed keys found\n"
            continue

        for key in user_managed_keys:
            key_id = key.get("name", "").split("/")[-1]
            expiry = key.get("validBeforeTime")

            if expiry:
                expiry_time = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                remaining = (expiry_time - datetime.now(timezone.utc)).days
                expiry_str = expiry_time.strftime("%d %b %Y")  # eg: 30 Jan 2027
                color = "🟥" if remaining <= 10 else "🟩"
                report += f"{color} {email} | Key: {key_id} | Expires in: {remaining} days | Expiry Date: {expiry_str}\n"
            else:
                report += f"🟨 {email} | Key: {key_id} | No expiry set\n"

    return report


def send_notification(event, context):
    try:
        report = fetch_service_account_data()

        username = os.environ["username"]
        password = os.environ["password"]
        sender = os.environ["sender"]
        recipients = os.environ["recipients"].split(",")
        smtp_server = os.environ.get("SMTP", "smtp.gmail.com")

        email = EmailMessage()
        email.set_content(report)
        email["Subject"] = "🚨 GCP Service Account Key Expiry Alert 🚨"
        email["From"] = sender
        email["To"] = ", ".join(recipients)

        with smtplib.SMTP_SSL(smtp_server, 465) as smtp:
            smtp.login(username, password)
            smtp.send_message(email)

        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Error in send_notification: {e}")
