from typing import Any, Dict, List, Optional, Tuple
import re
from firebase_admin import firestore
from SiPanit.firebase import get_db
from adminapi.activity import log_activity
from datetime import datetime, timezone

COLL = "events"

# ---- audit helpers ----
def with_audit_on_create(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(payload)
    payload.setdefault("createdAt", firestore.SERVER_TIMESTAMP)
    payload["updatedAt"] = firestore.SERVER_TIMESTAMP
    return payload

def with_audit_on_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(payload)
    payload["updatedAt"] = firestore.SERVER_TIMESTAMP
    return payload
# -----------------------

def _guests_col(db, event_id: str):
    return db.collection(COLL).document(event_id).collection("guests")

def _prefixes(s: str, min_len=1, max_len=12) -> List[str]:
    s = (s or "").lower().strip()
    return [s[:i] for i in range(min_len, min(max_len, len(s)) + 1)] if s else []

def _split_tags(*values: str) -> List[str]:
    raw = ";".join(v for v in values if v)
    parts = re.split(r"[;,]", raw) if raw else []
    tags = {p.strip().lower() for p in parts if p and p.strip()}
    return sorted(tags)

def _normalize_guest_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    name   = (data.get("name") or "").strip()
    email  = (data.get("email") or "").lower().strip()
    phone  = (data.get("phone") or "").strip()
    diet   = (data.get("dietaryRestriction") or "").strip()
    access = (data.get("accessibilityNeeds") or "").strip()

    # seat only if explicitly provided (layout editor)
    seat = (data.get("seat") or "").strip() if data.get("seat") else None

    tags = _split_tags(diet, access)
    full_for_search = f"{email} {name}".strip().lower()

    payload: Dict[str, Any] = {
        "name": name,
        "email": email,
        "phone": phone,
        "dietaryRestriction": diet,
        "accessibilityNeeds": access,
        "tags": tags,
        "checkedIn": bool(data.get("checkedIn", False)),
        #"searchPrefixes": list(set(_prefixes(full_for_search))),
    }
    if seat:
        payload["seat"] = seat
    return payload

def upsert_guest(event_id: str, data: Dict[str, Any], *, actor=None) -> str:
    db = get_db()
    col = _guests_col(db, event_id)
    guest_id = data.get("id") or col.document().id
    doc_ref = col.document(guest_id)

    exists = doc_ref.get().exists
    payload = _normalize_guest_payload(data)
    payload = with_audit_on_update(payload) if exists else with_audit_on_create(payload)
    doc_ref.set(payload, merge=True)

    log_activity(
        action="guest.update" if exists else "guest.create",
        entity_type="guest",
        entity_id=guest_id,
        event_id=event_id,
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", None),
        details={"name": payload.get("name"), "email": payload.get("email")}
    )
    return guest_id

def delete_guest(event_id: str, guest_id: str, *, actor=None) -> None:
    get_db().collection(COLL).document(event_id).collection("guests").document(guest_id).delete()
    log_activity(
        action="guest.delete",
        entity_type="guest",
        entity_id=guest_id,
        event_id=event_id,
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", None),
        details={}
    )

def toggle_checkin(event_id: str, guest_id: str, *, actor=None) -> bool:
    db = get_db()
    ref = _guests_col(db, event_id).document(guest_id)
    snap = ref.get()
    current = bool((snap.to_dict() or {}).get("checkedIn", False))
    new_val = not current
    ref.set({"checkedIn": new_val, "updatedAt": firestore.SERVER_TIMESTAMP}, merge=True)
    log_activity(
        action="guest.checkin.toggle",
        entity_type="guest",
        entity_id=guest_id,
        event_id=event_id,
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", None),
        details={"checkedIn": new_val}
    )
    return new_val

def list_guests(
    event_id: str,
    q: Optional[str] = None,
    tags_any: Optional[List[str]] = None,
    limit: int = 50,
    page_token: Optional[str] = None,
    order_by: str = "createdAt",
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Returns (items, next_page_token). Paginates using start_after(last_doc).
    Supports:
      - q: prefix on email+name via searchPrefixes
      - tags_any: array-contains-any (normalized to lowercase)
    """
    db = get_db()
    ref = _guests_col(db, event_id)

    if tags_any:
        tags_any = [t.strip().lower() for t in tags_any if t and t.strip()]
        if tags_any:
            ref = ref.where("tags", "array-contains-any", tags_any[:10])

    if q:
        ref = ref.where("searchPrefixes", "array-contains", q.lower())

    ref = ref.order_by(order_by)

    if page_token:
        cursor_doc = _guests_col(db, event_id).document(page_token).get()
        if cursor_doc.exists:
            ref = ref.start_after(cursor_doc)

    snaps = list(ref.limit(limit).stream())
    items = [{**(s.to_dict() or {}), "id": s.id} for s in snaps]
    next_token = snaps[-1].id if len(snaps) == limit else None
    return items, next_token
