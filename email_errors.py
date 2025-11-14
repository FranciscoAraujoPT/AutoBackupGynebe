import smtplib
import os
from email.mime.text import MIMEText
from loggingUtils import log_config
import sys

logger = log_config()

SENDER = "mcaraujo@clinicagynebe.com.pt"
RECIPIENTS = [
    "francisco.g.calado.araujo@gmail.com",
    "ruka.araujo@gmail.com",
    "rui.earaujo@gmail.com",
    "mcaraujo@clinicagynebe.com.pt"
]

SUBJECT = "[Gynébe] Failure in the backup"
BODY_BASE = (
    "There was an error in the backup process.\n"
    "Please contact its creator, the magnificent Ruca, "
    "or his successor, Quico The Great!\n"
)

ERROR_MESSAGES = {
    "1": "- Error sending backup to backup server.",
    "2": "- Error sending backup to google drive.",
    "3": "- Error sending backup to backup server.\n- Error sending backup to google drive.",
    "4": "- Error making backup in the server",
    "5": "- Error reading the credentials file"
}

def send_email(sender, password, recipients, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)

        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

if __name__ == "__main__":
    # Default argument is None
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    body = BODY_BASE

    if arg in ERROR_MESSAGES:
        body += "\nErrors:\n" + ERROR_MESSAGES[arg]

    current_path = os.getcwd()
    file_path = os.path.join(current_path, "app_password.txt")

    if not os.path.exists(file_path):
        logger.error(f"App password file does not exist: {file_path}")
    else:
        logger.info(f"App password file exists: {file_path}")
        with open(file_path, "r") as file:
            APP_PASSWORD = file.readline()
            send_email(SENDER, APP_PASSWORD, RECIPIENTS, SUBJECT, body)


   