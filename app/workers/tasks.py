from app.workers.celery_app import celery_app
from app.core.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any


@celery_app.task
def send_email_notification(to_email: str, subject: str, body: str):
    """Send email notification."""
    if not settings.SMTP_HOST:
        return {"status": "skipped", "reason": "SMTP not configured"}
    
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return {"status": "sent", "to": to_email}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@celery_app.task
def send_webhook_notification(webhook_url: str, payload: Dict[str, Any]):
    """Send webhook notification."""
    import httpx
    
    try:
        response = httpx.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return {"status": "sent", "url": webhook_url}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@celery_app.task
def process_scheduled_reminders():
    """Process scheduled reminders (called by Celery Beat)."""
    # This would query the database for reminders due to be sent
    # and send notifications
    pass

