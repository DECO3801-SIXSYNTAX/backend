# SiPanit/middleware/security_audit.py
import logging
logger = logging.getLogger("security_audit")

SENSITIVE_PREFIXES = ("/api/auth/", "/api/event/layouts")

class SecurityAuditMiddleware:
    """
    Logs minimal, privacy-preserving traces for sensitive endpoints:
    - Tujuan: accountability & post-incident review (tanpa menyimpan PII berlebih).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith(SENSITIVE_PREFIXES):
            uid = getattr(request.user, "id", None)
            logger.info("audit path=%s method=%s user=%s", path, request.method, uid)
        return self.get_response(request)