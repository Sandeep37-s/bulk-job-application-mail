"""Send mail through Gmail SMTP with an app password."""
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from .config import CFG, RESUME_PATH, env


def send_email(to, subject, body):
    sender = env("GMAIL_ADDRESS")
    msg = EmailMessage()
    msg["From"] = formataddr((CFG["profile"]["name"], sender))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    msg.set_content(body)
    msg.add_attachment(RESUME_PATH.read_bytes(), maintype="application", subtype="pdf",
                       filename=RESUME_PATH.name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(sender, env("GMAIL_APP_PASSWORD").replace(" ", ""))
        s.send_message(msg)
