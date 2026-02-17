# finance_app/settings.py
import os
import dj_database_url
from pathlib import Path
from django.utils.csp import CSP

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================
# SECURITY SETTINGS
# ============================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-dev-only-key-DO-NOT-USE-IN-PRODUCTION-12345'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# Allowed hosts
ALLOWED_HOSTS_STR = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(',')]

# Content Security Policy

# CSP configuration
SECURE_CSP = {
    # Default: allow only same origin
    "default-src": ["'self'"],
    
    # Scripts: Tailwind, Lucide, Chart.js
    "script-src": [
        "'self'",
        "https://cdn.tailwindcss.com",
        "https://unpkg.com",
        "https://cdn.jsdelivr.net",
        "'unsafe-inline'",  # Required for Tailwind CDN and inline scripts
    ],
    
    # Styles: Tailwind CSS
    "style-src": [
        "'self'",
        "https://cdn.tailwindcss.com",
        "'unsafe-inline'",  # Required for Tailwind utility classes
    ],
    
    # Images: allow self, data URIs, and HTTPS images
    "img-src": [
        "'self'",
        "data:",
        "https:",
    ],
    
    # Fonts: allow self and data URIs
    "font-src": [
        "'self'",
        "data:",
    ],
    
    # AJAX/WebSocket connections
    "connect-src": [
        "'self'",
        "https://unpkg.com", 
        "https://cdn.jsdelivr.net",
    ],
    
    # Frames: prevent clickjacking
    "frame-ancestors": [
        "'none'",  # Same as X-Frame-Options: DENY
    ],
    
    # Base URI: restrict base tag
    "base-uri": [
        "'self'",
    ],
    
    # Form actions: only allow forms to submit to same origin
    "form-action": [
        "'self'",
    ],
    
    # Object/Embed: block plugins
    "object-src": [
        "'none'",
    ],
    
    # Media: block audio/video from external sources
    "media-src": [
        "'self'",
    ],
    
    # Worker scripts
    "worker-src": [
        "'self'",
    ],
    
    # Manifests (PWA)
    "manifest-src": [
        "'self'",
    ],
}

# ============================================
# APPLICATION DEFINITION
# ============================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'storages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'finance_app.urls'

# ============================================
# TEMPLATES
# ============================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # ← IMPORTANTE!
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

WSGI_APPLICATION = 'finance_app.wsgi.application'

# ============================================
# DATABASE
# ============================================

if os.getenv('DATABASE_URL'):
    # Production database (Supabase PostgreSQL)
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Development database (SQLite)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ============================================
# PASSWORD VALIDATION
# ============================================

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

# ============================================
# INTERNATIONALIZATION
# ============================================

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# ============================================
# STATIC FILES (CSS, JavaScript, Images)
# ============================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for serving static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================
# AUTHENTICATION
# ============================================

LOGIN_URL = 'core:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'core:login'

# Password reset settings
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour in seconds

# ============================================
# EMAIL CONFIGURATION
# ============================================

if os.getenv('RESEND_API_KEY'):
    # Production - Resend email service
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.resend.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'resend'
    EMAIL_HOST_PASSWORD = os.getenv('RESEND_API_KEY')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'SaveIt <onboarding@resend.dev>')
elif os.getenv('EMAIL_HOST_USER'):
    # Production - Custom SMTP
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'SaveIt <{EMAIL_HOST_USER}>')
else:
    # Development - Console backend (prints emails to console)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================
# SECURITY SETTINGS
# ============================================

# ============================================
# COOKIE SECURITY
# ============================================

# Session cookies
SESSION_COOKIE_HTTPONLY = True  # Non accessibile da JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'  # Protezione CSRF
SESSION_COOKIE_AGE = 1209600  # 2 settimane (in secondi)
SESSION_COOKIE_NAME = 'saveit_sessionid'  # Nome custom (opzionale)

# CSRF cookies
CSRF_COOKIE_HTTPONLY = True  # ✅ IMPORTANTE: blocca accesso JS
CSRF_COOKIE_SAMESITE = 'Lax'  # Protezione CSRF
CSRF_COOKIE_AGE = 31449600  # 1 anno
CSRF_COOKIE_NAME = 'saveit_csrftoken'  # Nome custom (opzionale)

# Additional security headers
X_FRAME_OPTIONS = 'DENY'  # Previene clickjacking
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# ============================================
# PRODUCTION-ONLY SECURITY
# ============================================

if not DEBUG:
    # Force HTTPS
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cookies only over HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ============================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ============================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================================================
# MEDIA FILES
# ============================================================

if os.environ.get('USE_S3', 'False') == 'True':
    # Supabase Storage (Production)
    AWS_ACCESS_KEY_ID = os.environ.get('SUPABASE_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('SUPABASE_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('SUPABASE_BUCKET_NAME', 'media')
    AWS_S3_ENDPOINT_URL = os.environ.get('SUPABASE_S3_ENDPOINT')
    AWS_S3_REGION_NAME = os.environ.get('SUPABASE_REGION', 'eu-west-1')
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False

    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

    MEDIA_URL = f"{os.environ.get('SUPABASE_S3_ENDPOINT')}/{os.environ.get('SUPABASE_BUCKET_NAME', 'media')}/"

else:
    # Local Development
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')