"""Core views for VIPL Email Agent v2."""

import os
import time

from django.db import connection
from django.http import JsonResponse
from django.utils import timezone

from datetime import timedelta

_start_time = time.time()
VERSION = os.environ.get("APP_VERSION", "dev")

# Scheduler heartbeat is considered stale after this many minutes
HEARTBEAT_STALE_MINUTES = 5


def health_check(request):
    """Health endpoint returning JSON with system status."""
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    overall_status = "healthy" if db_ok else "degraded"

    # Scheduler heartbeat check
    scheduler_status = "not_started"
    try:
        from apps.core.models import SystemConfig

        heartbeat_str = SystemConfig.get("scheduler_heartbeat")
        if heartbeat_str:
            from django.utils.dateparse import parse_datetime

            heartbeat_time = parse_datetime(heartbeat_str)
            if heartbeat_time:
                # Ensure timezone-aware comparison
                now = timezone.now()
                if heartbeat_time.tzinfo is None:
                    heartbeat_time = timezone.make_aware(heartbeat_time)
                delta = now - heartbeat_time
                if delta < timedelta(minutes=HEARTBEAT_STALE_MINUTES):
                    scheduler_status = "running"
                else:
                    scheduler_status = "stale"
                    overall_status = "degraded"
            else:
                scheduler_status = "stale"
                overall_status = "degraded"
        # else: no heartbeat ever written = scheduler not started (not degraded)
    except Exception:
        # SystemConfig table may not exist yet (before migrations)
        scheduler_status = "unknown"

    # Operating mode
    try:
        operating_mode = SystemConfig.get("operating_mode", "unknown")
    except Exception:
        operating_mode = "unknown"

    # Unauthenticated requests get minimal info only
    if not (request.user.is_authenticated and request.user.is_staff):
        minimal = {"status": overall_status}
        status_code = 200 if overall_status == "healthy" else 503
        return JsonResponse(minimal, status=status_code)

    status = {
        "status": overall_status,
        "version": VERSION,
        "mode": operating_mode,
        "uptime_seconds": int(time.time() - _start_time),
        "database": "connected" if db_ok else "error",
        "scheduler": scheduler_status,
    }
    status_code = 200 if overall_status == "healthy" else 503
    return JsonResponse(status, status=status_code)
