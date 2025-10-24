from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from authentication.permissions import IsPlanner
from typing import Optional, List
from urllib.parse import urlparse, parse_qs
import io
import csv
from django.http import HttpResponse
from django.utils.text import slugify
from . import views
from .repository import list_guests, get_guest, get_event, upsert_guest, resolve_guest_email_from_event
from crypto.qr import encrypt_payload, decrypt_payload, qr_png_bytes, decrypt_to_guest
from .emails import send_guest_qr_email

def _format_dt(ts, tz=None):
        """Format Firestore Timestamp or ISO/datetime to 'DD Mon YYYY' and 'H:MM AM/PM'."""
        if not ts:
            return "", ""
        # Firestore Timestamp has .to_datetime()
        if hasattr(ts, "to_datetime"):
            dt = ts.to_datetime()
        else:
            if isinstance(ts, str):
                try:
                    # you imported `datetime` (class) above
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    # fallback: leave date as-is, no time
                    return str(ts), ""
            else:
                dt = ts
        # NOTE: if you store a timezone string, localize here
        date_s = dt.strftime("%d %b %Y")
        # %-I works on Unix; on Windows use %#I. If you need portability, use two branches.
        time_s = dt.strftime("%-I:%M %p") if hasattr(dt, "strftime") else ""
        return date_s, time_s


def _extract_token(raw):
    s = (raw or "").strip()
    if not s:
        return None
    try:
        u = urlparse(s)
        if u.scheme and u.netloc:
            return parse_qs(u.query).get("token", [None])[0]
    except Exception:
        pass
    return s

