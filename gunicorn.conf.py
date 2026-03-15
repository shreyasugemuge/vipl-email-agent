"""Gunicorn configuration for VIPL Email Agent v2."""

bind = "0.0.0.0:8000"
workers = 2  # Small app, shared VM -- keep low
threads = 2
timeout = 30
max_requests = 1000  # Recycle workers to prevent memory leaks
max_requests_jitter = 50
worker_tmp_dir = "/dev/shm"  # tmpfs for faster heartbeat
accesslog = "-"
errorlog = "-"
loglevel = "info"
