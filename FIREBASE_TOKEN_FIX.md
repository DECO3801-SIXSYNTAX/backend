# Firebase Authentication Token Fix

## Problem
Admin pages were receiving 401 Unauthorized errors when calling Django backend API endpoints because the Firebase authentication token wasn't being stored or sent with API requests.

## Root Cause
When users signed in with Firebase, the application was:
1. ✅ Successfully authenticating with Firebase
2. ✅ Setting user context in the app
3. ❌ **NOT storing the Firebase ID token** for API calls
4. ❌ **NOT refreshing expired tokens**

## Solution Implemented

### 1. Store Firebase Token on Sign In (`SignIn.tsx`)
```typescript
// After successful Firebase authentication
const userCredential = await signInWithEmailAndPassword(auth, email, password);
const idToken = await userCredential.user.getIdToken();
localStorage.setItem('access_token', idToken);
```

**What this does:**
- Gets the Firebase ID token after successful authentication
- Stores it in localStorage as 'access_token'
- This token is now automatically included in all API requests via the `withAuth()` function

### 2. Auto Token Refresh in App (`App.tsx`)

#### Auth State Listener
```typescript
onAuthStateChanged(auth, async (firebaseUser) => {
  if (firebaseUser) {
    const idToken = await firebaseUser.getIdToken();
    localStorage.setItem('access_token', idToken);
  }
});
```

**What this does:**
- Listens for Firebase auth state changes
- Automatically updates the token whenever auth state changes
- Ensures token is always synced

#### Auto-Refresh Timer
```typescript
setInterval(async () => {
  const user = auth.currentUser;
  if (user) {
    const newToken = await user.getIdToken(true); // Force refresh
    localStorage.setItem('access_token', newToken);
  }
}, 50 * 60 * 1000); // Every 50 minutes
```

**What this does:**
- Firebase tokens expire after 1 hour
- Auto-refreshes token every 50 minutes (before expiration)
- Prevents 401 errors from expired tokens

### 3. Enhanced Token Refresh in API (`api.ts`)
```typescript
async function refreshAccessToken(): Promise<string | null> {
  // Try Firebase token refresh first
  const currentUser = auth.currentUser;
  if (currentUser) {
    const newToken = await currentUser.getIdToken(true);
    setAuthToken(newToken);
    return newToken;
  }
  
  // Fallback to JWT refresh for Django
  // ... existing JWT refresh code ...
}
```

**What this does:**
- When API returns 401, automatically attempts token refresh
- Prioritizes Firebase token refresh
- Falls back to Django JWT refresh if needed
- Retries failed request with new token

## How It Works

### Authentication Flow
1. User enters email/password → Click Sign In
2. Firebase authenticates user
3. Get Firebase ID token
4. Store token in localStorage
5. Navigate to admin dashboard
6. All API calls include token in Authorization header

### API Request Flow
```
API Request → Include Bearer token in header
  ↓
  ├─ Success (200) → Return data
  │
  └─ Unauthorized (401)
      ↓
      Refresh Firebase token
      ↓
      Retry request with new token
      ↓
      ├─ Success → Return data
      └─ Fail → Show error
```

### Token Lifecycle
```
Sign In
  ↓
Get Firebase Token (valid 1 hour)
  ↓
Store in localStorage
  ↓
Use for API calls
  ↓
[50 minutes later]
  ↓
Auto-refresh token
  ↓
Continue using API
```

## Files Modified

1. **`/frontend/src/pages/SignIn.tsx`**
   - Store Firebase token after sign-in
   - Store token after user creation

2. **`/frontend/src/lib/api.ts`**
   - Enhanced token refresh with Firebase support
   - Import Firebase auth instance

3. **`/frontend/src/App.tsx`**
   - Auth state listener with token sync
   - Auto-refresh timer (every 50 minutes)

## Testing Checklist

- [x] Sign in with Firebase successfully
- [x] Token stored in localStorage
- [x] Admin dashboard loads without 401 errors
- [x] ManageUsers page loads user data
- [x] ViewEvents page loads event data
- [x] Token auto-refreshes before expiration
- [x] Auth state changes update token

## Expected Behavior

### Before Fix
```
✓ Firebase sign-in successful
✓ Current user set in context
✓ Navigating to dashboard
❌ 401 Unauthorized - /api/admin/events/
❌ 401 Unauthorized - /api/admin/users/
❌ 401 Unauthorized - /api/admin/activity/
```

### After Fix
```
✓ Firebase sign-in successful
✓ Firebase token stored for API authentication
✓ Current user set in context
✓ Navigating to dashboard
✓ Firebase token synced
✓ API calls succeed with token
✓ Data loads in admin pages
```

## Important Notes

1. **Token Expiration**: Firebase tokens expire after 1 hour
2. **Auto-Refresh**: Token refreshes every 50 minutes automatically
3. **Manual Refresh**: On 401 error, token is refreshed and request retried
4. **Persistence**: Token persists in localStorage across page refreshes
5. **Security**: Token is sent via Authorization Bearer header

## Backend Requirements

Your Django backend should:
1. Accept Firebase ID tokens in Authorization header
2. Verify Firebase tokens using Firebase Admin SDK
3. Extract user information from verified token
4. Grant appropriate permissions based on user claims

Example Django middleware:
```python
from firebase_admin import auth

def verify_firebase_token(request):
    token = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[-1]
    try:
        decoded_token = auth.verify_id_token(token)
        request.user_id = decoded_token['uid']
        request.user_email = decoded_token['email']
        return True
    except:
        return False
```

## Debug Tips

If still getting 401 errors:

1. **Check token in localStorage**
   ```javascript
   console.log(localStorage.getItem('access_token'));
   ```

2. **Verify token is sent**
   - Open DevTools → Network tab
   - Check API request headers
   - Should see: `Authorization: Bearer <token>`

3. **Check Firebase console**
   - Verify user exists in Firebase Auth
   - Check user permissions/claims

4. **Backend logs**
   - Check Django logs for token verification errors
   - Verify Firebase Admin SDK is configured

---

**Status: ✅ Fixed** - All admin API calls now include proper Firebase authentication token!
