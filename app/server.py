import os
import shutil
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional
from pydantic import BaseModel
import uvicorn

# Import the existing engine
from app.engine import generate_response
from app.database import create_chat, list_chats, get_chat_messages, add_message, update_chat_title, delete_chat

app = FastAPI()

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

class ChatRequest(BaseModel):
    chat_id: str
    prompt: str
    persona: str = "deepakllm"

class NewChatRequest(BaseModel):
    title: str = "New Chat"

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open(os.path.join(frontend_dir, "index.html"), "r") as f:
        return f.read()

@app.get("/api/chats")
async def get_chats():
    chats = list_chats()
    return {"chats": chats}

@app.post("/api/chats")
async def create_new_chat(req: NewChatRequest):
    chat_id = create_chat(req.title)
    return {"chat_id": chat_id, "title": req.title}

@app.get("/api/chats/{chat_id}")
async def get_chat_history(chat_id: str):
    messages = get_chat_messages(chat_id)
    return {"messages": messages}

@app.delete("/api/chats/{chat_id}")
async def remove_chat(chat_id: str):
    delete_chat(chat_id)
    return {"status": "success"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Simple sanitization
    filename = os.path.basename(file.filename)
    file_path = os.path.join(uploads_dir, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Make sure absolute path is available for Python script
    return {"filename": filename, "path": os.path.abspath(file_path)}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    print(f"Received chat request: {request.prompt} for chat: {request.chat_id} persona: {request.persona}")
    try:
        # Check if title needs updating
        history = get_chat_messages(request.chat_id)
        if len(history) == 0:
            title = request.prompt[:30] + ("..." if len(request.prompt) > 30 else "")
            update_chat_title(request.chat_id, title)
            
        # Add user message to DB
        add_message(request.chat_id, "user", request.prompt)
        
        # Get full history for the LLM
        messages = get_chat_messages(request.chat_id)
        
        # Call the existing RAG engine with full message history
        response_text = generate_response(
            client_id=request.persona, 
            messages=messages
        )
        
        # Add AI message to DB
        add_message(request.chat_id, "assistant", response_text)
        
        return {"response": response_text}
    except Exception as e:
        print(f"Error during generation: {e}")
        return {"response": f"Sorry, an error occurred on the backend: {str(e)}"}

if __name__ == "__main__":
    print("Starting AskDeepakAI Server on http://localhost:8000")
    uvicorn.run("app.server:app", host="0.0.0.0", port=8000, reload=True)
