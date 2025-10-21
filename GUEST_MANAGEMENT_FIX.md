# ✅ Fixed: Guest Management Now Uses Django API

## Problem
When adding guests in Guest Management page, they were **NOT being stored** because:
- Frontend was using `GuestService` which accesses Firebase directly
- Old Firebase path: `users/{userId}/events/{eventId}/guests/` ❌
- New Django backend expects: `events/{eventId}/guests/` ✅
- **They were going to different locations!**

## Solution Applied

### Updated File: `frontend/src/pages/planner/GuestManagement.tsx`

#### Changes Made:

1. **Import Django API Client:**
   ```typescript
   // OLD
   import { GuestService, Guest } from '../../services/GuestService';
   
   // NEW
   import { Guest } from '../../services/GuestService'; // Keep type only
   import { apiListGuests, apiCreateGuest, apiUpdateGuest, apiDeleteGuest } from '../../api/guest';
   ```

2. **Load Guests - Use Django API:**
   ```typescript
   const loadGuests = async () => {
     // OLD: const guestsData = await guestService.getGuestsByEvent(selectedEventId);
     
     // NEW: Use Django API
     const response = await apiListGuests(selectedEventId);
     const guestsData = response.items.map(g => ({
       id: g.id || '',
       eventId: g.eventId,
       name: g.name,
       email: g.email,
       phone: g.phone || '',
       status: 'confirmed' as const,
       dietaryNeeds: g.dietaryRestriction || '',
       accessibility: g.accessibilityNeeds || '',
       plusOne: false,
       table: g.seat || ''
     }));
     setGuests(guestsData);
   };
   ```

3. **Add Guest - Use Django API:**
   ```typescript
   const handleAddGuest = async () => {
     // OLD: await guestService.addGuest(selectedEventId, {...});
     
     // NEW: Use Django API
     await apiCreateGuest(selectedEventId, {
       eventId: selectedEventId,
       name: newGuest.name,
       email: newGuest.email,
       phone: newGuest.phone,
       dietaryRestriction: newGuest.dietaryNeeds,
       accessibilityNeeds: newGuest.accessibility
     });
   };
   ```

4. **Update Guest - Use Django API:**
   ```typescript
   const handleUpdateGuest = async () => {
     // OLD: await guestService.updateGuest(selectedEventId, editingGuest.id, editingGuest);
     
     // NEW: Use Django API
     await apiUpdateGuest(selectedEventId, editingGuest.id, {
       eventId: selectedEventId,
       name: editingGuest.name,
       email: editingGuest.email,
       phone: editingGuest.phone,
       dietaryRestriction: editingGuest.dietaryNeeds,
       accessibilityNeeds: editingGuest.accessibility
     });
   };
   ```

5. **Delete Guest - Use Django API:**
   ```typescript
   const handleDeleteGuest = async (guestId: string) => {
     // OLD: await guestService.deleteGuest(selectedEventId, guestId);
     
     // NEW: Use Django API
     await apiDeleteGuest(selectedEventId, guestId);
   };
   ```

## How It Works Now

### Data Flow:
```
Frontend (GuestManagement.tsx)
    ↓
Django API (/api/guest/<eventId>/)
    ↓
Django Backend (guest/views.py)
    ↓
Firebase Admin SDK
    ↓
Firestore (events/{eventId}/guests/)
```

### Storage Location:
```
Firestore:
  events/
    └─ {eventId}/
        └─ guests/
            └─ {guestId}/
                ├─ name
                ├─ email
                ├─ phone
                ├─ dietaryRestriction
                ├─ accessibilityNeeds
                ├─ seat (assigned from Layout Editor)
                ├─ tags (auto-generated)
                ├─ createdAt
                └─ updatedAt
```

## Testing

### 1. Start Both Servers:
```bash
# Backend (Terminal 1)
cd backend
python3.10 manage.py runserver

# Frontend (Terminal 2)
cd frontend
npm run dev
```

### 2. Test Guest Operations:

1. **Login** to your app: http://localhost:3000
2. **Navigate to Guest Management** page
3. **Select an event** from dropdown
4. **Add a guest**:
   - Click "+ Add Guest"
   - Fill in name, email, phone
   - Add dietary needs (optional)
   - Add accessibility needs (optional)
   - Click "Add Guest"

5. **Verify in Firebase Console**:
   - Open: https://console.firebase.google.com/project/deco-ad56f/firestore
   - Navigate to: `events → {your_event_id} → guests`
   - You should see your guest data there! ✅

