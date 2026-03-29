from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, TIMESTAMP, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class OrderStatus(str, enum.Enum):
    PENDING = "Chờ xử lý"
    PROCESSING = "Đang giao"
    COMPLETED = "Hoàn thành"
    CANCELLED = "Hủy"

class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    STAFF = "Staff"


class TicketCategory(str, enum.Enum):
    PRODUCT_CONSULTATION = "Tu van san pham"
    ORDER_TRACKING = "Theo doi don hang"
    RETURN_REFUND = "Doi tra hoan tien"
    PAYMENT_ISSUE = "Van de thanh toan"
    TECHNICAL_SUPPORT = "Ho tro ky thuat"
    COMPLAINT = "Khieu nai"
    OTHER = "Khac"


class TicketStatus(str, enum.Enum):
    OPEN = "Moi"
    IN_PROGRESS = "Dang xu ly"
    RESOLVED = "Da giai quyet"
    CLOSED = "Da dong"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STAFF, nullable=False)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    brand = Column(String(100), index=True)
    specs = Column(JSON, nullable=True) # Lưu trữ cấu hình dưới dạng JSON (RAM, CPU, Cache...)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    image_url = Column(Text, nullable=True)
    
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    cccd = Column(String(20), unique=True, index=True, nullable=True) # Có thể nullable nếu khách chưa mua hàng
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    address = Column(Text, nullable=True)
    
    orders = relationship("Order", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    total_amount = Column(Float, default=0.0)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_at_time = Column(Float, nullable=False) # Giá của sản phẩm tại thời điểm mua
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    subject = Column(String(255), nullable=True)
    category = Column(Enum(TicketCategory), default=TicketCategory.OTHER, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    ai_summary = Column(Text, nullable=True)
    satisfaction_score = Column(Integer, nullable=True)
    satisfaction_note = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer", back_populates="tickets")
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")
    activities = relationship("TicketActivity", back_populates="ticket", cascade="all, delete-orphan")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="messages")


class TicketActivity(Base):
    __tablename__ = "ticket_activities"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    actor = Column(String(50), nullable=False, default="system")
    action = Column(String(50), nullable=False)
    old_status = Column(Enum(TicketStatus), nullable=True)
    new_status = Column(Enum(TicketStatus), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="activities")
