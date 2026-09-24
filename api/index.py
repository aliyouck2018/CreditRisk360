"""Vercel serverless entrypoint (Flask WSGI app).

Kept minimal and import-safe: everything heavyweight happens at runtime,
not at import time.
"""
import os
import tempfile

# Serverless filesystems are read-only except /tmp — point Matplotlib's
# font/config cache there before anything imports matplotlib.
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "mpl"))
os.environ.setdefault("FLASK_DEBUG", "0")

from app import create_app  # noqa: E402

app = create_app()
