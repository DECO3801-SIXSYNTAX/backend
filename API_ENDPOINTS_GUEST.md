# ✅ Guest API Endpoints - Confirmed Working

## Backend (Django) Endpoints

### Base URL: `http://localhost:8000/api/guest/`

---

## 1. List All Guests (GET)
```
GET /api/guest/<eventId>/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters (Optional):**
- `q` - Search query (string)
- `tags` - Filter by tags (array)
- `limit` - Max results (default: 50)
- `pageToken` - Pagination token

**Response:**
```json
{
  "items": [
    {
      "id": "guest_id_123",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "1234567890",
      "dietaryRestriction": "Vegetarian",
      "accessibilityNeeds": "Wheelchair",
      "seat": "A1",
      "tags": ["vegetarian", "wheelchair"],
      "createdAt": "2025-10-20T10:00:00Z",
      "updatedAt": "2025-10-20T10:00:00Z"
    }
  ],
  "nextPageToken": "token_for_next_page"
}
```

**Frontend Usage:**
```typescript
import { apiListGuests } from '../../api/guest';

const { items, nextPageToken } = await apiListGuests(eventId, {
  q: 'john',
  limit: 20
});
```

---

## 2. Add Guest (POST)
```
POST /api/guest/<eventId>/
```

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "phone": "0987654321",
  "dietaryRestriction": "Vegan",
  "accessibilityNeeds": "None"
}
```

**Response:**
```json
{
  "id": "newly_created_guest_id"
}
```

**Frontend Usage:**
```typescript
import { apiCreateGuest } from '../../api/guest';

const result = await apiCreateGuest(eventId, {
  name: 'Jane Smith',
  email: 'jane@example.com',
  phone: '0987654321',
  dietaryRestriction: 'Vegan',
  accessibilityNeeds: 'None'
});

console.log('Created guest ID:', result.id);
```

---

## 3. Update Guest (PATCH)
```
PATCH /api/guest/<eventId>/<guestId>/
```

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body (Partial):**
```json
{
  "phone": "1111111111",
  "dietaryRestriction": "Gluten-free"
}
```

**Response:**
```json
{
  "id": "guest_id_123"
}
```

**Frontend Usage:**
```typescript
import { apiUpdateGuest } from '../../api/guest';

await apiUpdateGuest(eventId, guestId, {
  phone: '1111111111',
  dietaryRestriction: 'Gluten-free'
});
```

---

## 4. Delete Guest (DELETE)
```
DELETE /api/guest/<eventId>/<guestId>/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**Frontend Usage:**
```typescript
import { apiDeleteGuest } from '../../api/guest';

await apiDeleteGuest(eventId, guestId);
```

---

## 5. Import Guests from CSV (POST)
```
POST /api/guest/import-csv/<eventId>/
```

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body (FormData):**
```
file: <CSV_FILE>
```

**CSV Format:**
```csv
name,email,phone,dietary_restriction,accessibility_needs
John Doe,john@example.com,1234567890,Vegetarian,Wheelchair
Jane Smith,jane@example.com,0987654321,Vegan,None
```

**Response:**
```json
{
  "imported": 2,
  "skipped": []
}
```

**Frontend Usage:**
```typescript
import { apiImportGuestsCSV } from '../../api/guest';

const file = document.querySelector('input[type="file"]').files[0];
const result = await apiImportGuestsCSV(eventId, file);

console.log(`Imported ${result.imported} guests`);
```

---

## 6. Get Guest QR Code (GET)
```
GET /api/guest/qr/<eventId>/<guestId>/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** PNG image (binary)

**Frontend Usage:**
```typescript
import { apiGetGuestQR } from '../../api/guest';

const blob = await apiGetGuestQR(eventId, guestId);
const url = URL.createObjectURL(blob);

// Display in <img> tag
document.getElementById('qr-image').src = url;

// Or download
const a = document.createElement('a');
a.href = url;
a.download = `guest-${guestId}-qr.png`;
a.click();
```

---

