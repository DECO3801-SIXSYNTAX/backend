# 🏗️ Backend Architecture Overview

## 📋 Tech Stack

- **Framework**: Django 4.x + Django REST Framework
- **Authentication**: JWT (djangorestframework-simplejwt) + Google OAuth
- **Database**: 
  - SQLite (default, local dev)
  - PostgreSQL (production-ready with psycopg2-binary)
- **Cloud Services**: 
  - Firebase Admin SDK
  - Google Cloud Firestore (primary data store for events/guests)
  - Google Cloud Storage
- **Email**: SendGrid via django-anymail
- **CORS**: django-cors-headers (currently allows all origins)

---

## 🗂️ Project Structure

```
backend/
├── SiPanit/              # Main Django project
│   ├── settings.py       # Configuration
│   ├── urls.py           # Root URL routing
│   └── firebase.py       # Firebase initialization
├── authentication/       # User management & auth
├── adminapi/            # Admin dashboard APIs
├── events/              # Django models (Event, Guest)
├── event/               # Firestore event CRUD + layouts
├── guest/               # Firestore guest management
├── vendor/              # Vendor-specific APIs
└── manage.py
```

---

## 👥 User Model & Roles

**Model**: `authentication.models.User` (extends AbstractUser)

**Roles** (TextChoices):
- `ADMIN` - Full system access
- `PLANNER` - Event planning & management
- `VENDOR` - Collaborator on events
- `GUEST` - Basic access

**Fields**:
```python
id: UUID (primary key)
role: CharField (choices above)
company: CharField (planner-specific)
phone: CharField
experience: TextField
specialty: CharField
# + all standard Django User fields (username, email, password, etc.)
```

---

## 🔐 Authentication & Authorization

### Endpoints

#### **JWT Token Auth**
- `POST /api/auth/token/` - Obtain access + refresh tokens
- `POST /api/auth/token/refresh/` - Refresh access token

#### **Custom Auth**
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login (returns JWT + user data)
- `POST /api/auth/logout/` - Logout
- `POST /api/auth/google/` - Google OAuth login

#### **Password Reset**
- `POST /api/auth/password-reset/` - Request reset email
- `POST /api/auth/password-reset-confirm/` - Confirm reset with token

