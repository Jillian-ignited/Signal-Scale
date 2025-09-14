# server.py — import shim so gunicorn/uvicorn can always find your app
import os, sys

# Ensure the repo root is on the import path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Now import the FastAPI app regardless of package quirks
# Adjust this line ONLY if your actual file path differs.
from api.app.main import app  # <-- if your app is at api/app/main.py

# Optional: quick visibility in Render logs
print("[server.py] cwd:", os.getcwd())
print("[server.py] sys.path head:", sys.path[:5])
