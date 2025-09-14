# server.py (repo root)
import os, sys
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from api.app.main import app  # import the FastAPI app
print("[server.py] ready")
