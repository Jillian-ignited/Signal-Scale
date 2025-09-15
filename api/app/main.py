# api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import intelligence

app = FastAPI(title="Signal & Scale API", version="1.0.0")

# --- CORS: allow your frontend + local dev ---
ALLOWED_ORIGINS = [
    "https://signal-scale-frontend.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Mount your API routes under /api  (final path: /api/intelligence/analyze)
app.include_router(intelligence.router, prefix="/api")
