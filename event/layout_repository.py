# event/layout_repository.py
from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from SiPanit.firebase import get_db
from google.cloud import firestore_v1 as firestore  # <-- use module, not Transaction class

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------- Firestore paths ----------
# events/{event_id}/layout/meta                (Document)
# events/{event_id}/layout/meta/elements/*     (Collection)

def _meta_ref(event_id: str):
    # DocumentReference → can .collection("elements")
    return (
        get_db()
        .collection("events")
        .document(event_id)
        .collection("layout")
        .document("meta")
    )

def _elements_coll(event_id: str):
    # elements collection under meta document
    return _meta_ref(event_id).collection("elements")

# ---------- Queries ----------
def get_layout(event_id: str) -> Optional[Dict[str, Any]]:
    meta_snap = _meta_ref(event_id).get()
    if not meta_snap.exists:
        return None

    meta = meta_snap.to_dict() or {}

    # stream elements outside a transaction
    elements: List[Dict[str, Any]] = []
    for doc in _elements_coll(event_id).stream():
        d = doc.to_dict() or {}
        elements.append({
            "id": doc.id,
            "type": d.get("type"),
            "name": d.get("name"),
            "capacity": d.get("capacity", 0),
            "geom": d.get("geom", {}),
            "assigned_guest_ids": d.get("assigned_guest_ids", []),
        })

    return {
        "event_id": event_id,
        "version": int(meta.get("version", 1)),
        "canvas": meta.get("canvas", {}),
        "elements": elements,
        "konva_snapshot": meta.get("konva_snapshot"),
        "updatedAt": meta.get("updatedAt"),
        "createdAt": meta.get("createdAt"),
    }

# ---------- Commands (optimistic lock) ----------
def save_layout(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimistic lock via meta.version:
      - If incoming version != current → conflict
      - If same → bump version (+1), upsert elements, delete removed ones
    """
    db = get_db()
    event_id: str = payload["event_id"]
    incoming_ver: int = int(payload["version"])

    meta_ref = _meta_ref(event_id)
    elements_coll = _elements_coll(event_id)

    # current element ids (outside tx)
    current_ids = {doc.id for doc in elements_coll.stream()}

    @firestore.transactional  # <-- correct way
    def _tx_fn(transaction: firestore.Transaction) -> Dict[str, Any]:
        meta_snap = meta_ref.get(transaction=transaction)

        # init meta if missing
        if not meta_snap.exists:
            meta_doc = {
                "version": 1,
                "canvas": payload.get("canvas", {}),
                "konva_snapshot": payload.get("konva_snapshot"),
                "updatedAt": _now_iso(),
                "createdAt": _now_iso(),
            }
            transaction.set(meta_ref, meta_doc)
            current_ver = 1
        else:
            meta = meta_snap.to_dict() or {}
            current_ver = int(meta.get("version", 1))

        # version check
        if current_ver != incoming_ver:
            return {"conflict": True, "current_version": current_ver}

        # bump version
        new_version = current_ver + 1
        transaction.update(meta_ref, {
            "version": new_version,
            "canvas": payload.get("canvas", {}),
            "konva_snapshot": payload.get("konva_snapshot"),
            "updatedAt": _now_iso(),
        })

        # upsert elements
        incoming_ids = set()
        for el in payload.get("elements", []):
            el_id = el["id"]
            incoming_ids.add(el_id)
            el_ref = elements_coll.document(el_id)
            transaction.set(el_ref, {
                "type": el.get("type"),
                "name": el.get("name"),
                "capacity": el.get("capacity", 0),
                "geom": el.get("geom", {}),
                "assigned_guest_ids": el.get("assigned_guest_ids", []),
                "updatedAt": _now_iso(),
            }, merge=True)

        # delete removed elements
        to_delete = list(current_ids - incoming_ids)
        for _id in to_delete:
            transaction.delete(elements_coll.document(_id))

        return {"conflict": False, "version": new_version}

    # run the transaction
    transaction = db.transaction()
    result = _tx_fn(transaction)
    if result.get("conflict"):
        return {"conflict": True, "current_version": result["current_version"]}
    return {"conflict": False, "version": result["version"]}