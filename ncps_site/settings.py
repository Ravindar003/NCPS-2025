"""
Django settings for ncps_site project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'ncps-2025-polar-sciences-conference-key-12345'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []
# DEVELOPMENT ONLY
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'conference',
    'chatbot',  # Penguin Chatbot App
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ncps_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],                
        'APP_DIRS': True,         
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'conference.context_processors.theme_choices',
                'conference.context_processors.notification_count',
            ],
        },
    },
]


WSGI_APPLICATION = 'ncps_site.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Also make sure you have this
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------- reCAPTCHA configuration ----------------
# Provide these via environment variables in production. Leave empty to disable.
# For local testing the provided keys are used as defaults (do NOT commit secrets in production).
RECAPTCHA_SITE_KEY = os.getenv('RECAPTCHA_SITE_KEY', '6LctgEUsAAAAAOdNyDD6o0ad7nWN-ieYn7dxDWzC')
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY', '6LctgEUsAAAAAMBKx_992iiFhWj8sZ0fU2k-T1zW')


# Authentication settings
LOGIN_REDIRECT_URL = 'conference:dashboard'
LOGIN_URL = 'conference:login'
LOGOUT_REDIRECT_URL = 'conference:home'

# settings.py
CSP_IMG_SRC = ("'self'", "data:", "https:")

# ================= AI CHATBOT CONFIGURATION =================
# Local Ollama AI Configuration
CHATBOT_AI_ENABLED = True
CHATBOT_TYPE = 'ollama'
CHATBOT_NAME = 'Penguin'

# Ollama Server Configuration
OLLAMA_URL = 'http://localhost:11434'
OLLAMA_API_ENDPOINT = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'gemma3:4b'  # AI model to use
OLLAMA_TEMPERATURE = 0.4     # 0.0-1.0 (higher = more creative)
OLLAMA_MAX_TOKENS = 200      # Max response length
OLLAMA_TIMEOUT = 120         # Request timeout in seconds
