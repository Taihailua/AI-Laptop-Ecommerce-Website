from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import re
import unicodedata
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


def _normalize_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


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


def _extract_name_candidates(text: str) -> list[str]:
    patterns = [
        r"\*\*([^*]{2,80})\*\*",  # Markdown bold: **HP Pavilion 15**
        r"[\"“”]([^\"“”]{2,80})[\"“”]",  # Quoted product name
        r"\b(?:hp|dell|asus|lenovo|acer|msi|apple|macbook)\s+[^\n,.;:()]{1,40}\b",
    ]

    candidates: list[str] = []
    for pattern in patterns:
        for value in re.findall(pattern, text, flags=re.IGNORECASE):
            cleaned = re.sub(r"\s+", " ", value).strip(" .,-:")
            if len(cleaned) >= 3 and cleaned.lower() not in (c.lower() for c in candidates):
                candidates.append(cleaned)
    return candidates[:8]


def _build_recommendations_from_text(raw_text: str) -> list[RecommendedProduct]:
    normalized_text = _normalize_text(raw_text)
    if not normalized_text:
        return []

    candidates = _extract_name_candidates(raw_text)
    candidate_norms = [_normalize_text(c) for c in candidates]

    db = SessionLocal()
    try:
        products = crud.get_products(db, limit=200)
        recommendations: list[RecommendedProduct] = []

        for product in products:
            product_name_norm = _normalize_text(product.name)

            matched_in_text = product_name_norm in normalized_text
            matched_by_candidate = any(
                cand in product_name_norm or product_name_norm in cand for cand in candidate_norms
            )

            if not (matched_in_text or matched_by_candidate):
                continue

            recommendations.append(
                RecommendedProduct(
                    id=product.id,
                    name=product.name,
                    price=product.price,
                    image_url=product.image_url,
                )
            )

            if len(recommendations) >= 5:
                break

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

        # Fallback: nếu AI không trả ID, vẫn cố map theo tên sản phẩm trong câu user/AI.
        if not recommended_products:
            combined_text = f"{request.message}\n{ai_response}"
            recommended_products = _build_recommendations_from_text(combined_text)
        
        # Lưu lại vào lịch sử
        chat_history_store.add_message(request.session_id, "human", request.message)
        chat_history_store.add_message(request.session_id, "ai", ai_response)
        
        return ChatResponse(response=ai_response, recommended_products=recommended_products)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