### JWT Configuration
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}
```

### Custom Permissions
- `IsAdmin` - Requires `role='admin'`
- `IsPlanner` - Requires `role='planner'`
- `IsPlannerOrAdmin` - Either role
- `IsAdminOnly` - Admin only (used in adminapi)

---

## 📊 Data Architecture

### **Hybrid Storage Strategy**

1. **Django Database (SQLite/PostgreSQL)**
   - User accounts (`authentication.User`)
   - Django admin panel data
   - Session management

2. **Firebase Firestore** (Primary Event Data)
   - Events collection
   - Guests subcollection (per event)
   - Layouts collection (floor plans)
   - Activity logs

### **Event Schema (Firestore)**
```javascript
events/{eventId} = {
  id: string,
  name: string,
  date: string (ISO 8601),
  venue: string,
  status: "Draft" | "Planning" | "Active" | "Completed",
  createdBy: string (user UUID),
  company: string (uppercase),
  collaborators: string[] (user UUIDs),
  tags: string[],
  startDate: timestamp,
  endDate: timestamp,
  budget: number,
  expectedGuests: number,
  description: string,
  createdAt: timestamp,
  updatedAt: timestamp
}
```

### **Guest Schema (Firestore Subcollection)**
```javascript
events/{eventId}/guests/{guestId} = {
  id: string,
  name: string,
  email: string,
  phone: string,
  dietaryNeeds: string,
  accessibilityNeeds: string,
  checkedIn: boolean,
  checkedInAt: timestamp,
  plusOne: boolean,
  table: string,
  notes: string,
  qrCode: string (encrypted)
}
```

### **Layout Schema (Firestore)**
```javascript
layouts/{eventId} = {
  event_id: string,
  version: number (optimistic locking),
  canvas: {
    width: number,
    height: number,
    grid: number,
    scale: number,
    px_per_m: number,
    roomBoundary: object,
    floorplan_id: string
  },
  elements: [{
    id: string,
    type: string,
    name: string,
    capacity: number,
    geom: {
      x: number, y: number,
      width: number, height: number,
      rotation: number,
      radius: number,
      color: string,
      meta: object
    },
    assigned_guest_ids: string[]
  }],
  createdAt: timestamp,
  updatedAt: timestamp
}
```

---

## 🚀 API Endpoints

### **Admin APIs** (`/api/admin/`)
**Permission**: IsAuthenticated + IsAdminOnly

- `GET /api/admin/users/` - List users (filterable by role, status, search)
- `GET /api/admin/events/` - List all events (Firestore)
  - Query params: `?status=active&q=search&limit=100`
- `GET /api/admin/activity/` - Activity logs
  - Query params: `?eventId=xxx&limit=30`

### **User Management** (`/api/users/`)
**Permission**: IsAuthenticated (+ role-based)

- `GET /api/users/` - List users (company-scoped, admin only)
  - Query params: `?role=planner,admin&status=active&q=search`
- `GET /api/users/{id}/` - Get user details
- `POST /api/users/` - Create user
- `PATCH /api/users/{id}/` - Update user
- `POST /api/users/{id}/suspend/` - Suspend user (admin)
- `POST /api/users/{id}/activate/` - Activate user (admin)

### **Event Management** (`/api/event/`)
**Permission**: IsAuthenticated + IsPlanner

- `GET /api/event/events/` - List events
  - Query param: `?mine=1` (only my events)
- `GET /api/event/events/{id}/` - Get event details
- `POST /api/event/events/` - Create event
- `PATCH /api/event/events/{id}/` - Update event
- `DELETE /api/event/events/{id}/` - Delete event

#### **Collaborator Management**
- `POST /api/event/events/{id}/invite-collaborator/`
  - Body: `{ "user_id": "uuid" }` or `{ "email": "vendor@x.com" }`
- `POST /api/event/events/{id}/remove-collaborator/`
  - Body: `{ "user_id": "uuid" }` or `{ "email": "vendor@x.com" }`
- `POST /api/event/events/{id}/invite-vendor/`
  - Body: `{ "email": "required", "name": "optional", "company": "optional" }`
  - Creates vendor user if doesn't exist, adds to collaborators

### **Layout/Floor Plan** (`/api/event/layouts/`)
**Permission**: IsAuthenticated + IsPlanner

- `POST /api/event/layouts/save/` - Save floor plan
  - Supports FE payload (canvasSize, elements) or legacy payload
  - Version conflict detection & resolution
- `GET /api/event/layouts/{event_id}/` - Get floor plan
- `GET /api/event/layouts/{event_id}/meta/` - Get layout metadata (version, updatedAt)

### **Event Statistics**
- `GET /api/event/events/{event_id}/stats/` - Event stats
  ```json
  {
    "totalGuests": 150,
    "assignedSeats": 120,
    "dietaryNeeds": 25,
    "accessibilityNeeds": 5,
    "completionRate": 80.0
  }
  ```

### **Guest Management** (`/api/guest/`)
**Permission**: IsAuthenticated

- `GET /api/guest/{event_id}/` - List guests for event
- `POST /api/guest/{event_id}/` - Create guest
- `PATCH /api/guest/{event_id}/{guest_id}/` - Update guest
- `DELETE /api/guest/{event_id}/{guest_id}/` - Delete guest
- `POST /api/guest/{event_id}/import-csv/` - Bulk import from CSV
- `GET /api/guest/{event_id}/{guest_id}/qr/` - Get QR code PNG

### **Vendor APIs** (`/api/vendor/`)
**Permission**: IsAuthenticated + role='vendor'

- `GET /api/vendor/events/` - List events where user is collaborator

---

## 🔒 Security Features

### **RBAC (Role-Based Access Control)**
- Custom permissions: `IsAdmin`, `IsPlanner`, `IsAdminOnly`, `IsPlannerOrAdmin`
- Company-scoped data isolation (users can only see data from their company)
- Event ownership & collaborator checks

### **Authentication**
- JWT tokens (60 min access, 7 day refresh)
- Google OAuth integration
- Password reset with email tokens
- Suspended users blocked from login

### **Data Protection**
- QR codes encrypted with `QR_ENCRYPTION_KEY`
- CORS enabled (currently allow all - should restrict in production)
- Company-based tenant isolation

### **Activity Logging**
Activity logs stored in Firestore for audit trail:
```javascript
activity/{id} = {
  action: "event.creation" | "event.update" | "event.delete",
  entity_type: "event" | "user" | "guest",
  entity_id: string,
  event_id: string,
  actor_id: string,
  actor_email: string,
  ts: timestamp,
  details: object
}
```

---

## 🚨 Known Issues & Limitations

### **Current Limitations**

1. **No Firebase Token Authentication**
   - Backend accepts Django JWT only
   - Frontend uses Firebase auth but backend doesn't verify Firebase ID tokens
   - **Solution needed**: Implement Firebase Admin SDK token verification

2. **CORS Allow All**
   ```python
   CORS_ALLOW_ALL_ORIGINS = True  # ⚠️ Security risk in production
   ```
   - Should restrict to specific frontend origins

3. **Company Isolation Incomplete**
   - Some endpoints don't enforce company-scoped filtering
   - Admin can see all companies' data (may be intentional)

4. **No Rate Limiting**
   - APIs vulnerable to abuse/DDoS
   - Recommend: django-ratelimit or DRF throttling

5. **Email Failure Silent**
   ```python
   fail_silently=True  # Password reset emails
   ```
   - Users won't know if email sending fails

6. **SQLite in Production**
   - Default database is SQLite (not suitable for production)
   - Need to switch to PostgreSQL with proper config

### **Security Recommendations**

1. **Add Firebase Token Verification**
   ```python
   # In settings.py REST_FRAMEWORK
   'DEFAULT_AUTHENTICATION_CLASSES': [
       'path.to.FirebaseAuthentication',  # Add this
       'rest_framework_simplejwt.authentication.JWTAuthentication',
   ]
   ```

2. **Restrict CORS**
   ```python
   CORS_ALLOWED_ORIGINS = [
       "http://localhost:3000",
       "https://yourapp.com",
   ]
   ```

3. **Add Rate Limiting**
   ```python
   REST_FRAMEWORK = {
       'DEFAULT_THROTTLE_CLASSES': [
           'rest_framework.throttling.AnonRateThrottle',
           'rest_framework.throttling.UserRateThrottle'
       ],
       'DEFAULT_THROTTLE_RATES': {
           'anon': '100/hour',
           'user': '1000/hour'
       }
   }
   ```

4. **Environment Variables Required**
   ```bash
   SECRET_KEY=<generate strong key>
   DEBUG=0
   ALLOWED_HOSTS=yourapp.com
   FIREBASE_SERVICE_ACCOUNT=path/to/credentials.json
   SENDGRID_API_KEY=<your key>
   GOOGLE_CLIENT_ID=<your client id>
   QR_ENCRYPTION_KEY=<generate key>
   ```

---

## 🔄 Data Flow Examples

### **Event Creation Flow**
1. Frontend: `POST /api/event/events/` with event data
2. Backend: Validates data, adds `createdBy` and `company`
3. Firestore: Creates document in `events` collection
4. Activity log: Records `event.creation` action
5. Response: Returns `{ "id": "event-uuid" }`

### **Guest Check-in Flow**
1. Scanner: Reads QR code
2. Backend: `POST /api/guest/debug-decode-guest/` to decrypt
3. Backend: Updates `checkedIn: true` in Firestore
4. Response: Guest details + check-in status

### **Floor Plan Save with Conflict Resolution**
1. Frontend: `POST /api/event/layouts/save/` with version number
2. Backend: Checks current version in Firestore
3. If conflict: Returns current version
4. Frontend: Retries with updated version
5. Backend: Saves layout with incremented version
6. Response: Complete floor plan data

---

## 📈 Performance Considerations

### **Firestore Queries**
- Indexes required for compound queries (status + order by)
- Limit fetches to avoid over-reading (default: 100 docs)
- Client-side filtering for text search (Firestore doesn't support full-text)

### **Layout Versioning**
- Optimistic locking prevents overwrite conflicts
- Version stored with each layout save
- Retry logic in API handles conflicts

### **Company-Scoped Queries**
- All company comparisons use uppercase: `.upper()`
- Database queries should have indexes on company field

---

## 🛠️ Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env with your credentials

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run dev server
python manage.py runserver

# Or use custom command (if exists)
python manage.py rundev
```

