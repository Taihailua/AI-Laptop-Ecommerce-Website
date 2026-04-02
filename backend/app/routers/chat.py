from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional
import logging
import re
import unicodedata
import os
from uuid import uuid4
from sqlalchemy.orm import Session
from ..ai.agent import (
    get_chat_response,
    get_ticket_support_response,
    classify_ticket_with_llm,
    estimate_customer_satisfaction_from_history,
)
from ..database import SessionLocal, get_db
from .. import crud, models, schemas

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)

logger = logging.getLogger(__name__)

SATISFACTION_ASK_TEXT = (
    "Nếu bạn đã hài lòng với hỗ trợ vừa rồi, vui lòng đánh giá mức độ hài lòng từ 1-5 "
    "(ví dụ: 5 sao hoặc 4/5) để mình ghi nhận chất lượng dịch vụ."
)

ASSISTANT_OUT_OF_SCOPE_TEXT = (
    "Mình chỉ hỗ trợ các nội dung liên quan đến dịch vụ của TechShop như tư vấn laptop, "
    "giá/cấu hình, giỏ hàng, đặt hàng, theo dõi đơn và hỗ trợ ticket CSKH. "
    "Bạn hãy cho mình biết nhu cầu mua laptop hoặc vấn đề đơn hàng để mình hỗ trợ ngay nhé."
)

TICKET_OUT_OF_SCOPE_TEXT = (
    "Kênh này chỉ xử lý yêu cầu CSKH của TechShop (đơn hàng, thanh toán, đổi trả, bảo hành, "
    "kỹ thuật sản phẩm). Bạn vui lòng mô tả vấn đề liên quan đến dịch vụ của shop để mình hỗ trợ."
)

FEEDBACK_ASK_TEXT = (
    "Rất tiếc vì trải nghiệm của bạn chưa đạt mức tối đa. "
    "Bạn có thể chia sẻ thêm lý do hoặc góp ý cụ thể để TechShop cải thiện tốt hơn không ạ?"
)

class ChatRequest(BaseModel):
    session_id: str
    message: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None


class AssistantChatRequest(BaseModel):
    session_id: str
    message: str

class RecommendedProduct(BaseModel):
    id: int
    name: str
    price: float
    image_url: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    ticket_id: int
    category: models.TicketCategory
    status: models.TicketStatus
    recommended_products: list[RecommendedProduct] = Field(default_factory=list)


class AssistantChatResponse(BaseModel):
    response: str
    recommended_products: list[RecommendedProduct] = Field(default_factory=list)

class TicketAttachmentResponse(BaseModel):
    url: str
    mime_type: str
    size: int
    original_name: str

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_VIDEO_BYTES = 20 * 1024 * 1024

ALLOWED_ATTACHMENT_MIME = {
    "image/jpeg": ("jpg", MAX_IMAGE_BYTES),
    "image/png": ("png", MAX_IMAGE_BYTES),
    "image/webp": ("webp", MAX_IMAGE_BYTES),
    "video/mp4": ("mp4", MAX_VIDEO_BYTES),
}

ALLOWED_ATTACHMENT_EXT = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}

UPLOAD_TICKETS_DIR = os.path.join("uploads", "tickets")

PUBLIC_BASE_URL = "http://localhost:8000"

def _infer_extension_from_filename(filename: str | None) -> str:
    if not filename:
        return ""
    ext = os.path.splitext(filename)[1].lower()
    return ext

