from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from .models import OrderStatus, UserRole, TicketCategory, TicketStatus

# ----------------- User -----------------
class UserBase(BaseModel):
    username: str
    role: UserRole = UserRole.STAFF

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ----------------- Product -----------------
class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    specs: Optional[Any] = None
    price: float
    stock_quantity: int = 0
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    name: Optional[str] = None
    price: Optional[float] = None

class ProductResponse(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ----------------- OrderItem -----------------
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    price_at_time: float
    product: ProductResponse
    model_config = ConfigDict(from_attributes=True)

# ----------------- Order -----------------
class OrderBase(BaseModel):
    status: OrderStatus = OrderStatus.PENDING

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    # Khi tạo order mới, frontend sẽ gửi thông tin khách hàng
    customer_cccd: Optional[str] = None
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = None

class OrderCustomerSummary(BaseModel):
    full_name: str
    phone_number: str
    address: Optional[str] = None
    cccd: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class OrderResponse(OrderBase):
    id: int
    customer_id: int
    total_amount: float
    created_at: datetime
    items: List[OrderItemResponse]
    customer: Optional[OrderCustomerSummary] = None
    model_config = ConfigDict(from_attributes=True)

# ----------------- Customer -----------------
class CustomerBase(BaseModel):
    cccd: Optional[str] = None
    full_name: str
    phone_number: str
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    orders: List[OrderResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ----------------- Ticket -----------------
class TicketMessageResponse(BaseModel):
    id: int
    role: str
    message: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TicketActivityResponse(BaseModel):
    id: int
    actor: str
    action: str
    old_status: Optional[TicketStatus] = None
    new_status: Optional[TicketStatus] = None
    note: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    session_id: str
    message: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None


class TicketCustomerSummary(BaseModel):
    id: int
    full_name: str
    phone_number: str
    address: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class TicketResponse(BaseModel):
    id: int
    session_id: str
    customer_id: Optional[int] = None
    subject: Optional[str] = None
    category: TicketCategory
    status: TicketStatus
    ai_summary: Optional[str] = None
    satisfaction_score: Optional[int] = None
    satisfaction_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    customer: Optional[TicketCustomerSummary] = None
    model_config = ConfigDict(from_attributes=True)


class TicketDetailResponse(TicketResponse):
    messages: List[TicketMessageResponse] = []
    activities: List[TicketActivityResponse] = []


class TicketSatisfactionCreate(BaseModel):
    score: int
    note: Optional[str] = None


class TicketSatisfactionSummary(BaseModel):
    total_rated_tickets: int
    average_score: float
    score_1: int
    score_2: int
    score_3: int
    score_4: int
    score_5: int


class TicketAdminUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None
    actor: str = "admin"


# ----------------- Support KB -----------------
class SupportKBArticle(BaseModel):
    id: str
    title: str
    category: str
    intents: List[str] = []
    keywords: List[str] = []
    guidance: List[str] = []
    required_fields: List[str] = []
    sla_target_hours: Optional[int] = None
    escalation_rule: str = ""
    handoff_when: List[str] = []
    customer_message_template: Optional[str] = None


class SupportKBPayload(BaseModel):
    version: str
    source: Optional[str] = None
    policy_notes: Optional[str] = None
    updated_at: Optional[str] = None
    policies: dict[str, Any] = {}
    articles: List[SupportKBArticle] = []


class SupportKBResponse(BaseModel):
    message: str = "ok"
    data: SupportKBPayload


class SupportKBReindexResponse(BaseModel):
    message: str
    article_count: int
    collection_name: str


class SupportKBContextPreviewResponse(BaseModel):
    query: str
    context: str
