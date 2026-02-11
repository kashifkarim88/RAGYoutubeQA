from pydantic import BaseModel
from typing import List, Optional

class TranscriptRequest(BaseModel):
    video_id: str
    languages: List[str] = ["en"]

class TranscriptResponse(BaseModel):
    video_id: str
    transcript: Optional[str]
    message: str