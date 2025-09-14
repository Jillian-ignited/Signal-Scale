# server.py  (repo root)
import os
import sys

# Ensure the repo root is on sys.path so "api.app.main" is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Optional: sanity log to confirm working dir in Render logs
print("[server] cwd:", os.getcwd())
print("[server] sys.path[0]:", sys.path[0])

# Import your FastAPI app
from api.app.main import app  # <-- do not change this if your app is in api/app/main.py
