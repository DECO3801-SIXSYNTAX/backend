# event/views.py
from __future__ import annotations

from django.utils.timezone import now
from rest_framework import viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import IsPlanner
from .serializers import (
    EventSerializer,
    LayoutSaveSer,
    FEFloorPlanSer,
)
from . import repository as erepo
from .layout_repository import get_layout as lr_get_layout, save_layout as lr_save_layout


# =========================
# Helpers (RBAC & mapping)
# =========================

def _same_id(a, b) -> bool:
    return str(a).strip() == str(b).strip()

def _can_access_event(user, event_dict) -> bool:
    if not event_dict:
        return False
    if getattr(user, "is_superuser", False):
        return True
    uid = str(getattr(user, "pk", getattr(user, "id", "")))
    owner_ok = _same_id(event_dict.get("createdBy"), uid)
    collabs = set(map(str, (event_dict.get("collaborators") or [])))
    return owner_ok or (uid in collabs)

def _can_access_event_id(user, event_id: str):
    ev = erepo.get_event(event_id)
    return (_can_access_event(user, ev), ev)

# --- mapping repo <-> FE ---
def _layout_to_fe(event_id: str, layout: dict | None) -> dict:
    canvas = (layout or {}).get("canvas", {}) or {}
    els = (layout or {}).get("elements", []) or []

    fe_elements = []
    for e in els:
        geom = e.get("geom", {}) or {}
        meta = geom.get("meta", {}) or {}
        item = {
            "id": e.get("id"),
            "type": e.get("type"),
            "x": geom.get("x", 0),
            "y": geom.get("y", 0),
            "width": geom.get("width", 80),
            "height": geom.get("height", 60),
            "rotation": geom.get("rotation", 0),
            "capacity": e.get("capacity", 0),
            "name": e.get("name"),
            "assignedGuests": e.get("assigned_guest_ids", []),
            "config": {
                "id": meta.get("configId", e.get("type")),
                "shape": meta.get("shape", "rounded-rect"),
                "icon": {},  # FE menentukan icon sendiri
                "label": meta.get("label", e.get("type")),
                "color": geom.get("color", "#8B5CF6"),
                "textColor": meta.get("textColor", "#FFFFFF"),
                "defaultWidth": meta.get("defaultWidth", int(geom.get("width", 80))),
                "defaultHeight": meta.get("defaultHeight", int(geom.get("height", 60))),
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
# Event CRUD
# =========================

class EventViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsPlanner]

    def list(self, request):
        mine = request.query_params.get("mine")
        owner_id = str(request.user.id) if mine == "1" else None
        rows = erepo.list_events(owner_id)

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
        ser = EventSerializer(data=data)
        ser.is_valid(raise_exception=True)
        eid = erepo.upsert_event(ser.validated_data)
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
        ser = EventSerializer(data=data)
        ser.is_valid(raise_exception=True)
        eid = erepo.upsert_event(ser.validated_data)
        return Response({"id": eid})

    def destroy(self, request, pk=None):
        current = erepo.get_event(pk)
        if not current:
            return Response(status=204)
        if not _can_access_event(request.user, current):
            return Response({"detail": "Forbidden"}, status=403)
        erepo.delete_event(pk)
        return Response(status=204)


# =========================================
# Layout endpoints — now FE-friendly
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

        # --- Payload lama (tetap didukung)
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

        # kembalikan FE-shape juga supaya konsisten
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


# =========================
# (optional) meta endpoint
# =========================

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