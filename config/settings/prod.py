"""
Production settings for VIPL Email Agent v2.
Requires DATABASE_URL and SECRET_KEY environment variables.
"""

import os

import dj_database_url

from .base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Database from DATABASE_URL (required in production)
DATABASES = {
    "default": dj_database_url.config(conn_max_age=600),
}

# Security settings
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 28800  # 8 hours
SESSION_SAVE_EVERY_REQUEST = True
CSRF_TRUSTED_ORIGINS = [
    f"https://{host.strip()}"
    for host in ALLOWED_HOSTS
    if host.strip() and host.strip() != "localhost"
]

# Whitenoise static file serving (no manifest — prevents ValueError crashes
# when referenced files are missing; cache busting is unnecessary since we
# serve Tailwind/HTMX from CDN and only have a handful of static assets)
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
