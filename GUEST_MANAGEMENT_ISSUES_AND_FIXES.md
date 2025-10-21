# Guest Management Issues & Fixes

## Issues Identified

### 1. **Missing Backend Integration** ❌
**Problem**: Frontend GuestManagement uses Firebase (`GuestService.ts`), but backend has Django REST API (`/api/guest/`)

**Current Flow**:
```
Frontend (GuestManagement.tsx)
    ↓
GuestService.ts (Firebase Firestore)
    ↓
Firebase Database
```

**Should Be**:
```
Frontend (GuestManagement.tsx)
    ↓
Django Guest API (/api/guest/{event_id}/)
    ↓
Firebase Admin SDK (backend)
    ↓
Firebase Database
```

**Backend API Endpoints Available**:
- `GET /api/guest/{event_id}/` - List guests for event
- `POST /api/guest/{event_id}/` - Create guest
- `PATCH /api/guest/{event_id}/{guest_id}/` - Update guest
- `DELETE /api/guest/{event_id}/{guest_id}/` - Delete guest
- `POST /api/guest/import-csv/{event_id}/` - Bulk import
- `GET /api/guest/qr/{event_id}/{guest_id}/` - Get QR code

**Backend Guest Model** (from serializer):
```python
{
    "id": "string",
    "eventId": "string",
    "name": "string",
    "email": "string",
    "phone": "string (optional)",
    "dietaryRestriction": "string (optional)",
    "accessibilityNeeds": "string (optional)",
    "seat": "string (optional, read-only)",
    "tags": ["string"] (read-only)
}
```

---

###  2. **Manual Table Assignment in Guest Management** ❌
**Problem**: Guest Management allows manual table/seat assignment, but should only show assignments made in Layout Editor

**Current State**:
- GuestManagement has "Table" column (line 392-393)
- Shows manual input for table assignment (lines 640-650, 814-825)
- Users can type in table numbers manually

**Should Be**:
- Remove "Table" column from Guest Management table
- Remove table input from Add/Edit guest modals  
- Show "Assigned Seat" as **read-only** (from Layout Editor only)
- Seat assignment happens ONLY in Layout Editor via drag-and-drop

**Current Frontend Guest Interface** (`GuestService.ts`):
```typescript
interface Guest {
  id: string;
  eventId: string;
  name: string;
  email: string;
  phone: string;
  status: 'confirmed' | 'pending' | 'declined';
  rsvpDate?: string;
  dietaryNeeds?: string;
  accessibility?: string;
  plusOne: boolean;
  plusOneName?: string;
  table?: string;  // ❌ Should be removed from manual input
  createdAt?: Timestamp;
  updatedAt?: Timestamp;
}
```

---

## Required Changes

### Change 1: Create Django Guest API Client

**File**: `frontend/src/api/guest.ts` (NEW)

```typescript
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface DjangoGuest {
  id?: string;
  eventId: string;
  name: string;
  email: string;
  phone?: string;
  dietaryRestriction?: string;
  accessibilityNeeds?: string;
  seat?: string;  // Read-only, assigned from Layout Editor
  tags?: string[];  // Read-only
}

// Get token from localStorage
const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
};

// List guests for an event
export async function apiListGuests(eventId: string, params?: {
  q?: string;
  tags?: string[];
  limit?: number;
  pageToken?: string;
}): Promise<{ items: DjangoGuest[]; nextPageToken?: string }> {
  const response = await axios.get(`${API_URL}/api/guest/${eventId}/`, {
    headers: getAuthHeaders(),
    params
  });
  return response.data;
}

// Create a guest
export async function apiCreateGuest(eventId: string, guest: Omit<DjangoGuest, 'id' | 'seat' | 'tags'>): Promise<{ id: string }> {
  const response = await axios.post(`${API_URL}/api/guest/${eventId}/`, guest, {
    headers: getAuthHeaders()
  });
  return response.data;
}

// Update a guest
export async function apiUpdateGuest(eventId: string, guestId: string, updates: Partial<DjangoGuest>): Promise<{ id: string }> {
  const response = await axios.patch(`${API_URL}/api/guest/${eventId}/${guestId}/`, updates, {
    headers: getAuthHeaders()
  });
  return response.data;
}

// Delete a guest
export async function apiDeleteGuest(eventId: string, guestId: string): Promise<void> {
  await axios.delete(`${API_URL}/api/guest/${eventId}/${guestId}/`, {
    headers: getAuthHeaders()
  });
}

// Import guests from CSV
export async function apiImportGuestsCSV(eventId: string, file: File): Promise<{ imported: number; skipped: any[] }> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await axios.post(`${API_URL}/api/guest/import-csv/${eventId}/`, formData, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      // Don't set Content-Type, let browser set it with boundary
    }
  });
  return response.data;
}

// Get guest QR code
export async function apiGetGuestQR(eventId: string, guestId: string): Promise<Blob> {
  const response = await axios.get(`${API_URL}/api/guest/qr/${eventId}/${guestId}/`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    },
    responseType: 'blob'
  });
  return response.data;
}
```

---

### Change 2: Update GuestManagement to use Django API

**File**: `frontend/src/pages/planner/GuestManagement.tsx`

**Changes**:
1. Replace `GuestService` with Django API client
2. Remove "Table" column from table
3. Remove table input from Add/Edit modals
4. Show assigned seat as read-only (if exists)

