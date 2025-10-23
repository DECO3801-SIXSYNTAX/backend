# guests/emails.py
import datetime
from email.mime.image import MIMEImage
from django.template.loader import render_to_string

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.text import slugify

from crypto.qr import encrypt_payload, qr_png_bytes


# ---------- Templates ----------
TEXT_TEMPLATE = """\
Hi {guest_name},

You're confirmed for {event_name}.

Event:
• Date & time: {event_date} at {event_time}
• Venue: {venue_name}, {venue_address}

Check-in:
• Show your QR code at the kiosk on arrival.
• If your email app blocks images, open this link to view your QR:
  {checkin_url}

Need help at the venue? Show this email to a staff member.

This QR encodes a secure token linked to your invite (no personal data). Please don’t forward it.

See you soon,
{org_name} Team
{org_reply_email}
"""

HTML_TEMPLATE = """\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f7f7f8;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td align="center" style="padding:24px;">
          <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.04);" cellspacing="0" cellpadding="0">
            <tr>
              <td style="padding:20px 24px 0;">
                <div style="font-size:20px;font-weight:700;">{event_name}</div>
                <div style="font-size:14px;color:#555;margin-top:4px;">Your check-in QR code</div>
              </td>
            </tr>

            <tr>
              <td style="padding:12px 24px 0;font-size:15px;line-height:1.5;">
                <p style="margin:0 0 12px 0;">Hi {guest_name},</p>
                <p style="margin:0 0 12px 0;">You're confirmed for <strong>{event_name}</strong>. Please show this QR code at the kiosk when you arrive.</p>

                <div style="margin:12px 0 8px 0;font-size:14px;color:#444;">
                  <div><strong>Date & time:</strong> {event_date} at {event_time}</div>
                  <div><strong>Venue:</strong> {venue_name}, {venue_address}</div>
                </div>
              </td>
            </tr>

            <tr>
              <td align="center" style="padding:8px 24px 4px;">
                <img src="cid:qrimg" alt="Your QR code" width="240" height="240"
                     style="display:block;width:240px;height:240px;border:1px solid #eee;border-radius:8px" />
              </td>
            </tr>

            <tr>
              <td align="center" style="padding:6px 24px 16px;">
                <a href="{checkin_url}" target="_blank" rel="noreferrer noopener"
                   style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;
                          padding:12px 16px;border-radius:10px;font-weight:600;">
                  Open your QR / Check-in link
                </a>
                <div style="font-size:12px;color:#666;margin-top:8px;">
                  If the image didn’t load, use the button above or this link:<br/>
                  <a href="{checkin_url}" target="_blank" style="color:#2563eb;">{checkin_url}</a>
                </div>
              </td>
            </tr>

            <tr>
              <td style="padding:0 24px 20px;font-size:12px;line-height:1.5;color:#666;">
                <p style="margin:0 0 8px 0;">This QR encodes a secure token linked to your invite (no personal data). Please don’t forward it.</p>
                <p style="margin:0;">Need help at the venue? Show this email to a staff member.</p>
              </td>
            </tr>

            <tr>
              <td style="padding:12px 24px 20px;border-top:1px solid #eee;font-size:12px;color:#777;">
                {org_name} • <a href="mailto:{org_reply_email}" style="color:#555;text-decoration:none;">{org_reply_email}</a>
              </td>
            </tr>
          </table>

          <div style="font-size:11px;color:#9aa0a6;margin-top:12px;">
            © {year} {org_name}. All rights reserved.
          </div>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def build_checkin_url(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/check-in?token={token}"


def send_guest_qr_email(
    *,
    event_id: str,
    guest_id: str,
    guest_email: str,
    guest_name: str,
    base_url: str,
    event_name: str = "Your Event",
    event_date: str = "",
    event_time: str = "",
    venue_name: str = "",
    venue_address: str = "",
    org_name: str = "Event Team",
    org_reply_email: str = "no-reply@example.com",
    from_email: str | None = None,
) -> None:
    """
    Sends an invitation email with inline + attached QR PNG.

    Required:
      - event_id, guest_id, guest_email, guest_name, base_url

    Optional niceties:
      - event_name, event_date, event_time, venue_name, venue_address, org_name, org_reply_email
    """
    token    = encrypt_payload({"e": str(event_id), "g": str(guest_id)})
    qr_png   = qr_png_bytes(token)
    checkin_url = f"{base_url.rstrip('/')}/checkin?token={token}"   # be consistent: /checkin

    subject = f"Your QR Code for {event_name}"
    from_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    to = [guest_email]

    
    text_body = TEXT_TEMPLATE.format(
        guest_name=guest_name or "Guest",
        event_name=event_name,
        event_date=event_date,
        event_time=event_time,
        venue_name=venue_name,
        venue_address=venue_address,
        checkin_url=checkin_url,           
        org_name=org_name,
        org_reply_email=org_reply_email,
    )
    html_body = HTML_TEMPLATE.format(
        guest_name=guest_name or "Guest",
        event_name=event_name,
        event_date=event_date,
        event_time=event_time,
        venue_name=venue_name,
        venue_address=venue_address,
        checkin_url=checkin_url,           
        year=datetime.datetime.now().year,
        org_name=org_name,
        org_reply_email=org_reply_email,
    )

    msg = EmailMultiAlternatives(subject, text_body, from_email, to)
    msg.attach_alternative(html_body, "text/html")

    img = MIMEImage(qr_png, _subtype="png")
    img.add_header("Content-ID", "<qrimg>")
    img.add_header("Content-Disposition", "inline", filename="qr.png")
    msg.attach(img)
    msg.mixed_subtype = "related"

    msg.send(fail_silently=False)