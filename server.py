# server.py
import os, sys
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from api.app.main import app  # path to your FastAPI app
print("[server.py] ready")
