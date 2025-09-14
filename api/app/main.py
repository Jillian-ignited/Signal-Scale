# api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.intelligence import router as intelligence_router

app = FastAPI(
    title="Signal & Scale API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Allow your Render frontend + localhost
ALLOWED_ORIGINS = [
    "https://signal-scale-frontend.onrender.com",
    "https://signal-scale.onrender.com",
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
def health():
    return {"status": "ok"}

# Mount your API under /api
app.include_router(intelligence_router, prefix="/api")
