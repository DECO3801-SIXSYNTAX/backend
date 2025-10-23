import io, json
from typing import Dict
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken
import qrcode
from typing import Callable, Dict

def _fernet() -> Fernet:
    key = settings.QR_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)

def encrypt_payload(payload: Dict) -> str:
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return _fernet().encrypt(data).decode()

def decrypt_payload(token: str) -> Dict:
    try:
        data = _fernet().decrypt(token.encode())
        return json.loads(data.decode())
    except InvalidToken:
        raise ValueError("Invalid or expired token")

def qr_png_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def decrypt_to_guest(token: str, fetcher: Callable[[str, str], dict]) -> Dict:

    payload = decrypt_payload(token)
    e = str(payload.get("e") or "")
    g = str(payload.get("g") or "")
    if not e or not g:
        raise ValueError("Malformed token payload")
    guest = fetcher(e, g)
    if not guest:
        raise LookupError(f"Guest {g} not found for event {e}")
    return guest
