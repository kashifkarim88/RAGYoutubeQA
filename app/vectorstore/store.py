import logging
import time
import requests
import asyncio
import threading
import os
from typing import List, Union, Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from app.config.config import HF_TOKEN 

# --- Path Management for Render ---
# This ensures the database is created in the root of your project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

# --- Global Trackers ---
TASK_STATUS: Dict[str, dict] = {}
db_lock = threading.Lock() 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HuggingFaceInferenceEmbeddings(Embeddings):
    def __init__(self, api_key: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{self.model_name}/pipeline/feature-extraction"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _embed(self, texts: List[str]):
        payload = {"inputs": texts, "options": {"wait_for_model": True}}
        for attempt in range(5):
            try:
                response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=120)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [503, 429]:
                    time.sleep(10 if response.status_code == 503 else 5)
                else:
                    time.sleep(2)
            except Exception:
                time.sleep(2)
        return None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        for i in range(0, len(texts), 10):
            batch = texts[i:i + 10]
            embeddings = self._embed(batch)
            if embeddings:
                all_embeddings.extend(embeddings)
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        result = self._embed([text])
        return result[0] if result else []

# --- Initialize Vector Store with Absolute Path ---
embeddings_engine = HuggingFaceInferenceEmbeddings(api_key=HF_TOKEN)
vector_store = Chroma(
    collection_name="videoqa",
    embedding_function=embeddings_engine,
    persist_directory=CHROMA_PATH
)

# -----------------------------
# Storage Logic
# -----------------------------
def chunk_and_store(transcript: str, video_id: str, language: str = "en"):
    if not transcript:
        TASK_STATUS[video_id] = {"status": "error", "message": "Empty transcript"}
        return None

    with db_lock:
        try:
            TASK_STATUS[video_id] = {"status": "processing", "progress": 0}

            # --- STEP 1: CLEAR PREVIOUS DATA ---
            try:
                existing_data = vector_store.get()
                if existing_data["ids"]:
                    logger.info(f"Wiping vector store for fresh start...")
                    vector_store.delete(ids=existing_data["ids"])
            except Exception as e:
                logger.warning(f"Store clear skipped: {e}")

            # --- STEP 2: CHUNK NEW DATA ---
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=80)
            documents = splitter.create_documents(
                texts=[transcript],
                metadatas=[{"video_id": video_id, "language": language, "source": "youtube"}]
            )

            total_chunks = len(documents)
            batch_size = 10
            
            # --- STEP 3: STORE NEW DATA ---
            for i in range(0, total_chunks, batch_size):
                batch_docs = documents[i : i + batch_size]
                vector_store.add_documents(batch_docs)
                
                progress = min(int(((i + batch_size) / total_chunks) * 100), 100)
                TASK_STATUS[video_id]["progress"] = progress
                time.sleep(0.4)

            TASK_STATUS[video_id] = {"status": "completed", "progress": 100, "transcript": transcript}
            logger.info(f"✅ Video {video_id} indexed successfully at {CHROMA_PATH}")
            return documents

        except Exception as e:
            logger.error(f"❌ Storage failed: {e}")
            TASK_STATUS[video_id] = {"status": "failed", "error": str(e)}
            return None

def query_video_context(query: str, video_id: str, top_k: int = 4):
    if not query: return []
    try:
        retriever = vector_store.as_retriever(
            search_kwargs={
                "k": top_k,
                "filter": {"video_id": video_id}
            }
        )
        docs = retriever.invoke(query)
        return docs
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        return []
