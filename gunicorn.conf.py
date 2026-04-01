# Gunicorn config for PropScope backend
import os

timeout = 300
keepalive = 5
workers = 1
threads = 4
worker_class = "gthread"
# Railway assigns PORT dynamically — must use it
bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
loglevel = "info"
