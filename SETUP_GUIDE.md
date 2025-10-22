# SiPanit Backend Setup Guide

## 🚀 Quick Setup for New Team Members

### Prerequisites
- Python 3.10 or higher
- Git
- Firebase credentials file

### 1️⃣ Clone and Setup

```bash
# Clone the repository
git clone https://github.com/DECO3801-SIXSYNTAX/backend.git
cd backend

# Checkout the merge2 branch
git checkout merge2

# Install Python dependencies
pip3 install -r requirements.txt
```

### 2️⃣ Environment Configuration

Create a `.env` file in the `backend/` directory:

```env
ENV=dev
SECRET_KEY=your-secret-key-here
DEBUG=1
ALLOWED_HOSTS=127.0.0.1,localhost

# Firebase Configuration
FIREBASE_PROJECT_ID=deco-ad56f
FIREBASE_CREDENTIALS=credentials/firebase-admin.json
FIREBASE_EMULATOR=0

# Google OAuth
GOOGLE_CLIENT_ID=39518858179-okj6ufls3a79hhc9t35dr455cj66b3g9.apps.googleusercontent.com

# Email Configuration (for password reset)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# QR Code Encryption
QR_ENCRYPTION_KEY=your-32-character-encryption-key
```

**Important:** Get the Firebase credentials file (`firebase-admin.json`) from your team lead and place it in `backend/credentials/` folder.

### 3️⃣ Database Setup

```bash
# Run migrations
python3.10 manage.py migrate

# Sync Firebase users to Django database (IMPORTANT!)
python3.10 manage.py sync_firebase_users

# Create a superuser (optional, for Django admin access)
python3.10 manage.py createsuperuser
```

### 4️⃣ Start the Server

```bash
python3.10 manage.py runserver
```

The backend should now be running at `http://127.0.0.1:8000/`

---

## 🔐 Login Issues?

### Problem: "401 Unauthorized" when trying to login

**Cause:** Your Firebase Auth user hasn't been synced to Django database yet.

**Solution:**
```bash
cd backend
python3.10 manage.py sync_firebase_users
```

This command will:
- ✅ Import all Firebase Authentication users to Django
- ✅ Create Django user accounts with role "planner" by default
- ✅ Allow you to login with your existing Firebase email

### Check if sync worked:
```bash
python3.10 manage.py shell

# In Python shell:
from authentication.models import User
print(f"Total users: {User.objects.count()}")
User.objects.filter(email='your-email@gmail.com').exists()  # Should return True
```

---

## 🛠️ Useful Management Commands

### Sync Firebase Users
```bash
# Dry run (see what would be synced without making changes)
python3.10 manage.py sync_firebase_users --dry-run

# Actually sync users
python3.10 manage.py sync_firebase_users

# Limit number of users to sync
python3.10 manage.py sync_firebase_users --limit 50
```

### Database Management
```bash
# Run migrations
python3.10 manage.py migrate

# Create migrations after model changes
python3.10 manage.py makemigrations

# Reset database (CAUTION: deletes all data!)
rm db.sqlite3
python3.10 manage.py migrate
python3.10 manage.py sync_firebase_users
```

### View Users
```bash
python3.10 manage.py shell

# In shell:
from authentication.models import User
users = User.objects.all()
for u in users:
    print(f"{u.email} - {u.role} - Active: {u.is_active}")
```

---

## 📝 API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login with email/password
- `POST /api/auth/google/` - Login with Google OAuth
- `POST /api/auth/logout/` - Logout
- `POST /api/auth/password-reset/` - Request password reset
- `POST /api/auth/password-reset-confirm/` - Confirm password reset

### Users (Admin only)
- `GET /api/users/` - List users (company-scoped)
- `GET /api/users/{id}/` - Get user details
- `POST /api/users/` - Create user
- `PATCH /api/users/{id}/` - Update user
- `POST /api/users/{id}/suspend/` - Suspend user
- `POST /api/users/{id}/activate/` - Activate user

### Events
- `GET /api/events/` - List events
- `POST /api/events/` - Create event
- `GET /api/events/{id}/` - Get event details
- `PATCH /api/events/{id}/` - Update event
- `DELETE /api/events/{id}/` - Delete event

### Guests
- `GET /api/guests/?eventId={id}` - List guests for event
- `POST /api/guests/` - Add guest
- `PATCH /api/guests/{id}/` - Update guest
- `DELETE /api/guests/{id}/` - Delete guest

---

## 🔧 Troubleshooting

### Firebase Connection Issues
1. Check if `credentials/firebase-admin.json` exists
2. Verify `FIREBASE_PROJECT_ID=deco-ad56f` in `.env`
3. Run `python3.10 manage.py sync_firebase_users --dry-run` to test connection

### Module Import Errors
```bash
# Make sure you're using Python 3.10
python3.10 --version  # Should be 3.10.x

# Reinstall dependencies
pip3 install -r requirements.txt --force-reinstall
```

### Port Already in Use
```bash
# Kill existing server
pkill -f "python3.10 manage.py runserver"

# Or use a different port
python3.10 manage.py runserver 8001
```

---

## 👥 User Roles

- **Admin**: Full system access, can manage all users in their company
- **Planner**: Can create/manage events and guests
- **Vendor**: Limited access (vendor-specific features)
- **Guest**: Event attendee (kiosk check-in only)

Default role for synced Firebase users is **Planner**. Change roles via Django admin or API.

---

## 📚 Additional Resources

- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- Firebase Admin SDK: https://firebase.google.com/docs/admin/setup

---

## 🆘 Need Help?

Contact your team lead or check the team Slack/Discord channel.
