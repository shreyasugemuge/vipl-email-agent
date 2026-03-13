"""Gunicorn configuration for VIPL Email Agent v2."""

bind = "0.0.0.0:8000"
workers = 2  # Small app, shared VM -- keep low
threads = 2
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
