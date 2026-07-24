from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from app.engine import generate_response, generate_response_stream
from app.rag import add_documents

app = FastAPI(title="DeepakLLM API", version="1.0.0")

# Allow web apps like AskDeepakAI to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    client_id: str  # "echo", "askdeepakai", or "default"
    messages: List[Dict[str, str]]
    stream: bool = False
    use_rag: bool = True

class DocumentAddRequest(BaseModel):
    documents: List[str]
    metadatas: List[Dict[str, str]]
    ids: List[str]

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    try:
        if request.stream:
            # Return a streaming response
            stream_gen = generate_response_stream(request.client_id, request.messages, request.use_rag)
            return StreamingResponse(stream_gen, media_type="text/event-stream")
        else:
            # Return a standard JSON response
            response_text = generate_response(request.client_id, request.messages, request.use_rag)
            return {"choices": [{"message": {"role": "assistant", "content": response_text}}]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/knowledge/add")
async def add_knowledge(request: DocumentAddRequest):
    try:
        add_documents(request.documents, request.metadatas, request.ids)
        return {"status": "success", "message": f"Added {len(request.documents)} documents to DeepakLLM knowledge base."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "online", "model": "Llama 3 70B (Cloud-Backed)"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
