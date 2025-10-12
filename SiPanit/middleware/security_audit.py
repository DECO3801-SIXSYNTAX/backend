# SiPanit/middleware/security_audit.py
import logging
logger = logging.getLogger("security_audit")

SENSITIVE_PREFIXES = ("/api/auth/", "/api/event/layouts")

class SecurityAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith(SENSITIVE_PREFIXES):
            # user bisa belum ada jika middleware ini dieksekusi sebelum AuthenticationMiddleware
            user = getattr(request, "user", None)
            uid = getattr(user, "id", None) if user is not None else None
            method = getattr(request, "method", None)
            logger.info("audit path=%s method=%s user=%s", path, method, uid)
        return self.get_response(request)