@router.post("/attachments", response_model=TicketAttachmentResponse)
async def upload_ticket_attachment(file: UploadFile = File(...)):
    try:
        if not file:
            raise HTTPException(status_code=400, detail="Chưa có file được upload.")

        content_type = (file.content_type or "").lower()
        ext = _infer_extension_from_filename(file.filename)

        if ext and ext not in ALLOWED_ATTACHMENT_EXT:
            raise HTTPException(
                status_code=400,
                detail="Định dạng file không hợp lệ. Chỉ hỗ trợ jpg/png/webp và mp4.",
            )

        if content_type not in ALLOWED_ATTACHMENT_MIME:
            # Nếu browser gửi content_type không chuẩn, fallback theo extension
            if ext in {".jpg", ".jpeg", ".png", ".webp"}:
                content_type = "image/jpeg" if ext in {".jpg", ".jpeg"} else (
                    "image/png" if ext == ".png" else "image/webp"
                )
            elif ext == ".mp4":
                content_type = "video/mp4"
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Định dạng file không hợp lệ. Chỉ hỗ trợ jpg/png/webp và mp4.",
                )

        _, max_size = ALLOWED_ATTACHMENT_MIME[content_type]
        # UploadFile.size có thể không có sẵn; dùng read() để xác định size chắc chắn.
        data = await file.read()
        size = len(data or b"")

        if size <= 0:
            raise HTTPException(status_code=400, detail="File upload rỗng hoặc không hợp lệ.")

        if size > max_size:
            if content_type.startswith("image/"):
                raise HTTPException(status_code=413, detail="Ảnh vượt quá dung lượng tối đa 5MB.")
            raise HTTPException(status_code=413, detail="Video vượt quá dung lượng tối đa 20MB.")

        os.makedirs(UPLOAD_TICKETS_DIR, exist_ok=True)

        # Giữ phần đuôi theo mime (tránh lệch ext nếu browser đặt sai)
        expected_ext = ALLOWED_ATTACHMENT_MIME[content_type][0]
        saved_filename = f"{uuid4().hex}.{expected_ext}"
        saved_path = os.path.join(UPLOAD_TICKETS_DIR, saved_filename)

        try:
            with open(saved_path, "wb") as f:
                f.write(data)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi ghi file upload: {str(e)}")

        url = f"{PUBLIC_BASE_URL}/static/tickets/{saved_filename}"
        return TicketAttachmentResponse(
            url=url,
            mime_type=content_type,
            size=size,
            original_name=file.filename or "",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi upload file: {str(e)}")


def _history_from_ticket(ticket: models.Ticket) -> list[tuple[str, str]]:
    sorted_messages = sorted(ticket.messages, key=lambda m: (m.created_at, m.id))
    return [(msg.role, msg.message) for msg in sorted_messages if msg.role in {"human", "ai"}]


def _latest_ai_satisfaction_note(ticket: models.Ticket) -> str | None:
    activities = sorted(ticket.activities, key=lambda a: (a.created_at, a.id), reverse=True)
    for activity in activities:
        if activity.action == "ai_satisfaction_assessed":
            return activity.note
    return None


def _auto_assess_ticket_satisfaction(db: Session, ticket: models.Ticket) -> None:
    # Skip auto-assessment when customer has already provided explicit rating.
    if ticket.satisfaction_score is not None:
        return

    # Keep only one AI auto-assessment entry per ticket to avoid noisy duplicate logs.
    if _latest_ai_satisfaction_note(ticket) is not None:
        return

    history = _history_from_ticket(ticket)
    if len(history) < 4:
        return

    score, reason = estimate_customer_satisfaction_from_history(history)
    note = f"Mức độ hài lòng ước lượng: {score}/5. Lý do: {reason}"

    crud.add_ticket_activity(
        db,
        ticket_id=ticket.id,
        action="ai_satisfaction_assessed",
        actor="ai",
        old_status=ticket.status,
        new_status=ticket.status,
        note=note,
    )


def _category_from_code(category_code: str) -> models.TicketCategory:
    if category_code in models.TicketCategory.__members__:
        return models.TicketCategory[category_code]
    return models.TicketCategory.OTHER


def _status_from_any(status_value: str | None) -> models.TicketStatus | None:
    if status_value is None:
        return None

    raw = str(status_value).strip()
    if not raw:
        return None

    if raw in models.TicketStatus.__members__:
        return models.TicketStatus[raw]

    for status in models.TicketStatus:
        if raw.lower() == status.value.lower():
            return status

    return None


def _normalize_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def _is_greeting(normalized_text: str) -> bool:
    if not normalized_text:
        return False
    greetings = [
        "xin chao",
        "chao",
        "hello",
        "hi",
        "hey",
        "alo",
        "ad oi",
        "shop oi",
    ]
    return normalized_text in greetings


def _is_service_related_message(message: str) -> bool:
    normalized = _normalize_text(message or "")
    if not normalized:
        return False

    if _is_greeting(normalized):
        return True

    service_keywords = [
        "laptop",
        "may tinh",
        "mua",
        "muon mua",
        "dat mua",
        "chon",
        "mau nay",
        "model nay",
        "san pham nay",
        "lay mau nay",
        "san pham",
        "cau hinh",
        "cpu",
        "gpu",
        "ram",
        "ssd",
        "man hinh",
        "gaming",
        "do hoa",
        "van phong",
        "gia",
        "ngan sach",
        "trieu",
        "vnd",
        "khuyen mai",
        "gio hang",
        "dat hang",
        "checkout",
        "thanh toan",
        "don hang",
        "ma don",
        "van chuyen",
        "giao hang",
        "bao hanh",
        "doi tra",
        "hoan tien",
        "ho tro",
        "van de",
        "su co",
        "loi",
        "hong",
        "khong len",
        "khong hoat dong",
        "khong dung duoc",
        "ticket",
        "cskh",
        "techshop",
        "legion",
        "tuf",
        "aspire",
        "thinkpad",
        "vivobook",
        "rog",
        "macbook",
        "dell",
        "hp",
        "lenovo",
        "asus",
        "acer",
        "msi",
    ]

    if any(keyword in normalized for keyword in service_keywords):
        return True

    return bool(re.search(r"\b\d+\s*(trieu|k|nghin|vnd|d)\b", normalized))


def _already_asked_satisfaction(history: list[tuple[str, str]]) -> bool:
    key = "đánh giá mức độ hài lòng"
    for role, content in history:
        if role == "ai" and key in (content or "").lower():
            return True
    return False


def _ai_asked_feedback(history: list[tuple[str, str]]) -> bool:
    prompts = [
        "chia sẻ thêm lý do",
        "góp ý cụ thể",
        "cải thiện tốt hơn",
    ]
    for role, content in reversed(history):
        if role != "ai":
            continue
        lowered = (content or "").lower()
        return any(p in lowered for p in prompts)
    return False


def _looks_like_feedback_message(message: str) -> bool:
    normalized = _normalize_text(message or "")
    if not normalized:
        return False

    # Neu khach dang hoi tiep ho tro, uu tien xu ly nhu ticket thong thuong.
    support_signals = ["bao hanh", "don hang", "thanh toan", "doi tra", "ho tro", "khieu nai", "loi"]
    if any(k in normalized for k in support_signals):
        return False

    feedback_signals = [
        "gop y",
        "ly do",
        "vi ",
        "cham",
        "thai do",
        "chua hai long",
        "can cai thien",
        "trai nghiem",
        "nhan vien",
    ]
    return len(normalized) >= 12 or any(k in normalized for k in feedback_signals)


def _extract_satisfaction_score(message: str) -> int | None:
    text = (message or "").strip().lower()
    normalized = _normalize_text(text)

    for pattern in [r"\b([1-5])\s*/\s*5\b", r"\b([1-5])\s*(?:sao|star|diem)\b"]:
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))

    if any(k in normalized for k in ["danh gia", "hai long", "sao", "diem"]):
        raw_digit = re.search(r"\b([1-5])\b", normalized)
        if raw_digit:
            return int(raw_digit.group(1))

    if "rat khong hai long" in normalized:
        return 1
    if "rat hai long" in normalized:
        return 5
    if "khong hai long" in normalized:
        return 2
    if "binh thuong" in normalized:
        return 3
    if "hai long" in normalized:
        return 4

    return None


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


