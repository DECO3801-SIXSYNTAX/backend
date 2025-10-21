# Correct Architecture: Django + Firebase Hybrid System

## ✅ Your Current Architecture (CORRECT)

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  (React + TypeScript + Vite)                                │
│                                                              │
│  - User Interface                                            │
│  - API Calls to Django Backend                               │
│  - JWT Token Storage (localStorage)                          │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ HTTP Requests + JWT Token
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                   DJANGO BACKEND                             │
│  (Django 5.2.7 + DRF + Firebase Admin SDK)                  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Authentication Layer                                   │ │
│  │  - JWT Token Validation                                 │ │
│  │  - User Permissions (IsPlanner, IsAdmin, etc.)         │ │
│  │  - Google OAuth Integration                             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  API Endpoints (REST)                                   │ │
│  │  - /api/auth/* - Authentication                         │ │
│  │  - /api/guest/* - Guest Management                      │ │
│  │  - /api/users/* - User Management                       │ │
│  │  - /api/events/* - Event Management                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Business Logic                                          │ │
│  │  - Serializers (Data Validation)                        │ │
│  │  - ViewSets (CRUD Operations)                           │ │
│  │  - Repositories (Firestore Access Layer)                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Firebase Admin SDK                                      │ │
│  │  - firestore.client() - Database Operations             │ │
│  │  - credentials.Certificate() - Service Account Auth     │ │
│  │  - firebase_admin.initialize_app()                      │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ Firebase Admin SDK
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                  FIREBASE FIRESTORE                          │
│  (Cloud NoSQL Database)                                      │
│                                                              │
│  Collections:                                                │
│  ├── users/{userId}/                                         │
│  ├── events/{eventId}/                                       │
│  │   └── guests/{guestId}/                                   │
│  ├── floor_plans/{planId}/                                   │
│  └── activities/{activityId}/                                │
└──────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. **Authentication Flow** (Django JWT + Firebase Auth)

```
User SignUp/Login
    ↓
Django API (/api/auth/register/ or /api/auth/login/)
    ↓
Django validates credentials
    ↓
Returns JWT tokens (access + refresh)
    ↓
Frontend stores tokens in localStorage
    ↓
All API requests include: Authorization: Bearer <access_token>
```

**Optional Google OAuth**:
```
User clicks "Sign in with Google"
    ↓
Google returns id_token
    ↓
Frontend sends to Django (/api/auth/google/)
    ↓
Django verifies token with Google
    ↓
Django creates/gets user in Firestore (via Firebase Admin SDK)
    ↓
Returns JWT tokens
```

---

### 2. **Guest Management Flow** (Django API + Firebase Admin SDK)

#### Current (Incorrect - Frontend directly accessing Firestore):
```
❌ Frontend → Firebase Firestore (Direct Access)
```

#### Should Be (Django as middleware):
```
✅ Frontend → Django API → Firebase Admin SDK → Firestore
```

**Example: List Guests**
```
1. Frontend: GET /api/guest/{event_id}/
   Headers: Authorization: Bearer <jwt_token>

2. Django Views (guest/views.py):
   - Validates JWT token
   - Checks permissions (IsAuthenticated, IsPlanner)
   - Calls repository layer

3. Repository (guest/repository.py):
   - Uses Firebase Admin SDK
   - Queries Firestore:
     db.collection("events")
       .document(event_id)
       .collection("guests")
       .get()

4. Django Response:
   {
     "items": [
       {
         "id": "guest123",
         "name": "John Doe",
         "email": "john@example.com",
         "seat": "Table 3 - Seat 5",  // Assigned from Layout Editor
         ...
       }
     ]
   }
```

---

### 3. **Why This Architecture?**

#### Django Handles:
- ✅ **Authentication** - JWT tokens, Google OAuth
- ✅ **Authorization** - Permissions (planner, admin, vendor, guest)
- ✅ **Validation** - Serializers validate all input data
- ✅ **Business Logic** - Rules, constraints, workflows
- ✅ **API Rate Limiting** - Protect against abuse
- ✅ **Audit Logging** - Track who did what and when
- ✅ **Centralized Error Handling** - Consistent error responses

#### Firebase Admin SDK Handles:
- ✅ **Data Storage** - Firestore NoSQL database
- ✅ **Secure Access** - Service account credentials (server-side only)
- ✅ **Real-time Updates** - If using Firestore listeners
- ✅ **Scalability** - Google Cloud infrastructure

#### Why NOT direct Firebase access from frontend?
- ❌ **Security Risk** - Exposes Firebase credentials to browser
- ❌ **No Authentication Control** - Can't enforce Django JWT
- ❌ **No Validation** - Users can bypass Django serializers
- ❌ **Inconsistent Data** - Different validation rules
- ❌ **Audit Trail Missing** - Can't track who made changes

---

## Code Examples

### Backend: Guest Repository (guest/repository.py)

```python
from firebase_admin import firestore
from SiPanit.firebase import get_db

def upsert_guest(event_id: str, data: Dict[str, Any]) -> str:
    """Create or update a guest using Firebase Admin SDK"""
    db = get_db()  # Get Firestore client
    
    # Build Firestore path: events/{event_id}/guests/
    col = db.collection("events").document(event_id).collection("guests")
    
    guest_id = data.get("id") or col.document().id
    doc_ref = col.document(guest_id)
    
    # Normalize and validate data
    payload = _normalize_guest_payload(data)
    payload["updatedAt"] = firestore.SERVER_TIMESTAMP
    
    # Write to Firestore
    doc_ref.set(payload, merge=True)
    
    return guest_id
```

### Backend: Guest Views (guest/views.py)

```python
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsPlanner
from .repository import list_guests, upsert_guest, delete_guest

class GuestFirebaseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsPlanner]  # Django JWT + Permissions
    
    def list(self, request, event_id=None):
        """GET /api/guest/{event_id}/"""
        items, next_token = list_guests(event_id)  # Calls Firebase Admin SDK
        return Response({"items": items, "nextPageToken": next_token})
    
    def create(self, request, event_id=None):
        """POST /api/guest/{event_id}/"""
        data = {**request.data, "eventId": event_id}
        ser = GuestSerializer(data=data)  # Django validation
        ser.is_valid(raise_exception=True)
        gid = upsert_guest(event_id, ser.validated_data)  # Firebase Admin SDK
        return Response({"id": gid}, status=201)
```

### Frontend: API Client (api/guest.ts)

```typescript
import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Get JWT token from localStorage
const getAuthHeaders = () => ({
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  'Content-Type': 'application/json'
});

// List guests - Goes through Django API
export async function apiListGuests(eventId: string) {
  const response = await axios.get(
    `${API_URL}/api/guest/${eventId}/`,
    { headers: getAuthHeaders() }  // Django validates this JWT
  );
  return response.data;
}

// Create guest - Goes through Django API
export async function apiCreateGuest(eventId: string, guest: any) {
  const response = await axios.post(
    `${API_URL}/api/guest/${eventId}/`,
    guest,
    { headers: getAuthHeaders() }  // Django validates this JWT
  );
  return response.data;
}
```

---

## Current Issue in GuestManagement.tsx

### ❌ Current (Wrong):
```typescript
// GuestManagement.tsx
import { GuestService } from '../../services/GuestService';

// This bypasses Django and directly accesses Firebase
const guestService = new GuestService();
const guests = await guestService.getGuestsByEvent(eventId);
```

### ✅ Should Be:
```typescript
// GuestManagement.tsx
import { apiListGuests, apiCreateGuest } from '../../api/guest';

// This goes through Django API (which uses Firebase Admin SDK)
const { items: guests } = await apiListGuests(eventId);
```

---

## Benefits of Django + Firebase Hybrid

### Security:
- ✅ JWT tokens validated by Django
- ✅ Firebase credentials stored server-side only
- ✅ Role-based permissions enforced
- ✅ Service account credentials (not API keys)

### Data Consistency:
- ✅ All data validated by Django serializers
- ✅ Business rules enforced consistently
- ✅ Audit trails for all changes
- ✅ Single source of truth for validation

### Maintainability:
- ✅ Centralized business logic in Django
- ✅ Easy to add new features (Django views)
- ✅ Consistent error handling
- ✅ API versioning possible

### Performance:
- ✅ Firebase Admin SDK optimized for server-side
- ✅ Connection pooling
- ✅ Caching opportunities
- ✅ Batch operations

---

## Summary

**Your architecture is CORRECT: Django + Firebase working together**

### What works correctly:
- ✅ Authentication: Django JWT
- ✅ Users: Django User model + Firestore
- ✅ Events: Django API + Firestore (via Admin SDK)

### What needs fixing:
- ❌ Guest Management: Currently bypasses Django, accesses Firebase directly
- ❌ Should use: Django API (`/api/guest/`) → Firebase Admin SDK → Firestore

### The Fix:
1. Replace `GuestService` (direct Firebase) with `api/guest.ts` (Django API)
2. All frontend guest operations go through Django
3. Django uses Firebase Admin SDK to read/write Firestore
4. Security and validation enforced consistently

**This is the industry-standard pattern**: Backend controls all data access, frontend is just a UI layer.
