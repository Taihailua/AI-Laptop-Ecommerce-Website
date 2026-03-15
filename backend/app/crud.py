from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# --- USER ---
def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        password_hash=get_password_hash(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

# --- PRODUCT ---
def get_products(db: Session, skip: int = 0, limit: int = 100, search: str = None):
    query = db.query(models.Product)
    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%") | models.Product.brand.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()

def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# --- CUSTOMER ---
def get_customer_by_phone(db: Session, phone_number: str):
    return db.query(models.Customer).filter(models.Customer.phone_number == phone_number).first()

def create_customer(db: Session, customer: schemas.CustomerCreate):
    db_customer = models.Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

# --- ORDER ---
def get_orders(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Order).offset(skip).limit(limit).all()

def get_order_by_phone(db: Session, phone_number: str):
    return db.query(models.Order).join(models.Customer).filter(models.Customer.phone_number == phone_number).all()

def create_order(db: Session, order_data: schemas.OrderCreate):
    # Tìm hoặc tạo khách hàng
    customer = get_customer_by_phone(db, order_data.customer_phone)
    if not customer:
        customer = models.Customer(
            cccd=order_data.customer_cccd,
            full_name=order_data.customer_name,
            phone_number=order_data.customer_phone,
            address=order_data.customer_address
        )
        db.add(customer)
        db.flush() # Lấy ID để dùng cho Order
    
    # Tạo order
    db_order = models.Order(customer_id=customer.id)
    db.add(db_order)
    db.flush()
    
    total_amount = 0
    # Thêm items
    for item in order_data.items:
        product = get_product(db, item.product_id)
        if product and product.stock_quantity >= item.quantity:
            price_at_time = product.price
            db_order_item = models.OrderItem(
                order_id=db_order.id,
                product_id=product.id,
                quantity=item.quantity,
                price_at_time=price_at_time
            )
            db.add(db_order_item)
            # Trừ stock (trong thực tế có thể handle async/rollback)
            product.stock_quantity -= item.quantity
            total_amount += price_at_time * item.quantity
            
    db_order.total_amount = total_amount
    db.commit()
    db.refresh(db_order)
    return db_order
