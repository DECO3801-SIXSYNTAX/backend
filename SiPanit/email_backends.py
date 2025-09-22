"""
Custom email backend that sends emails to multiple backends simultaneously.
This allows sending to both console (for debugging) and SendGrid (for actual delivery).
"""

from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from anymail.backends.sendgrid import EmailBackend as SendGridEmailBackend


class MultiEmailBackend:
    """
    A custom email backend that sends messages to multiple backends.
    Sends to both console (for debugging) and SendGrid (for actual delivery).
    """

    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

        # Initialize both backends
        self.console_backend = ConsoleEmailBackend(fail_silently=fail_silently, **kwargs)
        self.sendgrid_backend = SendGridEmailBackend(fail_silently=fail_silently, **kwargs)

    def send_messages(self, email_messages):
        """
        Send messages through both backends.
        Returns the number of successfully sent messages.
        """
        if not email_messages:
            return 0

        sent_count = 0

        # Send through console backend (for debugging)
        try:
            console_sent = self.console_backend.send_messages(email_messages)
            if console_sent:
                print(f"[MultiEmailBackend] Console backend: {console_sent} messages logged")
        except Exception as e:
            if not self.fail_silently:
                raise
            print(f"[MultiEmailBackend] Console backend failed: {e}")

        # Send through SendGrid backend (for actual delivery)
        try:
            sendgrid_sent = self.sendgrid_backend.send_messages(email_messages)
            if sendgrid_sent:
                print(f"[MultiEmailBackend] SendGrid backend: {sendgrid_sent} messages sent")
                sent_count = sendgrid_sent
        except Exception as e:
            if not self.fail_silently:
                raise
            print(f"[MultiEmailBackend] SendGrid backend failed: {e}")

        return sent_count

    def open(self):
        """Open connections for both backends."""
        self.console_backend.open()
        self.sendgrid_backend.open()

    def close(self):
        """Close connections for both backends."""
        self.console_backend.close()
        self.sendgrid_backend.close()