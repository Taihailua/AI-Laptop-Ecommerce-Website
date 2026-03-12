from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import re
from . import chat_history_store # In-memory store for simplicity
from ..ai.agent import get_chat_response
from ..database import SessionLocal
from .. import crud

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class RecommendedProduct(BaseModel):
    id: int
    name: str
    price: float
    image_url: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    recommended_products: list[RecommendedProduct] = []


def _extract_product_ids(ai_response: str) -> list[int]:
    # Hỗ trợ nhiều định dạng: [ID: 3], ID 3, mã 3, #3
    patterns = [
        r"\bID\s*[:#-]?\s*(\d+)\b",
        r"\bmã\s*(?:sản\s*phẩm)?\s*[:#-]?\s*(\d+)\b",
        r"#(\d+)\b",
    ]

    found: list[int] = []
    for pattern in patterns:
        found.extend(int(m) for m in re.findall(pattern, ai_response, flags=re.IGNORECASE))

    # Loại trùng, giữ thứ tự xuất hiện
    unique_ids: list[int] = []
    for pid in found:
        if pid not in unique_ids:
            unique_ids.append(pid)
    return unique_ids[:5]


def _build_recommendations_from_response(ai_response: str) -> list[RecommendedProduct]:
    product_ids = _extract_product_ids(ai_response)
    if not product_ids:
        return []

    db = SessionLocal()
    try:
        recommendations: list[RecommendedProduct] = []
        for pid in product_ids:
            product = crud.get_product(db, pid)
            if not product:
                continue
            recommendations.append(
                RecommendedProduct(
                    id=product.id,
                    name=product.name,
                    price=product.price,
                    image_url=product.image_url,
                )
            )
        return recommendations
    finally:
        db.close()

@router.post("/", response_model=ChatResponse)
def chat_with_ai(request: ChatRequest):
    try:
        # Lấy lịch sử chat (giả lập lưu trong RAM cho demo)
        history = chat_history_store.get_history(request.session_id)
        
        # Lấy phản hồi từ AI
        ai_response = get_chat_response(request.message, chat_history=history)
        recommended_products = _build_recommendations_from_response(ai_response)
        
        # Lưu lại vào lịch sử
        chat_history_store.add_message(request.session_id, "human", request.message)
        chat_history_store.add_message(request.session_id, "ai", ai_response)
        
        return ChatResponse(response=ai_response, recommended_products=recommended_products)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
