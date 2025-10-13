from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, PermissionDenied

from authentication.permissions import IsPlanner
from .serializers import (
    EventSerializer,
    LayoutSaveSer,
    FEFloorPlanSer,
    # pastikan kamu punya serializer ini: email (required), name/company/message (optional)
    InviteVendorSer,
)
from . import repository as erepo
from .layout_repository import get_layout as lr_get_layout, save_layout as lr_save_layout

from adminapi.activity import log_activity
User = get_user_model()


# =========================
# Helpers (RBAC & tenancy)
# =========================

def _same_id(a, b) -> bool:
    return str(a).strip() == str(b).strip()


def _same_company(a, b) -> bool:
    return (a or "").strip().upper() == (b or "").strip().upper()


def _can_access_event(user, event_dict) -> bool:
    """
    Superuser = boleh.
    Owner atau collaborator event = boleh.
    """
    if not event_dict:
        return False
    if getattr(user, "is_superuser", False):
        return True

    uid = str(getattr(user, "pk", getattr(user, "id", "")))
    owner_ok = str(event_dict.get("createdBy")) == uid
    collabs = set(map(str, (event_dict.get("collaborators") or [])))
    return owner_ok or (uid in collabs)


def _can_access_event_id(user, event_id: str):
    ev = erepo.get_event(event_id)
    return (_can_access_event(user, ev), ev)


# =========================
# Mapping repo <-> FE model
# =========================

def _layout_to_fe(event_id: str, layout: dict | None) -> dict:
    canvas = (layout or {}).get("canvas", {}) or {}
    els = (layout or {}).get("elements", []) or []

    fe_elements = []
    for e in els:
        geom = e.get("geom", {}) or {}
        meta = geom.get("meta", {}) or {}
        # jaga-jaga kalau width/height bukan angka
        width_val = geom.get("width", 80)
        height_val = geom.get("height", 60)
        width_val = width_val if isinstance(width_val, (int, float)) else 80
        height_val = height_val if isinstance(height_val, (int, float)) else 60

        item = {
            "id": e.get("id"),
            "type": e.get("type"),
            "x": geom.get("x", 0),
            "y": geom.get("y", 0),
            "width": width_val,
            "height": height_val,
            "rotation": geom.get("rotation", 0),
            "capacity": e.get("capacity", 0),
            "name": e.get("name"),
            "assignedGuests": e.get("assigned_guest_ids", []),
            "config": {
                "id": meta.get("configId", e.get("type")),
                "shape": meta.get("shape", "rounded-rect"),
                "icon": {},
                "label": meta.get("label", e.get("type")),
                "color": geom.get("color", "#8B5CF6"),
                "textColor": meta.get("textColor", "#FFFFFF"),
                "defaultWidth": int(width_val),
                "defaultHeight": int(height_val),
                "defaultRadius": meta.get("defaultRadius"),
                "description": meta.get("description", "")
            }
        }
        if geom.get("radius") is not None:
            item["radius"] = geom.get("radius")
        fe_elements.append(item)

    return {
        "id": canvas.get("floorplan_id") or f"fp-{event_id}",
        "eventId": event_id,
        "canvasSize": {
            "width": canvas.get("width", 1200),
            "height": canvas.get("height", 800)
        },
        "pixelsPerMeter": canvas.get("px_per_m", 50),
        "elements": fe_elements,
        "roomBoundary": canvas.get("roomBoundary"),
        "createdAt": (layout or {}).get("createdAt", ""),
        "updatedAt": (layout or {}).get("updatedAt", ""),
    }