**Key Changes**:
```typescript
// OLD
import { GuestService, Guest } from '../../services/GuestService';
const guestService = new GuestService();
const guestsData = await guestService.getGuestsByEvent(selectedEventId);

// NEW
import { apiListGuests, apiCreateGuest, apiUpdateGuest, apiDeleteGuest, DjangoGuest } from '../../api/guest';
const { items: guestsData } = await apiListGuests(selectedEventId);
```

**Remove These Sections**:
1. Line 392-394: Remove "Table" `<th>` column header
2. Line 458-466: Remove "Table" `<td>` cell
3. Lines 640-650: Remove "Table Assignment" section from Add Modal
4. Lines 814-825: Remove "Table Assignment" section from Edit Modal

**Optional: Add Read-Only Seat Display**:
```tsx
{/* In guest table, replace table column with read-only seat */}
<td className="px-6 py-4 whitespace-nowrap">
  {guest.seat ? (
    <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">
      {guest.seat}
    </span>
  ) : (
    <span className="text-gray-400 text-sm">Not assigned</span>
  )}
</td>
```

---

### Change 3: Remove `table` from Guest Interface

**File**: `frontend/src/services/GuestService.ts`

**Change**:
```typescript
// OLD
export interface Guest {
  // ...
  table?: string;  // ❌ Remove this
  // ...
}

// NEW - No table field, seat is read-only from backend
export interface Guest {
  id: string;
  eventId: string;
  name: string;
  email: string;
  phone: string;
  status: 'confirmed' | 'pending' | 'declined';
  rsvpDate?: string;
  dietaryNeeds?: string;
  accessibility?: string;
  plusOne: boolean;
  plusOneName?: string;
  seat?: string;  // Read-only, assigned from Layout Editor
  createdAt?: Timestamp;
  updatedAt?: Timestamp;
}
```

**Remove table-related methods**:
```typescript
// ❌ Remove this method - seat assignment happens in Layout Editor
async assignTable(eventId: string, guestId: string, table: string): Promise<void> {
  // DELETE THIS METHOD
}
```

---

### Change 4: Update newGuest State

**File**: `frontend/src/pages/planner/GuestManagement.tsx`

**Change**:
```typescript
// OLD
const [newGuest, setNewGuest] = useState({
  name: '',
  email: '',
  phone: '',
  status: 'pending' as 'pending' | 'confirmed' | 'declined',
  dietaryNeeds: '',
  accessibility: '',
  plusOne: false,
  plusOneName: '',
  table: ''  // ❌ Remove this
});

// NEW
const [newGuest, setNewGuest] = useState({
  name: '',
  email: '',
  phone: '',
  status: 'pending' as 'pending' | 'confirmed' | 'declined',
  dietaryNeeds: '',
  accessibility: '',
  plusOne: false,
  plusOneName: ''
  // No table field
});
```

---

## How Seat Assignment Should Work

### Correct Flow:

1. **Guest Management** (for managing guest info):
   - Add/Edit guest details (name, email, phone, dietary, accessibility)
   - View guest list with read-only seat assignments
   - Cannot manually assign seats

2. **Layout Editor** (for seat assignments):
   - Drag guests onto seats in floor plan
   - Layout Editor calls backend to update guest's `seat` field
   - Seat assignment is stored in Firebase via backend

3. **Backend API** handles the update:
   ```python
   # When Layout Editor assigns a seat:
   PATCH /api/guest/{event_id}/{guest_id}/
   {
     "seat": "Table 3 - Seat 5"
   }
   ```

4. **Guest Management displays** the assigned seat (read-only):
   ```tsx
   <td>
     {guest.seat || "Not assigned"}
   </td>
   ```

---

## Testing Checklist

After implementing these changes:

- [ ] Guest Management loads guests from Django API
- [ ] Can add new guest via Django API
- [ ] Can edit guest (name, email, phone, dietary, accessibility)
- [ ] Can delete guest
- [ ] **Cannot** manually assign table/seat in Guest Management
- [ ] "Table" column is removed from guest table
- [ ] "Table Assignment" input is removed from Add/Edit modals
- [ ] Assigned seat (from Layout Editor) displays as read-only
- [ ] Layout Editor can still assign seats to guests
- [ ] Seat assignments persist in Firebase

---

## Summary

**Current Issues**:
1. ❌ Guest Management uses Firebase directly (should use Django API)
2. ❌ Manual table assignment in Guest Management (should be read-only)
3. ❌ Table input fields in Add/Edit modals (should not exist)

**Required Changes**:
1. ✅ Create Django Guest API client (`api/guest.ts`)
2. ✅ Update GuestManagement to use Django API
3. ✅ Remove "Table" column and inputs
4. ✅ Show assigned seat as read-only
5. ✅ Remove `table` field from Guest interface
6. ✅ Seat assignment happens ONLY in Layout Editor

**Benefits**:
- Centralized authentication via Django JWT
- Consistent API usage (not mixing Firebase & Django)
- Clear separation: Guest Management = info, Layout Editor = seating
- Read-only seat display prevents manual conflicts
- Backend controls all Firebase operations

---

## Priority

**HIGH PRIORITY** - This affects core functionality:
1. Guest management currently bypasses Django authentication
2. Manual seat assignment conflicts with Layout Editor
3. Inconsistent data flow (Firebase direct vs Django API)

**Recommended Order**:
1. First: Create `api/guest.ts` with Django API client
2. Second: Update GuestManagement to use Django API
3. Third: Remove table column and inputs
4. Fourth: Test full flow (add guest → assign seat in Layout Editor → view in Guest Management)
