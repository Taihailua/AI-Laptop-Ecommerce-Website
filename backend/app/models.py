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
