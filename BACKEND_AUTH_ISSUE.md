# Backend Authentication Issue - IMPORTANT

## 🔴 Problem: Django Backend Doesn't Accept Firebase Tokens

### Current Situation

Your app successfully authenticates with **Firebase** (frontend), but your **Django backend** only accepts **Django JWT tokens**, not Firebase ID tokens.

**Evidence:**
- ✅ Firebase sign-in successful: "✓ Firebase token stored for API authentication"
- ✅ Firebase token refreshed: "✓ Firebase token refreshed"
- ❌ Backend rejects requests: `401 Unauthorized` on all `/api/admin/*` endpoints

### Why This Happens

1. **Frontend (React)** uses Firebase Authentication
2. **Backend (Django)** expects Django JWT tokens (username/password → JWT)
3. Firebase ID tokens and Django JWT tokens are **incompatible**

### Temporary Solution ✅

**Mock data fallback** has been implemented in `/frontend/src/lib/api.ts`:

- When backend returns `401`, the API layer automatically uses mock data
- Admin pages will display sample events, users, and activity
- This allows you to **test the UI** without backend changes

**Console warnings will show:**
```
Backend not configured for Firebase auth - using mock data
Backend not configured for Firebase auth - using mock users data
Backend not configured for Firebase auth - using mock activity data
```

---

## 🔧 Permanent Solutions

### Option 1: Configure Django to Accept Firebase Tokens (Recommended)

**Backend changes required:**

1. **Install Firebase Admin SDK:**
   ```bash
   cd backend
   pip install firebase-admin
   ```

2. **Add Firebase service account:**
   - Download service account JSON from Firebase Console
   - Save to `backend/firebase-credentials.json`

3. **Create custom Django authentication backend:**
   ```python
   # backend/SiPanit/firebase_auth.py
   import firebase_admin
   from firebase_admin import auth, credentials
   from rest_framework import authentication, exceptions
   
   cred = credentials.Certificate("firebase-credentials.json")
   firebase_admin.initialize_app(cred)
   
   class FirebaseAuthentication(authentication.BaseAuthentication):
       def authenticate(self, request):
           auth_header = request.META.get('HTTP_AUTHORIZATION')
           if not auth_header or not auth_header.startswith('Bearer '):
               return None
           
           token = auth_header.split(' ')[1]
           try:
               decoded_token = auth.verify_id_token(token)
               # Get or create Django user from Firebase UID
               from django.contrib.auth.models import User
               user, _ = User.objects.get_or_create(
                   username=decoded_token['uid'],
                   defaults={'email': decoded_token.get('email', '')}
               )
               return (user, None)
           except Exception as e:
               raise exceptions.AuthenticationFailed(f'Invalid Firebase token: {e}')
   ```

4. **Update Django settings:**
   ```python
   # backend/SiPanit/settings.py
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'SiPanit.firebase_auth.FirebaseAuthentication',
           'rest_framework_simplejwt.authentication.JWTAuthentication',
       ],
   }
   ```

### Option 2: Switch Frontend to Django JWT (Alternative)

If you want to use Django's authentication instead of Firebase:

1. Remove Firebase authentication code
2. Create a Django login endpoint
3. Store Django JWT tokens instead of Firebase tokens
4. Update sign-in flow to call Django API

---

## 🧪 Testing Current Mock Data Setup

The admin pages now work with mock data:

1. **Sign in** with your Firebase account (`adminpln@gmail.com`)
2. Navigate to **Admin Dashboard** - you'll see mock events, users, activity
3. Go to **View Events** - displays 3 sample events
4. Go to **Manage Users** - displays 4 sample users

**You can test:**
- ✅ UI/UX improvements
- ✅ Search and filtering
- ✅ Dark mode
- ✅ Navigation
- ❌ Actual CRUD operations (requires backend fix)

---

## ⚡ Next Steps

**For Production:** Implement Option 1 (Firebase Admin SDK in Django)

**For Development:** Continue using mock data to test frontend features

**Need Help?** Check Django + Firebase authentication tutorials or ask your backend developer to implement Firebase verification.
