# SiPanit Backend Starter (Django + DRF + JWT)

## Quickstart on Windows

1. Install **Python 3.12** from https://www.python.org/downloads/ (check "Add python.exe to PATH").
2. Open **PowerShell** in this folder:
   - Right click the folder -> "Open in Terminal", or in VS Code Terminal.
3. Create & activate virtual environment:
   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Create your `.env`:
   ```powershell
   Copy-Item .env.example .env
   # then edit .env and set SECRET_KEY
   ```
6. Migrate DB and create admin:
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```
7. Run server:
   ```powershell
   python manage.py runserver
   ```

## Auth Endpoints
- `POST /api/auth/token/` — obtain JWT (username & password)
- `POST /api/auth/token/refresh/` — refresh JWT
- `GET /api/accounts/me/` — current user profile (requires Authorization: Bearer <token>)

## Event Endpoints (examples)
- `GET /api/events/events/`
- `POST /api/events/events/` (requires auth; owner auto=you)
- `GET /api/events/guests/`

Admin is at `/admin`.


---

## Firebase Login (optional)
1. Create a Firebase Service Account key (JSON).
2. Put its path or full JSON into `.env` as `FIREBASE_SERVICE_ACCOUNT_JSON`.
3. Use endpoint:
   - `POST /api/accounts/firebase/` with `{ "idToken": "<FIREBASE_ID_TOKEN>" }`
   - Returns local JWTs and user info.
