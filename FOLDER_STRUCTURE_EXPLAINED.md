# 📁 Repository Structure Explanation

## Current Situation

You have a **confusing duplicate structure** that happened during git operations. Here's what you have:

```
SiPanit:Admin/                  ← ROOT (tracks backend git repo)
├── .git/                       ← Points to backend repo
├── accounts/                   ← Django apps (CORRECT)
├── adminapi/
├── authentication/
├── event/
├── events/
├── guest/
├── SiPanit/                   ← Django settings (CORRECT)
├── manage.py                   ← Django management (CORRECT)
├── requirements.txt
├── frontend/                   ← React app (separate git repo)
│   ├── .git/                  ← Points to frontend repo
│   ├── src/
│   └── package.json
└── backend/                    ← ⚠️ DUPLICATE/MISTAKE (remove this!)
    ├── accounts/              ← Same as root level
    ├── adminapi/
    ├── SiPanit/
    ├── manage.py
    └── (all Django files duplicated)
```

## What Happened?

1. Your monorepo structure was created with `backend/` as a subdirectory
2. Later, the **root directory** was set to track the backend git repository
3. When you did `git pull origin dev` in the root, it updated root-level Django files
4. The `backend/` folder became an **orphaned duplicate**

## Correct Structure (What You Should Have)

```
SiPanit:Admin/              ← Backend Django project (git: backend repo)
├── .git/                   ← Tracks DECO3801-SIXSYNTAX/backend
│
├── # Django Backend Files
├── accounts/              ← Django app for accounts
├── adminapi/              ← Django app for admin API
├── authentication/        ← Django app for auth
├── crypto/                ← Django app for crypto/QR
├── event/                 ← Django app for events (Firestore)
├── events/                ← Django app for events (SQL)
├── guest/                 ← Django app for guests
├── project/               ← Old/unused?
├── SiPanit/              ← Django project settings
├── static/                ← Static files
├── vendor/                ← Django app for vendors
│
├── # Django Config Files
├── manage.py              ← Django management command
├── requirements.txt       ← Python dependencies
├── db.sqlite3             ← SQLite database
├── .env                   ← Environment variables
├── .env.development
├── .env.example
│
├── # Firebase Files
├── .firebaserc
├── firebase.json
├── firestore.rules
│
├── # Documentation
├── README.md
├── ADMIN_IMPROVEMENTS.md
├── BACKEND_ARCHITECTURE.md
├── BACKEND_AUTH_ISSUE.md
├── FIREBASE_TOKEN_FIX.md
│
└── frontend/              ← React Frontend (separate git repo)
    ├── .git/              ← Tracks DECO3801-SIXSYNTAX/frontend
    ├── src/
    ├── public/
    ├── package.json
    ├── vite.config.ts
    └── (all React files)
```

## Why This Makes Sense

### Backend at Root Level
- The root is a **Django project**
- Running `python manage.py runserver` from root works
- All Django apps are at root level
- Git tracks: backend repository

### Frontend as Subdirectory
- Frontend is a **separate git repository**
- Running `npm run dev` from `frontend/` works
- Git tracks: frontend repository (independent)

## How to Fix This

### Option 1: Remove the Duplicate (Recommended)

```bash
# CAREFUL: Make sure you don't need anything from backend/ folder
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin
rm -rf backend/

# The root level already has all the backend code!
```

### Option 2: If You Want Backend in Subdirectory

If you really want `backend/` as a subdirectory, you need to:

```bash
# Move all Django files INTO backend/
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin

# This is complex and risky - not recommended
```

## Verification

After cleaning up, your structure should look like:

```bash
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin
ls -l

# You should see:
# - Django apps (accounts, adminapi, authentication, etc.)
# - Django config (manage.py, requirements.txt)
# - frontend/ directory
# - NO backend/ directory
```

## Running Your Apps

### Backend (Django)
```bash
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin
python manage.py runserver
# Runs on http://127.0.0.1:8000
```

### Frontend (React)
```bash
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin/frontend
npm run dev
# Runs on http://localhost:3000
```

## Git Operations

### For Backend Changes
```bash
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin
git status                    # Shows backend repo status
git pull origin dev           # Pulls backend changes
git add .
git commit -m "message"
git push origin dev
```

### For Frontend Changes
```bash
cd /Users/auli/Documents/UQ/deco3801/SiPanit:Admin/frontend
git status                    # Shows frontend repo status
git pull origin merge1        # Pulls frontend changes
git add .
git commit -m "message"
git push origin merge1
```

## Summary

**The `backend/` folder is a duplicate/mistake. Your root directory IS the backend.**

Remove it with:
```bash
rm -rf /Users/auli/Documents/UQ/deco3801/SiPanit:Admin/backend/
```

Then your structure will be clean and correct! ✅
