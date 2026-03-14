"""
Development settings for VIPL Email Agent v2.
Uses SQLite by default, or DATABASE_URL if set.
"""

import os

from dotenv import load_dotenv

from .base import *  # noqa: F401, F403

# Load .env file from project root
load_dotenv(BASE_DIR / ".env")

DEBUG = True

ALLOWED_HOSTS = ["*"]

INTERNAL_IPS = ["127.0.0.1", "::1"]

# Database: SQLite for local dev, or PostgreSQL via DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
