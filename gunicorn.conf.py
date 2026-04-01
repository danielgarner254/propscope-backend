# Gunicorn config for PropScope backend
# Extended timeout to handle long Claude + web search requests

timeout = 300          # 5 minutes - handles Claude with multiple web searches
keepalive = 5          # keep connections alive
workers = 1            # single worker on free tier
threads = 4            # threads handle concurrent requests within the worker
worker_class = "gthread"
bind = "0.0.0.0:8000"
loglevel = "info"
