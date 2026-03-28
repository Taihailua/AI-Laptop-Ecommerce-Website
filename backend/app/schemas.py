from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from .models import OrderStatus, UserRole

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
