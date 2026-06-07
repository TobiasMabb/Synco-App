import os
import socket

if "pythonanywhere" in socket.gethostname():
    SITE_ID = 3 # Production Site: syncoo.pythonanywhere.com
else:
    SITE_ID = 2 # Local Site: (127.0.0.1:8000)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-synco-super-secret-key-change-in-production'

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'syncooo.pythonanywhere.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party auth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Custom Apps
    'accounts',
    'core',
    'songs',
    'setlists',
    'pwa',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Idinagdag para sa maayos na pag-serve ng static files sa Render production
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Third-Party Auth
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

]

ROOT_URLCONF = 'synco.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Global templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'synco.wsgi.application'

# 🛠️ FIXED: Kapag nasa Render, itatabi natin ang database sa permanenteng /data/ disk folder para hindi mabura
if os.environ.get('RENDER'):
    DB_PATH = os.path.join('/data', 'db.sqlite3')
else:
    DB_PATH = BASE_DIR / 'db.sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_PATH,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Idinagdag para mas mapabilis ang loading ng static structures sa production hosting
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Authentication Configurations
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'account_login'

ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SESSION_REMEMBER = True

SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# Pinapayagan si YouTube na makita kung saan nanggaling ang embed request
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# --- Progressive Web App Settings ---
PWA_APP_NAME = 'Synco'
PWA_APP_DESCRIPTION = "A Progressive Web App version of Synco"
PWA_APP_THEME_COLOR = '#0A0A0A'
PWA_APP_BACKGROUND_COLOR = '#FFFFFF'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_ORIENTATION = 'portrait'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_ICONS = [
    {
    'src': '/static/images/icon-192.png',
    'sizes': '192x192'
    },
    {
    'src': '/static/images/icon-512.png',
    'sizes': '512x512'
    }
]
PWA_APP_ICONS_APPLE = [
    {
    'src': '/static/images/icon-192.png',
    'sizes': '192x192'
    },
    {
    'src': '/static/images/icon-512.png',
    'sizes': '512x512'
    }
]
PWA_APP_DIR = 'ltr'
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static/js', 'serviceworker.js')