@api_view(["POST","GET"])
@permission_classes([AllowAny])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def debug_decode_guest(request):
    raw = request.data.get("token") if request.method == "POST" else request.query_params.get("token")
    print(raw,'raw')
    token = _extract_token(raw)
    if not token:
        return Response({"detail": "Token required (JSON/form 'token' or ?token=...)"}, status=400)
    try:
        payload = decrypt_payload(token)            # {"e": "...", "g": "..."}
        guest   = decrypt_to_guest(token, get_guest)
        return Response({"payload": payload, "guest": guest})
    except ValueError as e:
        return Response({"detail": str(e)}, status=401)
    except LookupError as e:
        return Response({"detail": str(e)}, status=404)

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsPlanner])
def bulk_send_invites(request, event_id: str):
    print("\n" + "="*60)
    print("🔍 BULK SEND INVITES START")
    print("="*60)
    print(f"Event ID: {event_id}")
    print(f"User: {request.user}")
    print(f"User role: {getattr(request.user, 'role', 'N/A')}")
    print(f"Request data: {request.data}")
    
    base_url = request.data.get("baseUrl") or "https://app.example.com"
    guest_ids: Optional[List[str]] = request.data.get("guestIds") or None
    
    if guest_ids:
        guest_ids = [str(g).strip() for g in guest_ids if str(g).strip()]
        print(f"Sending to {len(guest_ids)} specific guests")
    else:
        print("Sending to ALL guests")

    # Step 1: Get real event from Firestore
    print("\n📋 Step 1: Getting event from Firestore...")
    try:
        event = get_event(event_id)
        if not event:
            print("❌ Event not found")
            return Response({"detail": "Event not found"}, status=404)
        print(f"✅ Event found: {event.get('name')}")
    except Exception as e:
        print(f"❌ Error getting event: {e}")
        import traceback
        traceback.print_exc()
        return Response({"detail": f"Error getting event: {str(e)}"}, status=500)
    
    # Step 2: Get real guests from Firestore
    print("\n👥 Step 2: Getting guests from Firestore...")
    try:
        result = list_guests(event_id=event_id, limit=5000)
        items = result[0] if isinstance(result, tuple) else result
        
        print(f"   Total guests in event: {len(items)}")
        
        # Filter to specific guests if requested
        if guest_ids:
            targets = [(str(g.get("id")), g) for g in items if str(g.get("id")) in guest_ids]
            print(f"✅ Filtered to {len(targets)} specific guests")
        else:
            targets = [(str(g.get("id")), g) for g in items]
            print(f"✅ Will send to all {len(targets)} guests")
        
        if len(targets) == 0:
            print("⚠️  No guests to send emails to")
            return Response({
                "ok": True,
                "eventId": str(event_id),
                "requested": len(guest_ids) if guest_ids else "all",
                "sent": [],
                "skipped": [],
                "counts": {"sent": 0, "skipped": 0},
            })
            
    except Exception as e:
        print(f"❌ Error getting guests: {e}")
        import traceback
        traceback.print_exc()
        return Response({"detail": f"Error getting guests: {str(e)}"}, status=500)
    
    # Step 3: Prepare event details
    print("\n📝 Step 3: Preparing event details...")
    event_name = event.get("name") or event.get("title") or "Your Event"
    starts_at = event.get("startsAt") or event.get("startDate")
    venue_name = event.get("venueName") or event.get("venue", "")
    venue_addr = event.get("venueAddress") or event.get("address", "")
    org_name = event.get("orgName", "Event Team")
    org_reply = event.get("orgReplyEmail", "no-reply@example.com")
    
    event_date, event_time = _format_dt(starts_at)
    print(f"   Event: {event_name}")
    print(f"   Date: {event_date} at {event_time}")
    print(f"   Venue: {venue_name}")
    
    # Step 4: Send emails
    print(f"\n📧 Step 4: Sending emails to {len(targets)} guests...")
    sent, skipped = [], []
    
    for idx, (gid, guest) in enumerate(targets, 1):
        print(f"\n--- Guest {idx}/{len(targets)}: {gid} ---")
        
        try:
            guest_name = guest.get("name", "")
            guest_email = resolve_guest_email_from_event(event, gid) or (guest.get("email") or "").strip().lower()
            
            print(f"  Name: {guest_name or 'N/A'}")
            print(f"  Email: {guest_email or 'MISSING'}")
            
            if not guest_email:
                print("  ❌ No email address")
                skipped.append({"guestId": gid, "reason": "missing_email"})
                continue

            print("  📧 Sending email...")
            
            try:
                send_guest_qr_email(
                    event_id=str(event_id),
                    guest_id=str(gid),                   
                    guest_email=guest_email,
                    guest_name=guest_name,
                    base_url=base_url,
                    event_name=event_name,
                    event_date=event_date,
                    event_time=event_time,
                    venue_name=venue_name,
                    venue_address=venue_addr,
                    org_name=org_name,
                    org_reply_email=org_reply,
                )
                sent.append(gid)
                print("  ✅ Email sent successfully!")
                
            except Exception as email_err:
                print(f"  ❌ Email error: {email_err}")
                import traceback
                traceback.print_exc()
                skipped.append({"guestId": gid, "reason": f"email_error: {str(email_err)}"})
                
        except Exception as guest_err:
            print(f"  ❌ Processing error: {guest_err}")
            import traceback
            traceback.print_exc()
            skipped.append({"guestId": gid, "reason": f"error: {str(guest_err)}"})

    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    print(f"✅ Successfully sent: {len(sent)}")
    print(f"❌ Skipped: {len(skipped)}")
    if sent:
        print(f"\nEmails sent to guest IDs:")
        for gid in sent:
            print(f"  - {gid}")
    if skipped:
        print(f"\nSkipped:")
        for skip in skipped[:10]:  # Show first 10
            print(f"  - {skip['guestId']}: {skip['reason']}")
    print("="*60 + "\n")
    
    return Response({
        "ok": True,
        "eventId": str(event_id),
        "requested": len(guest_ids) if guest_ids else "all",
        "sent": sent,
        "skipped": skipped,
        "counts": {"sent": len(sent), "skipped": len(skipped)},
    })
    print("\n" + "="*60)
    print("🔍 BULK SEND INVITES START (MOCK MODE)")
    print("="*60)
    print(f"Event ID: {event_id}")
    print(f"User: {request.user}")
    print(f"User role: {getattr(request.user, 'role', 'N/A')}")
    print(f"Request data: {request.data}")
    
    base_url = request.data.get("baseUrl") or "https://app.example.com"
    guest_ids: Optional[List[str]] = request.data.get("guestIds") or None
    
    if guest_ids:
        guest_ids = [str(g).strip() for g in guest_ids if str(g).strip()]
        print(f"Sending to {len(guest_ids)} specific guests")
    else:
        print("Sending to ALL guests")

    # SKIP FIRESTORE - Use pure mock data
    print("\n⚠️  BYPASSING FIRESTORE - USING MOCK DATA")
    
    event = {
        "id": event_id,
        "name": "Test Event - Email Functionality Test",
        "startsAt": "2025-01-15T18:00:00Z",
        "venueName": "Brisbane Convention Centre",
        "venueAddress": "Cnr Merivale & Glenelg Streets, South Brisbane",
        "orgName": "SiPanit Team",
        "orgReplyEmail": "no-reply@sipanit.dev"
    }
    print(f"✅ Using mock event: {event['name']}")
    
    # Create mock guests
    print("\n👥 Creating mock guests...")
    mock_guests = []
    if guest_ids:
        for idx, gid in enumerate(guest_ids, 1):
            mock_guests.append({
                "id": gid,
                "name": f"Test Guest #{idx}",
                "email": "danindraahmad@gmail.com"  # ⚠️ Your real email
            })
    else:
        # If no specific IDs, create some mock guests
        for i in range(1, 4):
            mock_guests.append({
                "id": f"mock-guest-{i}",
                "name": f"Mock Guest {i}",
                "email": "danindraahmad@gmail.com"
            })
    
    targets = [(str(g["id"]), g) for g in mock_guests]
    print(f"✅ Created {len(targets)} mock guests")
    
    # Prepare event details
    print("\n📝 Preparing event details...")
    event_name = event["name"]
    starts_at = event["startsAt"]
    venue_name = event["venueName"]
    venue_addr = event["venueAddress"]
    org_name = event["orgName"]
    org_reply = event["orgReplyEmail"]
    
    event_date, event_time = _format_dt(starts_at)
    print(f"✅ Event: {event_name}")
    print(f"   Date: {event_date} at {event_time}")
    print(f"   Venue: {venue_name}")
    
    # Send emails
    print(f"\n📧 Sending emails to {len(targets)} guests...")
    sent, skipped = [], []
    
    for idx, (gid, guest) in enumerate(targets, 1):
        print(f"\n--- Guest {idx}/{len(targets)}: {gid} ---")
        
        try:
            guest_name = guest["name"]
            guest_email = guest["email"]
            
            print(f"  Name: {guest_name}")
            print(f"  Email: {guest_email}")
            
            if not guest_email:
                print("  ❌ No email address")
                skipped.append({"guestId": gid, "reason": "missing_email"})
                continue

            print("  📧 Calling send_guest_qr_email()...")
            
            try:
                send_guest_qr_email(
                    event_id=str(event_id),
                    guest_id=str(gid),                   
                    guest_email=guest_email,
                    guest_name=guest_name,
                    base_url=base_url,
                    event_name=event_name,
                    event_date=event_date,
                    event_time=event_time,
                    venue_name=venue_name,
                    venue_address=venue_addr,
                    org_name=org_name,
                    org_reply_email=org_reply,
                )
                sent.append(gid)
                print("  ✅ Email sent successfully!")
            except Exception as email_err:
                print(f"  ❌ Email send failed: {email_err}")
                import traceback
                traceback.print_exc()
                skipped.append({"guestId": gid, "reason": f"email_error: {str(email_err)}"})
                
        except Exception as e:
            print(f"  ❌ Processing error: {e}")
            import traceback
            traceback.print_exc()
            skipped.append({"guestId": gid, "reason": f"error: {str(e)}"})

    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    print(f"✅ Successfully sent: {len(sent)}")
    print(f"❌ Skipped: {len(skipped)}")
    if sent:
        print(f"\nEmails sent to guest IDs: {', '.join(sent)}")
    if skipped:
        print(f"\nSkipped:")
        for skip in skipped:
            print(f"  - {skip['guestId']}: {skip['reason']}")
    print("="*60 + "\n")
    
    return Response({
        "ok": True,
        "eventId": str(event_id),
        "requested": len(guest_ids) if guest_ids else "all",
        "sent": sent,
        "skipped": skipped,
        "counts": {"sent": len(sent), "skipped": len(skipped)},
    })
    print("\n" + "="*60)
    print("🔍 BULK SEND INVITES START")
    print("="*60)
    print(f"Event ID: {event_id}")
    print(f"User: {request.user}")
    print(f"User role: {getattr(request.user, 'role', 'N/A')}")
    print(f"Request data: {request.data}")
    
    base_url = request.data.get("baseUrl") or "https://app.example.com"
    guest_ids: Optional[List[str]] = request.data.get("guestIds") or None
    
    if guest_ids:
        guest_ids = [str(g).strip() for g in guest_ids if str(g).strip()]
        print(f"Sending to {len(guest_ids)} specific guests")
    else:
        print("Sending to ALL guests")

    try:
        event = get_event(event_id)
        if not event:
            print("❌ Event not found")
            return Response({"detail": "Event not found"}, status=404)
        
        print(f"✅ Event found: {event.get('name')}")
        
        # Get all guests
        items, _ = list_guests(event_id=event_id, limit=5000)
        targets = [(str(g.get("id")), g) for g in items]
        print(f"Total guests found: {len(targets)}")
        
        event_name = event.get("name") or event.get("title") or "Your Event"
        starts_at = event.get("startsAt")
        venue_name = event.get("venueName", "")
        venue_addr = event.get("venueAddress", "")
        org_name = event.get("orgName", "Event Team")
        org_reply = event.get("orgReplyEmail", "no-reply@example.com")
        
        event_date, event_time = _format_dt(starts_at)
        
        sent, skipped = [], []
        
        for idx, (gid, guest) in enumerate(targets, 1):
            print(f"\n--- Guest {idx}/{len(targets)}: {gid} ---")
            
            try:
                if not guest:
                    print("  ❌ Guest data is None")
                    skipped.append({"guestId": gid, "reason": "not_found"})
                    continue

                email = resolve_guest_email_from_event(event, gid) or (guest.get("email") or "").strip().lower()
                print(f"  Name: {guest.get('name', 'N/A')}")
                print(f"  Email: {email or 'MISSING'}")
                
                if not email:
                    print("  ❌ No email address")
                    skipped.append({"guestId": gid, "reason": "missing_email"})
                    continue

                print("  📧 Sending email...")
                
                send_guest_qr_email(
                    event_id=str(event_id),
                    guest_id=str(gid),                   
                    guest_email=email,
                    guest_name=guest.get("name", ""),
                    base_url=base_url,
                    event_name=event_name,
                    event_date=event_date,
                    event_time=event_time,
                    venue_name=venue_name,
                    venue_address=venue_addr,
                    org_name=org_name,
                    org_reply_email=org_reply,
                )
                sent.append(gid)
                print("  ✅ Email sent!")
                
            except Exception as email_error:
                print(f"  ❌ Email error: {email_error}")
                import traceback
                traceback.print_exc()
                skipped.append({"guestId": gid, "reason": f"email_error: {str(email_error)}"})

        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        print(f"✅ Sent: {len(sent)}")
        print(f"❌ Skipped: {len(skipped)}")
        print("="*60 + "\n")
        
        return Response({
            "ok": True,
            "eventId": str(event_id),
            "requested": len(guest_ids) if guest_ids else "all",
            "sent": sent,
            "skipped": skipped,
            "counts": {"sent": len(sent), "skipped": len(skipped)},
        })
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"detail": f"Server error: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class GuestFirebaseViewSet(viewsets.ViewSet):
    """
    /api/guests (GET, POST)
    /api/guests/{id} (PATCH, DELETE)
    /api/guests/toggle-checkin (POST)
    /api/guests/import-csv (POST multipart)
    """

    permission_classes = [IsAuthenticated, IsPlanner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request, event_id=None):
        q        = request.query_params.get("q")
        tags_any = request.query_params.getlist("tags") or None
        limit    = int(request.query_params.get("limit", 50))
        page_tok = request.query_params.get("pageToken")

        items, next_token = list_guests(event_id, q=q, tags_any=tags_any, limit=limit, page_token=page_tok)
        return Response({"items": items, "nextPageToken": next_token})

    def create(self, request, event_id=None):
        data = {**request.data, "eventId": event_id}   
        data.pop("seat", None)                          
        ser = GuestSerializer(data=data)
        ser.is_valid(raise_exception=True)
        gid = upsert_guest(event_id, ser.validated_data)
        return Response({"id": gid}, status=201)

    def partial_update(self, request, pk=None, event_id=None):
        """PATCH /api/guest/{event_id}/{guest_id}/ - Partial update (only provided fields)"""
        data = {**request.data, "id": pk, "eventId": event_id}
        ser = GuestSerializer(data=data, partial=True)
        ser.is_valid(raise_exception=True)
        # Use partial_update_guest to prevent data loss
        try:
            gid = partial_update_guest(event_id, pk, ser.validated_data, actor=request.user)
            return Response({"id": gid})
        except LookupError as e:
            return Response({"detail": str(e)}, status=404)

    def destroy(self, request, pk=None, event_id=None):
        delete_guest(event_id, pk)
        return Response(status=204)

    
    def import_csv(self, request, event_id=None, *args, **kwargs):

        if not event_id:
            return Response({"detail": "event_id missing in path"}, status=400)

        f = request.FILES.get("file") or request.data.get("file")
        if not f:
            return Response({"detail": "file is required"}, status=400)

        try:
            raw = f.read()
            text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
            reader = csv.DictReader(io.StringIO(text))
        except Exception as e:
            return Response({"detail": f"invalid CSV: {e}"}, status=400)

        imported, skipped = 0, []
        for idx, row in enumerate(reader, start=2):
            name  = (row.get("name")  or "").strip()
            email = (row.get("email") or "").strip().lower()
            if not name or not email:
                skipped.append({"line": idx, "reason": "missing name or email"})
                continue
            payload = {
                "eventId": event_id,
                "name": name,
                "email": email,
                "phone": (row.get("phone") or "").strip(),
                "dietaryRestriction": (row.get("dietary_restriction") or "").strip(),
                "accessibilityNeeds": (row.get("accessibility_needs") or "").strip(),
            }
            upsert_guest(event_id, payload)
            imported += 1

        return Response({"imported": imported, "skipped": skipped}, status=201)
    

    def qr(self, request, event_id=None, pk=None):
    # list_guests returns (items, next_page_token) or just items
        res = list_guests(event_id=event_id, limit=5000)

        guests = res[0] if isinstance(res, tuple) else res
        if not isinstance(guests, list):
            return Response({"detail": "Unexpected repository shape"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Find the guest by id
        target = None
        for x in guests:
            gid = str(x.get("id") or x.get("uid") or x.get("guest_id") or "")
            if gid == str(pk):
                target = x
                break

        if not target:
            return Response({"detail": "Guest not found."}, status=status.HTTP_404_NOT_FOUND)

        token = encrypt_payload({"e": str(event_id), "g": str(pk)})
    
        png = qr_png_bytes(token)
        filename = f"guest-{slugify(target.get('name') or pk)}.png"
        resp = HttpResponse(png, content_type="image/png")
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        return resp
    