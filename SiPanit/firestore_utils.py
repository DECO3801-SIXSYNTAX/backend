from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def with_audit_for_create(data: dict) -> dict:
    data = dict(data or {})
    data.setdefault("createdAt", now_iso())
    data["updatedAt"] = now_iso()
    return data

def with_audit_for_update(data: dict) -> dict:
    data = dict(data or {})
    data["updatedAt"] = now_iso()
    return data