def _fe_to_layout_payload(fe: dict, current_version: int) -> dict:
    elements = []
    for el in fe.get("elements", []):
        cfg = el.get("config", {}) or {}
        elements.append({
            "id": el["id"],
            "type": el["type"],
            "name": el.get("name"),
            "capacity": el.get("capacity", 0),
            "geom": {
                "x": el.get("x", 0),
                "y": el.get("y", 0),
                "width": el.get("width", 80),
                "height": el.get("height", 60),
                "rotation": el.get("rotation", 0),
                "radius": el.get("radius"),
                "color": cfg.get("color"),
                "meta": {
                    "configId": cfg.get("id"),
                    "shape": cfg.get("shape"),
                    "label": cfg.get("label"),
                    "textColor": cfg.get("textColor"),
                    "defaultWidth": cfg.get("defaultWidth"),
                    "defaultHeight": cfg.get("defaultHeight"),
                    "defaultRadius": cfg.get("defaultRadius"),
                    "description": cfg.get("description"),
                }
            },
            "assigned_guest_ids": el.get("assignedGuests", []),
        })

    canvas_size = fe.get("canvasSize") or {}
    canvas = {
        "width": canvas_size.get("width", 1200),
        "height": canvas_size.get("height", 800),
        "grid": 20,
        "scale": 1,
        "px_per_m": fe.get("pixelsPerMeter", 50),
        "roomBoundary": fe.get("roomBoundary"),
        "floorplan_id": fe.get("id") or None,
    }

    return {
        "event_id": fe["eventId"],
        "version": int(current_version),
        "canvas": canvas,
        "elements": elements,
        "konva_snapshot": None,
    }


# =========================
# Event CRUD (company-aware) + invite/remove vendor
# =========================

class EventViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsPlanner]

    # --- helper: hanya owner atau superuser yang boleh edit collaborators
    def _require_owner(self, request, ev: dict):
        uid = str(request.user.id)
        if getattr(request.user, "is_superuser", False):
            return
        if str(ev.get("createdBy")) != uid:
            raise PermissionDenied("Only event owner can modify collaborators.")

    def list(self, request):
        mine = request.query_params.get("mine")
        owner_id = str(request.user.id) if mine == "1" else None
        company = getattr(request.user, "company", None)
        rows = erepo.list_events(owner_id=owner_id, company=company)

        enriched = []
        for e in rows:
            try:
                lay = lr_get_layout(e["id"]) or {}
                e_with_ver = {
                    **e,
                    "layout_version": int(lay.get("version", 1)),
                    "layout_updatedAt": lay.get("updatedAt"),
                }
            except Exception:
                e_with_ver = {**e, "layout_version": 1, "layout_updatedAt": None}
            enriched.append(e_with_ver)

        return Response(enriched)

    def retrieve(self, request, pk=None):
        item = erepo.get_event(pk)
        if not item:
            return Response({"detail": "Not found"}, status=404)
        if not _can_access_event(request.user, item):
            return Response({
                "detail": "Forbidden",
                "reason": "not_owner_or_collaborator",
                "createdBy": item.get("createdBy"),
                "me": str(request.user.id)
            }, status=403)
        return Response(item)

    def create(self, request):
        data = dict(request.data)
        data["createdBy"] = str(request.user.id)
        data["company"] = (getattr(request.user, "company", "") or "").strip().upper()

        ser = EventSerializer(data=data)
        ser.is_valid(raise_exception=True)
        eid = erepo.upsert_event(ser.validated_data)
        log_activity(
                action="event.creation",           
                entity_type="event",
                entity_id=str(eid),
                event_id=str(eid),
                actor_id=str(getattr(request.user, "id", "")),
                actor_email=getattr(request.user, "email", None),
                #details=changed_fields,          
            )
        return Response({"id": eid}, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        current = erepo.get_event(pk)
        if not current:
            return Response({"detail": "Not found"}, status=404)
        if not _can_access_event(request.user, current):
            return Response({"detail": "Forbidden"}, status=403)

        data = dict(request.data)
        data["id"] = pk
        data["createdBy"] = current.get("createdBy")
        data["company"] = current.get("company")  # jangan pindah company lewat update

        ser = EventSerializer(data=data)
        ser.is_valid(raise_exception=True)
        eid = erepo.upsert_event(ser.validated_data)
        log_activity(
                action="event.update",
                entity_type="event",
                entity_id=str(current.id),
                event_id=str(current.id),
                actor_id=str(getattr(request.user, "id", "")),
                actor_email=getattr(request.user, "email", None),
                #details=changed_fields,
            )
        return Response({"id": eid})

    def destroy(self, request, pk=None):
        current = erepo.get_event(pk)
        if not current:
            return Response(status=204)
        if not _can_access_event(request.user, current):
            return Response({"detail": "Forbidden"}, status=403)
        erepo.delete_event(pk)
        log_activity(
                action="event.delete",
                entity_type="event",
                entity_id=str(current.id),
                event_id=str(current.id),
                actor_id=str(getattr(request.user, "id", "")),
                actor_email=getattr(request.user, "email", None),
                #details=changed_fields,
            )
        return Response(status=204)

    # -------- Collaborators --------

    @action(detail=True, methods=["post"], url_path="invite-collaborator")
    def invite_collaborator(self, request, pk=None):
        """
        Body: { "user_id": "<uuid>" }  ATAU  { "email": "vendor@x.com" }
        Target harus user yang ada dengan role='vendor'.
        """
        ev = erepo.get_event(pk)
        if not ev:
            return Response({"detail": "Not found"}, status=404)
        self._require_owner(request, ev)

        user_id = (request.data.get("user_id") or "").strip()
        email = (request.data.get("email") or "").strip().lower()

        target = None
        if user_id:
            try:
                target = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise ValidationError({"user_id": "User not found."})
        elif email:
            try:
                target = User.objects.get(email=email)
            except User.DoesNotExist:
                raise ValidationError({"email": "User not found."})
        else:
            raise ValidationError("Provide 'user_id' or 'email'.")

        if getattr(target, "role", "") != "vendor":
            raise ValidationError("Target user must have role 'vendor'.")

        erepo.add_collaborator(pk, str(target.id))
        # return state terbaru
        latest = erepo.get_event(pk) or {}
        return Response({"detail": "Collaborator invited", "collaborators": latest.get("collaborators", [])})

    @action(detail=True, methods=["post"], url_path="remove-collaborator")
    def remove_collaborator(self, request, pk=None):
        """
        Body: { "user_id": "<uuid>" }  ATAU  { "email": "vendor@x.com" }
        """
        ev = erepo.get_event(pk)
        if not ev:
            return Response({"detail": "Not found"}, status=404)
        self._require_owner(request, ev)

        user_id = (request.data.get("user_id") or "").strip()
        email = (request.data.get("email") or "").strip().lower()

        tid = None
        if user_id:
            tid = user_id
        elif email:
            try:
                tid = str(User.objects.only("id").get(email=email).id)
            except User.DoesNotExist:
                return Response({"detail": "No such user; nothing to remove."})
        else:
            raise ValidationError("Provide 'user_id' or 'email'.")

        erepo.remove_collaborator(pk, str(tid))
        latest = erepo.get_event(pk) or {}
        return Response({"detail": "Collaborator removed", "collaborators": latest.get("collaborators", [])})

    @action(detail=True, methods=["post"], url_path="invite-vendor")
    def invite_vendor(self, request, pk=None):
        """
        Membuat (jika belum ada) user role=vendor lalu menambahkannya ke collaborators.
        Body: { "email": "<required>", "name": "optional", "company": "optional", "message": "optional" }
        """
        ev = erepo.get_event(pk)
        if not ev:
            return Response({"detail": "Not found"}, status=404)
        self._require_owner(request, ev)

        ser = InviteVendorSer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()
        name = ser.validated_data.get("name") or ""
        vend_company = (ser.validated_data.get("company") or "").strip() or None

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "role": "vendor",
                "first_name": name.split(" ")[0] if name else "",
                "last_name": " ".join(name.split(" ")[1:]) if " " in name else "",
                "company": vend_company,
                "is_active": True,
            },
        )
        if not created and user.role != "vendor":
            return Response({"detail": "Target user bukan vendor.", "role": user.role}, status=400)

        erepo.add_collaborator(pk, str(user.id))
        latest = erepo.get_event(pk) or {}
        return Response(
            {"detail": "Vendor invited", "user_id": str(user.id), "created_user": created,
             "collaborators": latest.get("collaborators", [])},
            status=status.HTTP_200_OK,
        )


# =========================================
# Layout endpoints — FE-friendly + locking
# =========================================

