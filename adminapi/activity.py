from typing import Optional, Dict, Any
from firebase_admin import firestore
from SiPanit.firebase import get_db

def log_activity(
    *,
    action: str,                 # e.g. "guest.create", "guest.update", "guest.delete", "guest.checkin.toggle", "event.upsert"
    entity_type: str,            # "guest" | "event"
    entity_id: str,
    event_id: Optional[str],
    actor_id: Optional[str],
    actor_email: Optional[str],
):
    db = get_db()
    db.collection("activity").add({
        "ts": firestore.SERVER_TIMESTAMP,
        "action": action,
        "entityType": entity_type,
        "entityId": entity_id,
        "eventId": event_id,
        "actorId": actor_id,
        "actorEmail": actor_email,
    })
