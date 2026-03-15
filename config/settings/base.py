"""
Base Django settings for VIPL Email Agent v2.
Shared across dev and prod environments.
"""

import os
from pathlib import Path

# Build paths: BASE_DIR is the project root (vipl-email-agent/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-dev-only-change-in-production",
)

DEBUG = False  # Overridden in dev.py

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "django_htmx",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Project apps
    "apps.core",
    "apps.accounts",
    "apps.emails",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.user_permissions",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database -- overridden in dev.py and prod.py
DATABASES = {}

# Custom user model -- MUST be set before first migration
AUTH_USER_MODEL = "accounts.User"

# Auth URLs
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/emails/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # Password auth (superuser fallback)
    "allauth.account.auth_backends.AuthenticationBackend",  # allauth
]

# allauth settings
ACCOUNT_EMAIL_VERIFICATION = "none"  # No email verification loop
ACCOUNT_LOGIN_METHODS = {"username"}  # Keep username-based password login working
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_SIGNUP_ENABLED = False  # No manual signup — Google SSO only
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False  # SECURITY: prevent email-matching auto-connect
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = False  # Require POST to prevent login CSRF
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.VIPLSocialAccountAdapter"
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email", "openid"],
        "AUTH_PARAMS": {
            "access_type": "online",
            "hd": "vidarbhainfotech.com",  # UI hint only -- enforced server-side in adapter
        },
        "OAUTH_PKCE_ENABLED": True,
        "APP": {
            "client_id": os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "placeholder"),
            "secret": os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        },
    }
}
SOCIALACCOUNT_STORE_TOKENS = False  # We don't need access tokens after login
