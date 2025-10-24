from __future__ import annotations
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
    """Full normalization for create/upsert - includes all fields"""
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

def _normalize_guest_payload_partial(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Partial normalization - only includes fields present in data.
    This prevents overwriting existing fields with empty values.
    """
    out = {}
    
    if "name" in data:
        out["name"] = (data.get("name") or "").strip()
    if "email" in data:
        out["email"] = (data.get("email") or "").lower().strip()
    if "phone" in data:
        out["phone"] = (data.get("phone") or "").strip()
    if "dietaryRestriction" in data:
        out["dietaryRestriction"] = (data.get("dietaryRestriction") or "").strip()
    if "accessibilityNeeds" in data:
        out["accessibilityNeeds"] = (data.get("accessibilityNeeds") or "").strip()
    if "checkedIn" in data:
        out["checkedIn"] = bool(data.get("checkedIn"))
    if "seat" in data and data.get("seat"):
        out["seat"] = (data.get("seat") or "").strip()
    
    # Only recompute tags when the related fields are touched
    if ("dietaryRestriction" in data) or ("accessibilityNeeds" in data):
        diet   = out.get("dietaryRestriction", (data.get("dietaryRestriction") or "").strip())
        access = out.get("accessibilityNeeds", (data.get("accessibilityNeeds") or "").strip())
        out["tags"] = _split_tags(diet, access)
    
    return out

def update_doc(doc_ref, updates: Dict[str, Any]) -> None:
    """Helper to update a document with timestamp"""
    if not updates:
        return
    updates = {**updates, "updatedAt": firestore.SERVER_TIMESTAMP}
    doc_ref.update(updates)

def partial_update_guest(event_id: str, guest_id: str, data: Dict[str, Any], *, actor=None) -> str:
    """
    Update only specified fields without overwriting other existing fields.
    Prevents data loss when updating single fields like 'seat' or 'checkedIn'.
    """
    db = get_db()
    ref = _guests_col(db, event_id).document(str(guest_id))
    snap = ref.get()
    if not snap.exists:
        raise LookupError("Guest not found")
    
    payload = _normalize_guest_payload_partial(data)
    update_doc(ref, payload)
    
    log_activity(
        action="guest.update",
        entity_type="guest",
        entity_id=str(guest_id),
        event_id=event_id,
        actor_id=str(getattr(actor, "id", None)),
        actor_email=getattr(actor, "email", None),
    )
    return str(guest_id)

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
        #details={"name": payload.get("name"), "email": payload.get("email")}
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
    # Map Firestore fields to frontend-expected fields
    items = []
    for s in snaps:
        data = s.to_dict() or {}
        # Map field names for frontend compatibility
        mapped = {
            **data,
            "id": s.id,
            "dietaryNeeds": data.get("dietaryRestriction", ""),  # Map to frontend field
            "accessibility": data.get("accessibilityNeeds", ""),  # Map to frontend field
            "table": data.get("seat", ""),  # Map seat to table for frontend
        }
        items.append(mapped)
    next_token = snaps[-1].id if len(snaps) == limit else None
    return items, next_token


def get_guest(event_id: str, guest_id: str) -> dict | None:
    res = list_guests(event_id=event_id, limit=10000)
    items = res[0] if isinstance(res, tuple) else res
    for x in items or []:
        if str(x.get("id")) == str(guest_id):
            # Already mapped by list_guests, so just return it
            return x
    return None

def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    print(f"  🔍 get_event() called with event_id: {event_id}")
    try:
        db = get_db()
        print(f"  ✅ Firestore DB connected")
        
        print(f"  🔍 Fetching document from collection: {COLL}, document: {event_id}")
        doc = db.collection(COLL).document(event_id).get()
        
        print(f"  ✅ Document fetched, exists: {doc.exists}")
        
        if not doc.exists:
            print(f"  ❌ Document does not exist")
            return None
            
        data = doc.to_dict() or {}
        data["id"] = doc.id
        print(f"  ✅ Event data retrieved: {data.get('name', 'N/A')}")
        return data
        
    except Exception as e:
        print(f"  ❌ Error in get_event(): {e}")
        import traceback
        traceback.print_exc()
        return None  # Return None instead of raising    print(f"  🔍 get_event() called with event_id: {event_id}")
    try:
        db = get_db()
        print(f"  ✅ Firestore DB connected")
        
        print(f"  🔍 Fetching document from collection: {COLL}, document: {event_id}")
        
        # Add timeout to prevent hanging
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Firestore query timed out after 10 seconds")
        
        # Set 10 second timeout (only works on Unix/Mac)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        
        try:
            doc = db.collection(COLL).document(event_id).get()
            signal.alarm(0)  # Cancel timeout
        except TimeoutError as e:
            print(f"  ❌ Timeout: {e}")
            raise
        
        print(f"  ✅ Document fetched, exists: {doc.exists}")
        
        if not doc.exists:
            print(f"  ❌ Document does not exist")
            return None
            
        data = doc.to_dict() or {}
        data["id"] = doc.id
        print(f"  ✅ Event data retrieved: {data.get('name', 'N/A')}")
        return data
        
    except Exception as e:
        print(f"  ❌ Error in get_event(): {e}")
        import traceback
        traceback.print_exc()
        raise
    print(f"  🔍 get_event() called with event_id: {event_id}")
    try:
        db = get_db()
        print(f"  ✅ Firestore DB connected")
        
        print(f"  🔍 Fetching document from collection: {COLL}, document: {event_id}")
        doc = db.collection(COLL).document(event_id).get()
        
        print(f"  ✅ Document fetched, exists: {doc.exists}")
        
        if not doc.exists:
            print(f"  ❌ Document does not exist")
            return None
            
        data = doc.to_dict() or {}
        data["id"] = doc.id
        print(f"  ✅ Event data retrieved: {data.get('name', 'N/A')}")
        return data
        
    except Exception as e:
        print(f"  ❌ Error in get_event(): {e}")
        import traceback
        traceback.print_exc()
        raise

def resolve_guest_email_from_event(event: Dict[str, Any], guest_id: str) -> Optional[str]:
    gid = str(guest_id)

    guest_index = event.get("guestIndex")
    if isinstance(guest_index, dict):
        node = guest_index.get(gid)
        if isinstance(node, dict):
            email = (node.get("email") or "").strip().lower()
            if email:
                return email

    guest_emails = event.get("guestEmails")
    if isinstance(guest_emails, dict):
        email = (guest_emails.get(gid) or "").strip().lower()
        if email:
            return email

    guests_arr = event.get("guests")
    if isinstance(guests_arr, list):
        for g in guests_arr:
            if isinstance(g, dict):
                cand_id = str(g.get("id") or g.get("uid") or g.get("guest_id") or "")
                if cand_id == gid:
                    email = (g.get("email") or "").strip().lower()
                    if email:
                        return email
    return None