class LayoutSaveView(APIView):
    """
    POST /api/event/layouts/save/
    - Bisa menerima:
      a) FE floorplan payload (disarankan)
      b) Payload lama (event_id/version/canvas/elements)
    - Response: FE floorplan.
    """
    permission_classes = [permissions.IsAuthenticated, IsPlanner]

    def post(self, request):
        body = request.data or {}

        # --- FE payload?
        if "eventId" in body and "canvasSize" in body and "elements" in body:
            fe_ser = FEFloorPlanSer(data=body)
            fe_ser.is_valid(raise_exception=True)
            fe = fe_ser.validated_data

            allowed, _ = _can_access_event_id(request.user, fe["eventId"])
            if not allowed:
                return Response({"detail": "Forbidden"}, status=403)

            current = lr_get_layout(fe["eventId"]) or {"version": 1}
            payload = _fe_to_layout_payload(fe, int(current.get("version", 1)))
            result = lr_save_layout(payload)
            if result.get("conflict"):
                payload["version"] = int(result["current_version"])
                result = lr_save_layout(payload)

            saved = lr_get_layout(fe["eventId"])
            return Response(_layout_to_fe(fe["eventId"], saved), status=200)

        # --- Legacy payload (tetap didukung)
        legacy_ser = LayoutSaveSer(data=body)
        legacy_ser.is_valid(raise_exception=True)
        data = legacy_ser.validated_data

        allowed, ev = _can_access_event_id(request.user, data["event_id"])
        if not allowed:
            return Response({
                "detail": "Forbidden",
                "reason": "event_not_found" if not ev else "not_owner_or_collaborator",
                "createdBy": ev.get("createdBy") if ev else None,
                "me": str(request.user.id),
            }, status=403)

        result = lr_save_layout(data)
        if result.get("conflict"):
            data["version"] = int(result["current_version"])
            result = lr_save_layout(data)
            if result.get("conflict"):
                return Response({
                    "type": "https://httpstatuses.com/409",
                    "title": "Conflict",
                    "status": 409,
                    "detail": "Layout version is stale.",
                    "current_version": result["current_version"]
                }, status=409)

        saved = lr_get_layout(data["event_id"])
        return Response(_layout_to_fe(data["event_id"], saved), status=200)


class LayoutReadView(APIView):
    """
    GET /api/event/layouts/<event_id>/
    - Selalu balikan format FE floorplan agar FE bisa langsung render.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, event_id: str):
        allowed, _ = _can_access_event_id(request.user, event_id)
        if not allowed:
            return Response({"detail": "Forbidden"}, status=403)

        layout = lr_get_layout(event_id)
        if not layout:
            empty = _layout_to_fe(event_id, {
                "canvas": {"width": 1200, "height": 800, "px_per_m": 50},
                "elements": [],
                "updatedAt": now().isoformat()
            })
            return Response(empty, status=200)

        return Response(_layout_to_fe(event_id, layout), status=200)


class LayoutMetaView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlanner]

    def get(self, request, event_id: str):
        ev = erepo.get_event(event_id)
        if not ev:
            return Response({"detail": "Not found"}, status=404)
        if not _can_access_event(request.user, ev):
            return Response({"detail": "Forbidden"}, status=403)

        layout = lr_get_layout(event_id) or {}
        return Response({
            "event_id": event_id,
            "version": int(layout.get("version", 1)),
            "updatedAt": layout.get("updatedAt"),
            "has_elements": bool(layout.get("elements")),
        }, status=200)


# =========================
# Event stats
# =========================

class EventStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPlanner]

    def get(self, request, event_id: str):
        allowed, ev = _can_access_event_id(request.user, event_id)
        if not allowed or not ev:
            return Response({"detail": "Forbidden"}, status=403)

        # Layout → hitung kursi terpakai
        layout = lr_get_layout(event_id) or {"elements": []}
        assigned = 0
        for el in layout.get("elements", []):
            assigned += len(el.get("assigned_guest_ids", []) or [])

        # Guests (jika kamu simpan di events/{id}/guests)
        from SiPanit.firebase import get_db
        db = get_db()
        guests = list(db.collection("events").document(event_id).collection("guests").stream())
        total_guests = len(guests)

        dietary = 0
        accessibility = 0
        for g in guests:
            d = g.to_dict() or {}
            if d.get("dietaryNeeds"):
                dietary += 1
            if d.get("accessibilityNeeds"):
                accessibility += 1

        completion = 0
        if total_guests > 0:
            completion = round(assigned * 100.0 / total_guests, 2)

        return Response({
            "totalGuests": total_guests,
            "assignedSeats": assigned,
            "dietaryNeeds": dietary,
            "accessibilityNeeds": accessibility,
            "completionRate": completion
        })