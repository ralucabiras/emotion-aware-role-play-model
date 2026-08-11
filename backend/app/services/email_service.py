import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    pass


class EmailService:
    async def send_verification(self, recipient: str, preferred_name: str, token: str) -> None:
        if not all((settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_sender)):
            raise EmailDeliveryError("Email delivery is not configured")
        link = f"{settings.frontend_origin.rstrip('/')}/verify-email?token={token}"
        message = EmailMessage()
        message["Subject"] = "Confirm your AffectLab email"
        message["From"] = settings.smtp_sender
        message["To"] = recipient
        greeting = f"Hi {preferred_name}," if preferred_name else "Hello,"
        message.set_content(
            f"{greeting}\n\nConfirm your AffectLab email by opening this link:\n{link}\n\n"
            f"This link expires in {settings.email_verification_hours} hours. If you did not create "
            "this account, you can ignore this email.\n\nAffectLab is a research prototype, not medical care."
        )
        await asyncio.to_thread(self._send, message)

    def _send(self, message: EmailMessage) -> None:
        try:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
            ) as client:
                client.ehlo()
                if settings.smtp_use_tls:
                    client.starttls()
                    client.ehlo()
                client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("Verification email could not be sent") from exc