@router.post("/assistant", response_model=AssistantChatResponse)
def chat_assistant(request: AssistantChatRequest):
    """
    AI chat for product consultation only.
    This endpoint intentionally does not create ticket records.
    """
    try:
        normalized = _normalize_text(request.message)
        if _is_greeting(normalized):
            return AssistantChatResponse(
                response=(
                    "Chào bạn! Mình hỗ trợ tư vấn laptop theo nhu cầu/ngân sách, "
                    "so sánh cấu hình, và hướng dẫn đặt hàng tại TechShop."
                ),
                recommended_products=[],
            )

        ai_response = get_chat_response(request.message)
        recommended_products = _build_recommendations_from_response(ai_response)

        if not recommended_products:
            combined_text = f"{request.message}\n{ai_response}"
            recommended_products = _build_recommendations_from_text(combined_text)

        return AssistantChatResponse(response=ai_response, recommended_products=recommended_products)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=ChatResponse)
def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        normalized = _normalize_text(request.message)
        if _is_greeting(normalized):
            return ChatResponse(
                response=(
                    "Chào bạn! Kênh này hỗ trợ CSKH TechShop về đơn hàng, thanh toán, đổi trả, "
                    "bảo hành và sự cố sản phẩm. Bạn mô tả vấn đề để mình hỗ trợ ngay nhé."
                ),
                ticket_id=0,
                category=models.TicketCategory.OTHER,
                status=models.TicketStatus.OPEN,
                recommended_products=[],
            )

        ticket = crud.get_ticket_by_session_id(db, request.session_id)

        # Allow concise follow-up messages once a ticket session already exists.
        if ticket is None and not _is_service_related_message(request.message):
            return ChatResponse(
                response=TICKET_OUT_OF_SCOPE_TEXT,
                ticket_id=0,
                category=models.TicketCategory.OTHER,
                status=models.TicketStatus.OPEN,
                recommended_products=[],
            )

        if not ticket:
            category_code, subject = classify_ticket_with_llm(request.message)
            category = _category_from_code(category_code)
            ticket = crud.create_ticket(
                db=db,
                session_id=request.session_id,
                subject=subject,
                category=category,
                customer_name=request.customer_name,
                customer_phone=request.customer_phone,
                customer_address=request.customer_address,
            )

        history = _history_from_ticket(ticket)
        recommended_products: list[RecommendedProduct] = []
        score = _extract_satisfaction_score(request.message)

        # Khach tra loi diem danh gia qua chat, he thong tu dong ghi nhan.
        if score is not None and ticket.satisfaction_score is None:
            crud.add_ticket_message(db, ticket_id=ticket.id, role="human", message=request.message)
            crud.rate_ticket_satisfaction(db, ticket, score, request.message.strip()[:240])
            if score <= 3:
                ai_response = (
                    f"Cảm ơn bạn đã đánh giá {score}/5 cho ticket #{ticket.id}. "
                    f"{FEEDBACK_ASK_TEXT}"
                )
            else:
                ai_response = (
                    f"Cảm ơn bạn đã đánh giá {score}/5 cho ticket #{ticket.id}. "
                    "Mình đã ghi nhận phản hồi để cải thiện chất lượng CSKH."
                )
            crud.add_ticket_message(db, ticket_id=ticket.id, role="ai", message=ai_response)
            crud.set_ticket_ai_summary(db, ticket, ai_response[:300])
            db.commit()
            db.refresh(ticket)

            return ChatResponse(
                response=ai_response,
                ticket_id=ticket.id,
                category=ticket.category,
                status=ticket.status,
                recommended_products=recommended_products,
            )

        if ticket.satisfaction_score is not None and _ai_asked_feedback(history) and _looks_like_feedback_message(request.message):
            crud.add_ticket_message(db, ticket_id=ticket.id, role="human", message=request.message)
            crud.add_ticket_activity(
                db,
                ticket_id=ticket.id,
                action="customer_feedback",
                actor="customer",
                old_status=ticket.status,
                new_status=ticket.status,
                note=request.message.strip()[:500],
            )
            ai_response = (
                "Cảm ơn bạn đã chia sẻ góp ý. Mình đã ghi nhận để đội CSKH cải thiện quy trình hỗ trợ tốt hơn."
            )
            crud.add_ticket_message(db, ticket_id=ticket.id, role="ai", message=ai_response)
            crud.set_ticket_ai_summary(db, ticket, ai_response[:300])
            db.commit()
            db.refresh(ticket)
            return ChatResponse(
                response=ai_response,
                ticket_id=ticket.id,
                category=ticket.category,
                status=ticket.status,
                recommended_products=recommended_products,
            )

        ai_response = get_ticket_support_response(request.message, chat_history=history)

        should_ask_satisfaction = (
            ticket.satisfaction_score is None
            and len(history) >= 2
            and not _already_asked_satisfaction(history)
        )
        if should_ask_satisfaction:
            ai_response = f"{ai_response}\n\n{SATISFACTION_ASK_TEXT}"

        crud.add_ticket_message(db, ticket_id=ticket.id, role="human", message=request.message)
        crud.add_ticket_message(db, ticket_id=ticket.id, role="ai", message=ai_response)

        if ticket.status == models.TicketStatus.OPEN:
            crud.update_ticket_status(db, ticket, models.TicketStatus.IN_PROGRESS)
        crud.set_ticket_ai_summary(db, ticket, ai_response[:300])

        db.commit()
        db.refresh(ticket)

        try:
            _auto_assess_ticket_satisfaction(db, ticket)
            db.commit()
            db.refresh(ticket)
        except Exception as auto_err:
            db.rollback()
            logger.exception("Auto AI satisfaction assessment failed for ticket %s: %s", ticket.id, auto_err)

        return ChatResponse(
            response=ai_response,
            ticket_id=ticket.id,
            category=ticket.category,
            status=ticket.status,
            recommended_products=recommended_products,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets/by-phone/{phone_number}", response_model=list[schemas.TicketResponse])
def get_customer_tickets(phone_number: str, db: Session = Depends(get_db)):
    return crud.get_tickets_by_customer_phone(db, phone_number=phone_number)


@router.get("/tickets/summary/satisfaction", response_model=schemas.TicketSatisfactionSummary)
def get_satisfaction_summary(db: Session = Depends(get_db)):
    return crud.get_ticket_satisfaction_summary(db)


@router.get("/tickets/{ticket_id}", response_model=schemas.TicketDetailResponse)
def get_ticket_detail(ticket_id: int, db: Session = Depends(get_db)):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket khong ton tai")
    return ticket


@router.get("/admin/tickets", response_model=list[schemas.TicketDetailResponse])
def admin_get_tickets(status: Optional[str] = None, db: Session = Depends(get_db)):
    parsed_status = _status_from_any(status)
    return crud.get_all_tickets(db, status=parsed_status)


@router.patch("/admin/tickets/{ticket_id}", response_model=schemas.TicketDetailResponse)
def admin_update_ticket(ticket_id: int, payload: schemas.TicketAdminUpdate, db: Session = Depends(get_db)):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket khong ton tai")

    parsed_status = _status_from_any(payload.status)
    if payload.status is not None and parsed_status is None:
        raise HTTPException(status_code=400, detail="Status khong hop le")

    if parsed_status is None and not (payload.note and payload.note.strip()):
        raise HTTPException(status_code=400, detail="Can cap nhat status hoac note")

    crud.admin_update_ticket(
        db,
        ticket=ticket,
        status=parsed_status,
        note=(payload.note or "").strip() or None,
        actor=(payload.actor or "admin").strip() or "admin",
    )
    db.commit()
    db.refresh(ticket)
    return crud.get_ticket(db, ticket_id)


@router.post("/tickets/{ticket_id}/satisfaction", response_model=schemas.TicketResponse)
def rate_ticket(ticket_id: int, payload: schemas.TicketSatisfactionCreate, db: Session = Depends(get_db)):
    if payload.score < 1 or payload.score > 5:
        raise HTTPException(status_code=400, detail="Diem danh gia phai tu 1 den 5")

    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket khong ton tai")

    crud.rate_ticket_satisfaction(db, ticket, payload.score, payload.note)
    db.commit()
    db.refresh(ticket)
    return ticket
