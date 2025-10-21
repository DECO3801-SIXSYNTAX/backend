# 🔄 Guest Data Migration Guide

## Problem

After pulling the `dev` branch, you can't see your events because the guest data storage structure changed:

### Old Structure (Frontend Direct Firebase Access):
```
users/
  └─ {userId}/
      └─ events/
          └─ {eventId}/
              └─ guests/
                  └─ {guestId}
```

### New Structure (Django API + Firebase Admin SDK):
```
events/
  └─ {eventId}/
      └─ guests/
          └─ {guestId}
```

## Solution Options

### Option 1: Migrate Data (RECOMMENDED) ✅

**Steps:**

1. **Get your User ID**:
   - Open: `file:///Users/auli/Documents/UQ/deco3801/SiPanit:Admin/get_user_id.html`
   - Copy your User ID (e.g., `vZ5e5BzQSoTd7...`)

2. **Run Migration**:
   - Open: `file:///Users/auli/Documents/UQ/deco3801/SiPanit:Admin/migrate_guests.html`
   - Click "Start Migration"
   - Enter your User ID when prompted
   - Wait for completion

3. **Verify**:
   - Refresh your app: http://localhost:3000
   - Login if needed
   - Check if events now show guests

**What it does:**
- Copies guests from `users/{userId}/events/{eventId}/guests` → `events/{eventId}/guests`
- Only migrates events you created (`createdBy === userId`)
- Adds `migratedAt` timestamp to track migration
- Keeps old data intact (safe)

---

### Option 2: Update Frontend to Use Django API (FUTURE)

Currently, `GuestManagement.tsx` uses `GuestService` which directly accesses Firebase.

**Change to:**
```typescript
import { apiListGuests, apiCreateGuest, apiUpdateGuest, apiDeleteGuest } from '../../api/guest';
```

**Benefits:**
- Uses Django API (proper architecture)
- JWT authentication
- Better permission control
- Consistent with backend

---

### Option 3: Manual Firebase Console Migration

1. Open [Firebase Console](https://console.firebase.google.com/project/deco-ad56f/firestore)
2. Navigate to `users → {your_user_id} → events → {event_id} → guests`
3. For each guest:
   - Copy guest data
   - Create new document in `events → {event_id} → guests`
   - Paste data

❌ **Not recommended** - Too slow for many guests

---

## After Migration

### Update Your Frontend (Next Steps):

1. **Update GuestManagement.tsx** to use Django API:
   ```bash
   # Current: Direct Firebase access via GuestService
   # Target: Django API via api/guest.ts
   ```

2. **Update DashboardService.ts** guest methods:
   ```typescript
   // OLD: collection(db, 'users', userId, 'events', eventId, 'guests')
   // NEW: Use Django API endpoint: /api/guest/{eventId}/
   ```

3. **Test all guest operations**:
   - [ ] List guests
   - [ ] Add guest
   - [ ] Edit guest  
   - [ ] Delete guest
   - [ ] Import CSV
   - [ ] Seat assignment

---

## Troubleshooting

### "No events showing up"
- Check if migration completed successfully
- Verify User ID matches your logged-in user
- Check Firebase Console: `events/{eventId}/guests` should have data

### "Migration failed"
- Open browser console (F12) for error details
- Verify Firebase config is correct
- Check if you have Firestore permissions

### "Still using old structure"
- Clear browser cache: `localStorage.clear()`
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- Restart dev server: `npm run dev`

---

## Files Modified

- ✅ `frontend/src/services/DashboardService.ts` - Now uses localStorage for user ID
- ✅ `migrate_guests.html` - Migration tool (ready to use)
- ✅ `get_user_id.html` - Helper to find your User ID
- ⏳ `frontend/src/pages/planner/GuestManagement.tsx` - TODO: Update to use Django API
- ⏳ `frontend/src/services/DashboardService.ts` - TODO: Update getGuests() to use Django API

---

## Next Actions

1. **Immediate**: Run migration tool to restore your event data
2. **Short-term**: Update GuestManagement to use Django API
3. **Long-term**: Remove direct Firebase access from frontend entirely
