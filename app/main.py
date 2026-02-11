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
# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://youtube-qa-rag-bot.vercel.app", 
]

app.add_middleware(
    CORSMiddleware,
    # Option A (Secure): Use the origins list above
    allow_origins=origins, 
    
    # Option B (Fastest for testing): Use ["*"] to allow all domains
    # allow_origins=["*"], 
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------

app.include_router(transcript_router)

@app.get("/")
def root():
    return {"status": "API is running"}
