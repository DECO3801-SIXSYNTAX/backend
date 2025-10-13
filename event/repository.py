from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from SiPanit.firebase import get_db
from google.cloud.firestore_v1 import ArrayUnion, ArrayRemove

COLL = "events"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _with_audit_on_create(data: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(data or {})
    d.setdefault("createdAt", _now_iso())
    d["updatedAt"] = _now_iso()
    # pastikan field yang dipakai FE selalu ada
    d.setdefault("collaborators", [])
    return d


def _with_audit_on_update(data: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(data or {})
    d["updatedAt"] = _now_iso()
    return d


def _norm_company(c: Optional[str]) -> str:
    return (c or "").strip().upper()


def list_events(owner_id: Optional[str] = None, company: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List events dengan filter optional:
    - owner_id: hanya event yang dibuat oleh user tsb
    - company : hanya event milik company tsb (tenancy boundary)
    """
    db = get_db()
    q = db.collection(COLL)

    if company:
        q = q.where("company", "==", _norm_company(company))
    if owner_id:
        q = q.where("createdBy", "==", owner_id)

    return [{**doc.to_dict(), "id": doc.id} for doc in q.stream()]


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    snap = get_db().collection(COLL).document(event_id).get()
    return ({**snap.to_dict(), "id": snap.id} if snap.exists else None)


def upsert_event(data: Dict[str, Any]) -> str:
    """
    Simpan event; pastikan field 'company' ternormalisasi dan ikut disimpan.
    """
    db = get_db()
    event_id = data.get("id") or db.collection(COLL).document().id
    ref = db.collection(COLL).document(event_id)
    exists = ref.get().exists

    payload = dict(data or {})
    payload["company"] = _norm_company(payload.get("company"))

    payload = _with_audit_on_update(payload) if exists else _with_audit_on_create(payload)
    ref.set(payload, merge=True)
    return event_id


def delete_event(event_id: str) -> None:
    get_db().collection(COLL).document(event_id).delete()


# -------- Collaborators (atomic) --------

def add_collaborator(event_id: str, user_id: str) -> None:
    ref = get_db().collection(COLL).document(event_id)
    ref.update({
        "collaborators": ArrayUnion([str(user_id)]),
        "updatedAt": _now_iso(),
    })


def remove_collaborator(event_id: str, user_id: str) -> None:
    ref = get_db().collection(COLL).document(event_id)
    ref.update({
        "collaborators": ArrayRemove([str(user_id)]),
        "updatedAt": _now_iso(),
    })