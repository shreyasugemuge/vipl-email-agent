"""Core views for VIPL Email Agent v2."""

import os
import time

from django.db import connection
from django.http import JsonResponse

_start_time = time.time()
VERSION = os.environ.get("APP_VERSION", "dev")


def health_check(request):
    """Health endpoint returning JSON with system status."""
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    status = {
        "status": "healthy" if db_ok else "degraded",
        "version": VERSION,
        "uptime_seconds": int(time.time() - _start_time),
        "database": "connected" if db_ok else "error",
    }
    status_code = 200 if db_ok else 503
    return JsonResponse(status, status=status_code)
