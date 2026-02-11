from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.transcript import router as transcript_router

app = FastAPI(
    title="YouTube Transcript API",
    description="Extract YouTube video transcripts for Q&A apps",
    version="1.0.0"
)

# --- CORS Configuration ---
# This allows your Next.js frontend to communicate with this API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # Allows headers like Content-Type
)
# ---------------------------

app.include_router(transcript_router)

@app.get("/")
def root():
    return {"status": "API is running"}
