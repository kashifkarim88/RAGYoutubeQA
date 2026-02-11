import json
import requests
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from app.schemas.transcript_schema import TranscriptResponse
from app.services.youtube_service import get_video_transcript
from app.vectorstore.store import chunk_and_store, TASK_STATUS, query_video_context
from app.config.config import OPENROUTER_MODEL, OPENROUTER_API_KEY

router = APIRouter(prefix="/transcript", tags=["Transcript"])

@router.post("/", response_model=TranscriptResponse)
async def fetch_transcript(video_id: str, background_tasks: BackgroundTasks):
    try:
        # --- LOGIC CHANGE 1: Return the stored transcript if already completed ---
        existing_status = TASK_STATUS.get(video_id)
        if existing_status and existing_status.get("status") == "completed":
            return JSONResponse(
                status_code=200,
                content={
                    "video_id": video_id, 
                    "status": "completed", # Helpful to keep status consistent
                    "transcript": existing_status.get("transcript", ""), # Send the full saved text
                    "message": "Video already indexed. Ready for questions!"
                }
            )

        transcript = get_video_transcript(video_id)

        if not transcript or transcript.strip() == "":
            return JSONResponse(
                status_code=404,
                content={"video_id": video_id, "message": "No transcript available."}
            )
            
        background_tasks.add_task(chunk_and_store, transcript, video_id)

        return JSONResponse(
            status_code=200,
            content={
                "video_id": video_id,
                "transcript": transcript[:500] + "...", 
                "message": "Transcript retrieved. Processing embeddings..."
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"video_id": video_id, "message": f"Error: {str(e)}"}
        )

@router.get("/status/{video_id}")
async def get_task_status(video_id: str):
    status_info = TASK_STATUS.get(video_id, {"status": "not_started", "progress": 0})
    return JSONResponse(status_code=200, content=status_info)


@router.get("/ask")
async def ask_question(video_id: str, question: str):
    status_info = TASK_STATUS.get(video_id)
    
    # Check if processing is done
    if not status_info or status_info.get("status") != "completed":
        raise HTTPException(
            status_code=400, 
            detail="The video is still being indexed. Please wait for the progress bar to finish."
        )

    # Increase top_k to 5 for "smarter" depth
    relevant_docs = query_video_context(question, video_id, top_k=5)
    
    if not relevant_docs:
        return {
            "answer": "I couldn't find relevant information in this video's transcript.",
            "evidence": []
        }

    context_text = "\n\n".join([f"--- SEGMENT ---\n{doc.page_content}" for doc in relevant_docs])
    
    evidence_list = [
        {"content": doc.page_content, "metadata": doc.metadata} for doc in relevant_docs
    ]

    # API Configuration
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # SMARTER PROMPT DESIGN
    system_role = (
        "You are an expert technical educator. Use the provided transcript segments to provide "
        "a detailed, clear, and insightful answer. If the transcript uses analogies or examples, "
        "include them. If the answer isn't in the text, say you don't know."
    )
    
    prompt = f"""CONTEXT FROM VIDEO TRANSCRIPT:
{context_text}

USER QUESTION:
{question}

Helpful Answer:"""

    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_role},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4 # Slightly higher for more natural explanation
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        answer = response.json()['choices'][0]['message']['content']
        
        return {
            "video_id": video_id,
            "answer": answer,
            "evidence": evidence_list 
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI connection issue: {str(e)}")
