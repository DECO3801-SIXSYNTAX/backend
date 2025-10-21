# event/layout_repository.py
from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from SiPanit.firebase import get_db
from google.cloud import firestore  # module import for Transaction

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------- Firestore paths ----------
# events/{event_id}/floorplan/metadata         (Document)
# events/{event_id}/floorplan/metadata/elements/*  (Collection)

def _meta_ref(event_id: str):
    # DocumentReference → can .collection("elements")
    return (
        get_db()
        .collection("events")
        .document(event_id)
        .collection("floorplan")
        .document("metadata")
    )

def _elements_coll(event_id: str):
    # elements collection under metadata document
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
            # support both: nested 'geom' (old) or flat coords (new)
            "geom": (d.get("geom") or {k: d.get(k) for k in ("x","y","width","height","rotation","radius","color") if k in d}),
            # support both: snake_case (old) or camelCase (new)
            "assigned_guest_ids": (d.get("assigned_guest_ids") or d.get("assignedGuests") or []),
        })

    return {
        "event_id": event_id,
        "version": int(meta.get("version", 1)),
        "canvas": (meta.get("canvas") or {
            "width": (meta.get("canvasSize") or {}).get("width"),
            "height": (meta.get("canvasSize") or {}).get("height"),
            "px_per_m": meta.get("pixelsPerMeter"),
            "roomBoundary": meta.get("roomBoundary"),
            "floorplan_id": meta.get("floorplan_id"),
        }),
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

    @firestore.transactional
    def _tx_fn(transaction: firestore.Transaction) -> Dict[str, Any]:
        meta_snap = transaction.get(meta_ref)
        current_meta = meta_snap.to_dict() if meta_snap.exists else {}
        current_version = int(current_meta.get("version", 1))

        if current_version != incoming_ver:
            return {"conflict": True, "current_version": current_version}

        new_version = current_version + 1
        transaction.set(meta_ref, {
            "version": new_version,
            "updatedAt": _now_iso(),
        }, merge=True)

        incoming_ids: set[str] = set()
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

    transaction = db.transaction()
    result = _tx_fn(transaction)
    if result.get("conflict"):
        return {"conflict": True, "current_version": result["current_version"]}
    return {"conflict": False, "version": result["version"]}
