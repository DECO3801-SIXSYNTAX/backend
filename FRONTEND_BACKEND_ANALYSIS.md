# Frontend-Backend Integration Analysis

## Date: October 21, 2025

## Issues Found and Fixes Needed

### ✅ CORRECT Configurations

1. **Backend API Endpoints** (`backend/SiPanit/urls.py`):
   - ✅ `/api/auth/login/` - Login endpoint
   - ✅ `/api/auth/register/` - Registration
   - ✅ `/api/auth/google/` - Google OAuth
   - ✅ `/api/auth/token/refresh/` - JWT refresh
   - ✅ `/api/auth/password-reset/` - Password reset
   - ✅ `/api/admin/` - Admin APIs
   - ✅ `/api/event/` - Event management
   - ✅ `/api/guest/` - Guest management

2. **Frontend API URLs**:
   - ✅ `DjangoAuthService.ts` correctly uses `http://127.0.0.1:8000/api`
   - ✅ `lib/api.ts` correctly uses `http://127.0.0.1:8000/api`

### ❌ ISSUES FOUND

#### Issue 1: Login Request Format Mismatch
**Problem:** Backend expects `username` OR `email`, but you might be sending email as email field.

**Backend Login View** (`authentication/views.py`):
```python
class _LoginSerializer(TokenObtainPairSerializer):
    # Uses Django's default TokenObtainPairSerializer
    # which expects: { "username": "...", "password": "..." }
```

**Frontend** (`DjangoAuthService.ts`):
```typescript
async login(username: string, password: string): Promise<LoginResponse> {
    body: JSON.stringify({ username, password }),
    // ✅ This is CORRECT - sending username field
}
```

**Frontend SignIn.tsx**:
```typescript
const response = await djangoAuth.login(email, password);
// ✅ This is CORRECT - passing email as username parameter
```

✅ **Actually this is fine** - Django's TokenObtainPairSerializer accepts username field, and you can configure Django to accept email as username.

#### Issue 2: Missing User Data in Context After Login
**Problem:** After successful login, the user data might not persist correctly.

**Current Flow:**
1. Login returns: `{ access, refresh, user }`
2. Frontend stores tokens and user in localStorage ✅
3. Frontend calls `setCurrentUser(appUser)` ✅
4. BUT: On page refresh, context doesn't restore user from localStorage ❌

**Fix Needed:** DashboardContext should restore user from localStorage on mount.

#### Issue 3: Django CORS Configuration
**Potential Problem:** Backend might be blocking requests from `localhost:3000`

**Check backend CORS settings** (`backend/SiPanit/settings.py`):
```python
CORS_ALLOW_ALL_ORIGINS = True  # or
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

#### Issue 4: Missing Database Migrations
**Problem:** You have 21 unapplied migrations which might cause authentication errors.

**Fix:**
```bash
cd backend
python3.10 manage.py migrate
```

#### Issue 5: No Test User in Database
**Problem:** You might not have any users in the database to test with.

**Fix:** Create a superuser:
```bash
cd backend
python3.10 manage.py createsuperuser
```

#### Issue 6: User Data Format Mismatch
**Backend returns:**
```python
{
    "access": "...",
    "refresh": "...",
    "user": {
        "id": "uuid",
        "username": "...",
        "email": "...",
        "first_name": "...",
        "last_name": "...",
        "role": "admin|planner|vendor|guest",
        "company": "...",
        "phone": "...",
        "is_active": true
    }
}
```

**Frontend expects in some places:**
```typescript
{
    id: string;
    email: string;
    name: string;  // ❌ Backend sends first_name + last_name separately
    role: string;
    password: string;  // ❌ Never send password back
}
```

## Fixes Required

### Fix 1: Update DashboardContext to Restore User on Mount

```typescript
// frontend/src/contexts/DashboardContext.tsx
export const DashboardProvider: React.FC<DashboardProviderProps> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<any>(null);
  
  // Restore user from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        const user = JSON.parse(savedUser);
        setCurrentUser(user);
      } catch (error) {
        console.error('Failed to restore user:', error);
      }
    }
  }, []);
  
  // ... rest of the code
}
```

### Fix 2: Run Database Migrations

```bash
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin/backend
python3.10 manage.py migrate
```

### Fix 3: Create Test Superuser

```bash
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin/backend
python3.10 manage.py createsuperuser
# Enter:
# Username: admin
# Email: admin@test.com
# Password: admin123 (or your preferred password)
# Role: admin
```

### Fix 4: Verify CORS Settings

Check `backend/SiPanit/settings.py` has:
```python
INSTALLED_APPS = [
    'corsheaders',
    ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Should be near the top
    ...
]

CORS_ALLOW_ALL_ORIGINS = True  # For development
# OR for production:
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]
```

### Fix 5: Remove Password from User Object

Update SignIn.tsx to not include password:
```typescript
const appUser = {
    id: user.id,
    email: user.email,
    name: user.first_name && user.last_name 
      ? `${user.first_name} ${user.last_name}`.trim()
      : user.first_name || user.username || email.split('@')[0],
    role: user.role,
    // ❌ Remove this line:
    // password: password
};
```

## Testing Steps

1. **Ensure both servers are running:**
   - Backend: `cd backend && python3.10 manage.py runserver`
   - Frontend: `cd frontend && npm run dev`

2. **Create test user:**
   ```bash
   cd backend
   python3.10 manage.py createsuperuser
   ```

3. **Test login flow:**
   - Open `http://localhost:3000`
   - Try logging in with superuser credentials
   - Check browser console for errors
   - Check backend terminal for request logs

4. **Verify authentication:**
   - After login, check localStorage for tokens:
     - `access_token`
     - `refresh_token`
     - `user`
   - Try navigating to admin dashboard
   - Check if API calls include Authorization header

## Expected Backend Responses

### Login Success:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "admin",
    "email": "admin@test.com",
    "first_name": "Admin",
    "last_name": "User",
    "role": "admin",
    "company": null,
    "phone": null,
    "is_active": true
  }
}
```

### Login Error:
```json
{
  "detail": "No active account found with the given credentials"
}
```

## Status Check

Run these checks:
```bash
# 1. Backend running?
lsof -ti:8000 && echo "✓ Backend running" || echo "✗ Backend NOT running"

# 2. Frontend running?
lsof -ti:3000 && echo "✓ Frontend running" || echo "✗ Frontend NOT running"

# 3. Database migrated?
cd backend && python3.10 manage.py showmigrations | grep "\[ \]" && echo "❌ Unapplied migrations found" || echo "✓ All migrations applied"

# 4. Any users in database?
cd backend && python3.10 manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(f'Users in DB: {User.objects.count()}')"
```
