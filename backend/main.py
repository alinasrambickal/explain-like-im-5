# main.py
import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import explain

app = FastAPI(title="ELI5 Backend")

# --- CORS ---
# Only allow requests from your specific Chrome extension
# Replace YOUR_EXTENSION_ID with the actual ID from chrome://extensions
EXTENSION_ID = os.getenv("EXTENSION_ID", "YOUR_EXTENSION_ID")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"chrome-extension://{EXTENSION_ID}"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# --- Routes ---
app.include_router(explain.router)


@app.get("/health")
def health():
    return {"status": "ok"}