6. **Test Edit**:
   - Click edit icon on guest
   - Update information
   - Save
   - Guest should update in Firebase

7. **Test Delete**:
   - Click delete icon
   - Confirm deletion
   - Guest removed from Firebase

## API Endpoints Used

### List Guests:
```
GET http://localhost:8000/api/guest/<eventId>/
Headers: Authorization: Bearer <access_token>
```

### Create Guest:
```
POST http://localhost:8000/api/guest/<eventId>/
Headers: 
  Authorization: Bearer <access_token>
  Content-Type: application/json
Body: {
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "1234567890",
  "dietaryRestriction": "Vegetarian",
  "accessibilityNeeds": "Wheelchair"
}
```

### Update Guest:
```
PATCH http://localhost:8000/api/guest/<eventId>/<guestId>/
Headers: 
  Authorization: Bearer <access_token>
  Content-Type: application/json
Body: {
  "phone": "9999999999"
}
```

### Delete Guest:
```
DELETE http://localhost:8000/api/guest/<eventId>/<guestId>/
Headers: Authorization: Bearer <access_token>
```

## What Changed

### Before ❌:
- Guest Management → Firebase directly (old path)
- Guests stored in: `users/{userId}/events/{eventId}/guests/`
- Backend couldn't see the guests
- No JWT authentication
- No Django permission checks

### After ✅:
- Guest Management → Django API → Firebase Admin SDK
- Guests stored in: `events/{eventId}/guests/`
- Backend can access guests
- JWT authentication required
- Django permission checks (IsAuthenticated, IsPlanner)
- Proper API architecture

## Field Mapping

### Frontend Form → Django API:
```typescript
{
  name: "John Doe",              // → name
  email: "john@example.com",     // → email
  phone: "1234567890",           // → phone
  dietaryNeeds: "Vegetarian",    // → dietaryRestriction
  accessibility: "Wheelchair",   // → accessibilityNeeds
  
  // NOT sent to Django (frontend-only):
  status: "pending",    // Django doesn't track RSVP status yet
  plusOne: false,       // Not in Django model
  plusOneName: "",      // Not in Django model
  table: ""            // Read-only, assigned from Layout Editor
}
```

## Known Limitations

1. **RSVP Status**: Not tracked in Django backend yet
   - Frontend shows status but doesn't save it
   - `handleUpdateStatus()` is disabled
   - To enable: Add `status` field to Django guest model

2. **Plus One**: Not supported in Django backend
   - Form fields exist but data not saved
   - To enable: Add `plusOne` and `plusOneName` to Django model

3. **Table Assignment**: Read-only
   - Assigned from Layout Editor, not Guest Management
   - Manual table input removed (or should be)

## Troubleshooting

### "Failed to add guest"
- Check if backend is running: http://localhost:8000/api/health/
- Check browser console for error details
- Verify JWT token exists: `localStorage.getItem('access_token')`
- Check if user is authenticated and has `planner` role

### "No guests showing up"
- Check if event is selected in dropdown
- Check browser console for API errors
- Verify Firebase path: `events/{eventId}/guests/`
- Try running data migration if you have old guests

### "401 Unauthorized"
- JWT token expired - re-login
- User doesn't have permission - check role is `planner` or `admin`

### "Network Error"
- Backend not running - start with `python3.10 manage.py runserver`
- Wrong API URL - check `VITE_API_BASE_URL` in `.env`

## Next Steps

1. ✅ **DONE**: Guest Management uses Django API
2. ⏳ **TODO**: Update ViewLayout.tsx to use Django API
3. ⏳ **TODO**: Update DashboardService.getGuests() to use Django API
4. ⏳ **TODO**: Add RSVP status tracking to Django backend
5. ⏳ **TODO**: Remove direct Firebase access from all frontend code

## Files Modified

- ✅ `frontend/src/pages/planner/GuestManagement.tsx` - Now uses Django API
- ✅ `frontend/src/api/guest.ts` - Django API client (already existed)
- 📁 `backend/guest/views.py` - Django API endpoints (unchanged)
- 📁 `backend/guest/repository.py` - Firebase Admin SDK (unchanged)

## Success Indicators

✅ Guests appear in Firebase Console under `events/{eventId}/guests/`  
✅ Add guest works and shows immediately  
✅ Edit guest updates in Firebase  
✅ Delete guest removes from Firebase  
✅ No errors in browser console  
✅ Django backend logs show API requests  

Your guests should now be stored correctly in Firebase! 🎉