### **Required Services**
1. **Firebase Project** with:
   - Firestore enabled
   - Service account JSON downloaded
   - Authentication enabled (Google provider)

2. **SendGrid Account**
   - API key for email sending

3. **Google OAuth**
   - Client ID for OAuth login

---

## 📝 API Response Formats

### **Success Response**
```json
{
  "id": "uuid",
  "field": "value"
}
```

### **Error Response**
```json
{
  "detail": "Error message",
  "field_name": ["Validation error"]
}
```

### **Pagination** (where applicable)
```json
{
  "count": 100,
  "next": "url",
  "previous": null,
  "results": []
}
```

---

## 🎯 Frontend Integration Notes

### **Authentication Flow**
1. User signs in with Firebase (frontend)
2. Frontend tries to use Firebase token with backend → **401 Unauthorized**
3. **Current workaround**: Mock data fallback in frontend API layer
4. **Proper solution**: Backend needs Firebase Admin SDK integration

### **Headers Required**
```javascript
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### **Recommended API Client Setup**
```javascript
// With automatic token refresh
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      const newToken = await refreshToken();
      error.config.headers.Authorization = `Bearer ${newToken}`;
      return axios.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

---

## 📚 Key Dependencies

```
django                          # Web framework
djangorestframework            # REST API
djangorestframework-simplejwt  # JWT auth
django-cors-headers            # CORS support
firebase-admin                 # Firebase integration
google-cloud-firestore         # Firestore client
django-anymail[sendgrid]       # Email sending
google-auth                    # Google OAuth
python-dotenv                  # Environment variables
cryptography                   # QR encryption
qrcode[pil]                    # QR code generation
```

---

## 🔮 Future Improvements

1. **Firebase Auth Integration** - Support Firebase ID tokens
2. **WebSocket Support** - Real-time updates (Django Channels)
3. **Celery Task Queue** - Async email sending, bulk operations
4. **Redis Cache** - Session storage, API caching
5. **API Versioning** - `/api/v1/`, `/api/v2/`
6. **GraphQL** - Alternative to REST for complex queries
7. **File Upload** - Event images, guest photos
8. **Notifications** - Push notifications for event updates
9. **Analytics** - Dashboard metrics, usage tracking
10. **Multi-tenancy** - Better company isolation with tenant middleware

---

## 📞 Support

For backend issues or questions, check:
- Django logs: `python manage.py runserver` output
- Firestore console: https://console.firebase.google.com
- Error responses for detailed validation messages