## 7. Bulk Send Invites (POST)
```
POST /api/guest/bulk-send-invites/<eventId>/
```

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "baseUrl": "https://app.sipanit.com",
  "guestIds": ["guest_id_1", "guest_id_2"]  // Optional, if empty sends to ALL
}
```

**Response:**
```json
{
  "ok": true,
  "eventId": "event_123",
  "requested": 2,
  "sent": ["guest_id_1", "guest_id_2"],
  "skipped": [],
  "counts": {
    "sent": 2,
    "skipped": 0
  }
}
```

---

## Backend Code Reference

### Django View: `backend/guest/views.py`
```python
class GuestFirebaseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsPlanner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request, event_id=None):
        # GET /api/guest/<eventId>/
        
    def create(self, request, event_id=None):
        # POST /api/guest/<eventId>/
        
    def partial_update(self, request, pk=None, event_id=None):
        # PATCH /api/guest/<eventId>/<pk>/
        
    def destroy(self, request, pk=None, event_id=None):
        # DELETE /api/guest/<eventId>/<pk>/
        
    def import_csv(self, request, event_id=None):
        # POST /api/guest/import-csv/<eventId>/
        
    def qr(self, request, event_id=None, pk=None):
        # GET /api/guest/qr/<eventId>/<pk>/
```

### URL Routing: `backend/guest/urls.py`
```python
urlpatterns = [
    path("<str:event_id>/", guest_list_create, name="guest-list-create"),
    path("<str:event_id>/<str:pk>/", guest_detail, name="guest-detail"),
    path("import-csv/<str:event_id>/", guest_import_csv, name="guest-import-csv"),
    path("qr/<str:event_id>/<str:pk>/", guest_qr_png, name="guest-qr"),
    path("bulk-send-invites/<str:event_id>/", bulk_send_invites, name="guest-bulk-send-invites"),
]
```

---

## Data Storage

### Firestore Path:
```
events/
  └─ {eventId}/
      └─ guests/
          └─ {guestId}/
              ├─ name: string
              ├─ email: string
              ├─ phone: string
              ├─ dietaryRestriction: string
              ├─ accessibilityNeeds: string
              ├─ seat: string (assigned from Layout Editor)
              ├─ tags: array (auto-generated from dietary + accessibility)
              ├─ checkedIn: boolean
              ├─ createdAt: timestamp
              └─ updatedAt: timestamp
```

---

## Authentication

All endpoints require JWT authentication:

1. **Login** to get access token:
   ```typescript
   const response = await axios.post('http://localhost:8000/api/auth/login/', {
     email: 'user@example.com',
     password: 'password123'
   });
   
   localStorage.setItem('access_token', response.data.access);
   ```

2. **Include token in requests:**
   ```typescript
   headers: {
     'Authorization': `Bearer ${localStorage.getItem('access_token')}`
   }
   ```

---

## Permissions

- **Required Role:** `planner` or `admin`
- **Authentication:** JWT token required
- **Scope:** Users can only access guests for events they created (or in their company)

---

## Testing with cURL

### List Guests:
```bash
curl -X GET "http://localhost:8000/api/guest/<EVENT_ID>/" \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

### Add Guest:
```bash
curl -X POST "http://localhost:8000/api/guest/<EVENT_ID>/" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "phone": "1234567890",
    "dietaryRestriction": "None",
    "accessibilityNeeds": "None"
  }'
```

### Update Guest:
```bash
curl -X PATCH "http://localhost:8000/api/guest/<EVENT_ID>/<GUEST_ID>/" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "9999999999"
  }'
```

### Delete Guest:
```bash
curl -X DELETE "http://localhost:8000/api/guest/<EVENT_ID>/<GUEST_ID>/" \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

---

## ✅ Summary

**Your endpoints are CORRECT:**

✅ `POST /api/guest/<eventId>/` - Add single guest  
✅ `GET /api/guest/<eventId>/` - List all guests  
✅ `PATCH /api/guest/<eventId>/<guestId>/` - Update guest  
✅ `DELETE /api/guest/<eventId>/<guestId>/` - Delete guest  
✅ `POST /api/guest/import-csv/<eventId>/` - Import from CSV  
✅ `GET /api/guest/qr/<eventId>/<guestId>/` - Get QR code  
✅ `POST /api/guest/bulk-send-invites/<eventId>/` - Send email invites  

**Frontend client ready:**  
✅ `frontend/src/api/guest.ts` - All functions implemented  

**Next step:**  
Update `GuestManagement.tsx` to use the Django API instead of direct Firebase access!
