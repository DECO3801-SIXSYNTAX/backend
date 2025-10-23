# Slim Backend — Django + DRF + JWT + Firebase Login

## Install & Run
```bash
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
## Endpoints
- `POST /api/auth/token/`, `POST /api/auth/token/refresh/`
- `POST /api/accounts/firebase/`
- `GET /api/accounts/me/`
- `GET/POST /api/events/events/` (create = PLANNER/ADMIN)
- `GET/POST /api/events/guests/`
