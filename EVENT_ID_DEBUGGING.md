# Event ID Debugging Guide

## Issue
You mentioned: "my planner pages didn't have event id so i cant check it on my firebase storage"

## Event ID Flow - How It Works

### 1. **Event Creation** (`DashboardService.createEvent`)
```typescript
const docRef = await addDoc(eventsRef, newEvent);
return {
  id: docRef.id,  // ✅ Firebase auto-generates this ID
  ...newEvent,
} as Event;
```

**Result**: Every event created gets a unique Firebase document ID

### 2. **Event Fetching** (`DashboardService.getEvents`)
```typescript
return snapshot.docs.map(doc => {
  return {
    id: doc.id,  // ✅ Firebase document ID
    ...data,
  } as Event;
});
```

**Result**: All events have `event.id` property

### 3. **Event Display** (Dashboard, EventsList, etc.)
```typescript
events.map(event => (
  <div key={event.id}>  // ✅ Using event.id
    {event.name}
  </div>
))
```

**Result**: Events are displayed with their IDs

---

## How to Check Event IDs

### Method 1: Browser Console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Type:
```javascript
// Check events in DashboardContext
console.log('Events:', events);

// Or check localStorage
const user = JSON.parse(localStorage.getItem('user'));
console.log('User ID:', user.id);
```

### Method 2: Check Firebase Firestore Directly

1. **Open Firebase Console**:
   - Go to https://console.firebase.google.com
   - Select your project
   - Go to Firestore Database

2. **Navigate to Events Collection**:
   ```
   Firestore Database
   └── events (collection)
       ├── {auto-generated-id-1} (document)
       │   ├── name: "My Event"
       │   ├── createdBy: "user-id"
       │   ├── startDate: "2025-10-25"
       │   └── ...other fields
       ├── {auto-generated-id-2} (document)
       └── ...
   ```

3. **Check Event Structure**:
   - Each document ID is the `eventId`
   - The document doesn't store "id" as a field - it's the document ID itself
   - When fetched, we add `id: doc.id` to the object

### Method 3: Add Console Logging

Add this to any planner page to see event IDs:

```typescript
useEffect(() => {
  console.log('=== Events Debug ===');
  console.log('Total events:', events.length);
  events.forEach((event, index) => {
    console.log(`Event ${index + 1}:`, {
      id: event.id,
      name: event.name,
      createdBy: event.createdBy
    });
  });
}, [events]);
```

---

## Common Issues & Solutions

### Issue 1: Events show undefined ID
**Symptom**: `event.id` is `undefined`

**Cause**: Event object doesn't have `id` property

**Solution**: Check if you're using the correct service method:
```typescript
// ✅ Correct
const events = await dashboardService.getEvents();

// ❌ Wrong - raw Firebase query
const snapshot = await getDocs(collection(db, 'events'));
// This won't have .id mapped
```

### Issue 2: Can't see events in Firebase Firestore
**Symptom**: Firestore shows empty `events` collection

**Possible Causes**:
1. **No events created yet** - Create an event first
2. **Wrong user ID** - Events are filtered by `createdBy` field
3. **Firebase rules** - Check if you have read permission

**Solution**:
```typescript
// Check current user
const user = auth.currentUser;
console.log('Current User:', user?.uid);

// Check what's in Firestore
const eventsRef = collection(db, 'events');
const allEvents = await getDocs(eventsRef);
console.log('Total events in Firestore:', allEvents.size);
allEvents.forEach(doc => {
  console.log('Event:', doc.id, doc.data());
});
```

### Issue 3: Event ID doesn't match between pages
**Symptom**: Different pages show different event IDs for the same event

**Cause**: Mixing `event.id` and `event.eventId` 

**Check**: 
- `Event` type uses: `id: string`
- `Guest` type uses: `eventId: string` (reference to event)
- `EventBreakdown` uses: `eventId: string` (reference to event)

```typescript
// Event object
{
  id: "abc123",           // ✅ Event's own ID
  name: "My Event",
  ...
}

// Guest object
{
  id: "xyz789",           // Guest's own ID
  eventId: "abc123",      // ✅ Reference to Event ID
  name: "John Doe",
  ...
}
```

---

## Testing Event IDs

### 1. Create a Test Event
1. Go to http://localhost:3000/planner
2. Click "Create Event" button
3. Fill in event details
4. Click "Create"
5. **Open Console** and check:
```javascript
// Should see log:
// Created event: { id: "xyz...", name: "...", ... }
```

### 2. Verify in Firebase
1. Go to Firebase Console → Firestore
2. Open `events` collection
3. You should see a new document with auto-generated ID
4. The document ID is the `event.id`

### 3. Check Guest Management
1. Go to http://localhost:3000/planner/guest-management
2. Select an event from dropdown
3. **Open Console** and check:
```javascript
// Should see logs:
// Selected Event ID: abc123
// Loading guests for event: abc123
```

### 4. Check Event Details
1. Go to any event in the list
2. **Right-click** → Inspect Element
3. Check the `key` attribute:
```html
<div key="abc123" class="...">
  <!-- Event card -->
</div>
```

---

## Firebase Firestore Structure

Your Firebase should have this structure:

```
firestore
├── users
│   └── {userId}
│       ├── email: string
│       ├── name: string
│       ├── role: string
│       └── ...
├── events
│   └── {eventId}  ← Auto-generated by Firebase
│       ├── name: string
│       ├── description: string
│       ├── createdBy: userId
│       ├── startDate: string
│       ├── endDate: string
│       └── ...
├── guests
│   └── {guestId}
│       ├── eventId: string  ← References events/{eventId}
│       ├── name: string
│       ├── email: string
│       └── ...
├── floor_plans
│   └── {floorPlanId}
│       ├── eventId: string  ← References events/{eventId}
│       ├── tables: array
│       └── ...
└── activities
    └── {activityId}
        ├── eventId: string | null
        ├── userId: string
        ├── action: string
        └── ...
```

---

## Quick Debugging Checklist

Run this in your browser console on any planner page:

```javascript
// 1. Check if user is logged in
const user = JSON.parse(localStorage.getItem('user'));
console.log('✓ User:', user?.email, 'ID:', user?.id);

// 2. Check Firebase auth
import { auth } from './config/firebase';
console.log('✓ Firebase User:', auth.currentUser?.uid);

// 3. Check events in context
// (You'll need to be on a page that uses DashboardContext)
console.log('✓ Events:', events);
console.log('✓ Event IDs:', events.map(e => e.id));

// 4. Check Firebase directly
import { collection, getDocs } from 'firebase/firestore';
import { db } from './config/firebase';

const eventsSnapshot = await getDocs(collection(db, 'events'));
console.log('✓ Total events in Firestore:', eventsSnapshot.size);
eventsSnapshot.forEach(doc => {
  console.log('  -', doc.id, ':', doc.data().name);
});
```

---

## Next Steps

**Tell me specifically**:
1. Are you trying to create a new event?
2. Are you trying to view existing events?
3. Are events showing in the UI but without IDs?
4. Is Firebase Firestore empty?
5. Are you getting any console errors?

**Then I can**:
- Add specific logging to help debug
- Check your Firebase configuration
- Verify event creation is working
- Help you query Firebase Firestore correctly
