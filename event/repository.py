# event/repository.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from SiPanit.firebase import get_db

COLL = "events"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _with_audit_on_create(data: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(data or {})
    d.setdefault("createdAt", _now_iso())
    d["updatedAt"] = _now_iso()
    return d

def _with_audit_on_update(data: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(data or {})
    d["updatedAt"] = _now_iso()
    return d

def list_events(owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    db = get_db()
    coll = db.collection(COLL)
    q = coll.where("createdBy", "==", owner_id) if owner_id else coll
    return [{**doc.to_dict(), "id": doc.id} for doc in q.stream()]

def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    snap = get_db().collection(COLL).document(event_id).get()
    return ({**snap.to_dict(), "id": snap.id} if snap.exists else None)

def upsert_event(data: Dict[str, Any]) -> str:
    db = get_db()
    event_id = data.get("id") or db.collection(COLL).document().id
    exists = db.collection(COLL).document(event_id).get().exists
    payload = _with_audit_on_update(data) if exists else _with_audit_on_create(data)
    db.collection(COLL).document(event_id).set(payload, merge=True)
    return event_id

def delete_event(event_id: str) -> None:
    get_db().collection(COLL).document(event_id).delete()
