"""
Production settings for VIPL Email Agent v2.
Requires DATABASE_URL and SECRET_KEY environment variables.
"""

import os

import dj_database_url

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Database from DATABASE_URL (required in production)
DATABASES = {
    "default": dj_database_url.config(conn_max_age=600),
}

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
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
