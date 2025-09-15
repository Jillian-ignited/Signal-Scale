# api/app/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import your router
from .routers import intelligence

# Create FastAPI instance
app = FastAPI(
    title="Signal & Scale API",
    version="1.0.0",
)

# Allow cross-origin requests (frontend ↔ backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(intelligence.router)

@app.get("/healthz")
def health():
    return {"status": "ok", "cwd": os.getcwd()}

