from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from . import chat_history_store # In-memory store for simplicity
from ..ai.agent import get_chat_response

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

@router.post("/", response_model=ChatResponse)
def chat_with_ai(request: ChatRequest):
    try:
        # Lấy lịch sử chat (giả lập lưu trong RAM cho demo)
        history = chat_history_store.get_history(request.session_id)
        
        # Lấy phản hồi từ AI
        ai_response = get_chat_response(request.message, chat_history=history)
        
        # Lưu lại vào lịch sử
        chat_history_store.add_message(request.session_id, "human", request.message)
        chat_history_store.add_message(request.session_id, "ai", ai_response)
        
        return ChatResponse(response=ai_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
