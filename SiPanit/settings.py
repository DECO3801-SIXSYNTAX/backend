from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = os.getenv('DEBUG', '1') == '1'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    #'accounts',
    'events',
    'anymail',
    'authentication.apps.AuthenticationConfig',
    'event',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'SiPanit.middleware.security_audit.SecurityAuditMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True 

ROOT_URLCONF = 'SiPanit.urls'

TEMPLATES = [{
    'BACKEND':'django.template.backends.django.DjangoTemplates',
    'DIRS':[BASE_DIR / 'templates'],
    'APP_DIRS':True,
    'OPTIONS':{'context_processors':[
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'SiPanit.wsgi.application'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 30},  # wait up to 30s instead of failing fast
    }
}


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Australia/Brisbane'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',)
}


# ----- Firebase service account path -----
FIREBASE_SERVICE_ACCOUNT = os.getenv('FIREBASE_SERVICE_ACCOUNT', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

AUTH_USER_MODEL = "authentication.User"

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

TIME_ZONE = "Australia/Brisbane"

# Email configuration
EMAIL_BACKEND = "SiPanit.email_backends.MultiEmailBackend"
DEFAULT_FROM_EMAIL = "hevaquenta@gmail.com"

# Anymail configuration for SendGrid
ANYMAIL = {
    "SENDGRID_API_KEY": os.getenv("SENDGRID_API_KEY"),
}

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# settings.py
MIDDLEWARE.insert(0, 'SiPanit.middleware.security_audit.SecurityAuditMiddleware')

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "security_audit": {"handlers": ["console"], "level": "INFO"},
    },
}

# settings.py
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'user': '10/minute'},
})

DEBUG = os.getenv('DEBUG', '1') == '1'

CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [o for o in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if o]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE   = not DEBUG
CSRF_COOKIE_SECURE      = not DEBUG
SECURE_HSTS_SECONDS     = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD     = not DEBUG

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"].append(
    "authentication.throttles.PasswordResetRateThrottle"
)
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["password_reset"] = "3/minute"