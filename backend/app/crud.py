from sqlalchemy.orm import Session, joinedload
from . import models, schemas
from passlib.context import CryptContext

from passlib.context import CryptContext
import json

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
def _is_product_paused(product: models.Product) -> bool:
    specs = product.specs if isinstance(product.specs, dict) else {}
    paused_flag = specs.get("__business_paused__", False)
    if isinstance(paused_flag, str):
        return paused_flag.strip().lower() in {"1", "true", "yes", "on"}
    return bool(paused_flag)


def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    include_paused: bool = False,
    specs_filter: str = None,
    sort_by_price: str = None,
):
    query = db.query(models.Product)
    if search and search.strip():  # Chỉ filter nếu search không rỗng
        query = query.filter(models.Product.name.ilike(f"%{search}%") | models.Product.brand.ilike(f"%{search}%"))

    products = query.all()
    if not include_paused:
        products = [p for p in products if not _is_product_paused(p)]

    if specs_filter:
        try:
            filters = json.loads(specs_filter)
            filtered_products = []
            for p in products:
                p_specs = dict(p.specs) if isinstance(p.specs, dict) else {}
                match = True
                for cat, values in filters.items():
                    if not values:
                        continue
                    cat_spec_val = p_specs.get(cat)
                    if not cat_spec_val:
                        match = False
                        break
                    # OR within the category
                    if not any(str(cat_spec_val).lower().strip() == str(v).lower().strip() for v in values):
                        match = False
                        break
                if match:
                    filtered_products.append(p)
            products = filtered_products
        except Exception:
            pass

    if sort_by_price == "asc":
        products.sort(key=lambda x: x.price)
    elif sort_by_price == "desc":
        products.sort(key=lambda x: x.price, reverse=True)

    start = max(skip, 0)
    if limit is None or limit < 0:
        return products[start:]
    return products[start:start + limit]

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
    return (
        db.query(models.Order)
        .options(
            joinedload(models.Order.customer),
            joinedload(models.Order.items).joinedload(models.OrderItem.product),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_order_by_phone(db: Session, phone_number: str):
    return (
        db.query(models.Order)
        .join(models.Customer)
        .options(
            joinedload(models.Order.customer),
            joinedload(models.Order.items).joinedload(models.OrderItem.product),
        )
        .filter(models.Customer.phone_number == phone_number)
        .all()
    )

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
    else:
        if order_data.customer_name and customer.full_name != order_data.customer_name:
            customer.full_name = order_data.customer_name
        if order_data.customer_address and customer.address != order_data.customer_address:
            customer.address = order_data.customer_address
    
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


# --- TICKET ---
def _get_or_create_customer_for_ticket(
    db: Session,
    customer_name: str | None,
    customer_phone: str | None,
    customer_address: str | None,
):
    if not customer_phone:
        return None

    customer = get_customer_by_phone(db, customer_phone)
    if customer:
        if customer_name and customer.full_name != customer_name:
            customer.full_name = customer_name
        if customer_address and customer.address != customer_address:
            customer.address = customer_address
        return customer

    customer = models.Customer(
        full_name=customer_name or "Khach hang",
        phone_number=customer_phone,
        address=customer_address,
    )
    db.add(customer)
    db.flush()
    return customer


def get_ticket_by_session_id(db: Session, session_id: str):
    return (
        db.query(models.Ticket)
        .options(
            joinedload(models.Ticket.messages),
            joinedload(models.Ticket.activities),
            joinedload(models.Ticket.customer),
        )
        .filter(models.Ticket.session_id == session_id)
        .first()
    )


def get_ticket(db: Session, ticket_id: int):
    return (
        db.query(models.Ticket)
        .options(
            joinedload(models.Ticket.messages),
            joinedload(models.Ticket.activities),
            joinedload(models.Ticket.customer),
        )
        .filter(models.Ticket.id == ticket_id)
        .first()
    )


def get_tickets_by_customer_phone(db: Session, phone_number: str, limit: int = 50):
    return (
        db.query(models.Ticket)
        .join(models.Customer, models.Ticket.customer_id == models.Customer.id)
        .options(
            joinedload(models.Ticket.messages),
            joinedload(models.Ticket.activities),
            joinedload(models.Ticket.customer),
        )
        .filter(models.Customer.phone_number == phone_number)
        .order_by(models.Ticket.created_at.desc())
        .limit(limit)
        .all()
    )


def get_all_tickets(db: Session, status: models.TicketStatus | None = None, limit: int = 200):
    query = (
        db.query(models.Ticket)
        .options(
            joinedload(models.Ticket.messages),
            joinedload(models.Ticket.activities),
            joinedload(models.Ticket.customer),
        )
        .order_by(models.Ticket.updated_at.desc())
    )
    if status is not None:
        query = query.filter(models.Ticket.status == status)
    return query.limit(limit).all()


def add_ticket_activity(
    db: Session,
    ticket_id: int,
    action: str,
    actor: str = "system",
    old_status: models.TicketStatus | None = None,
    new_status: models.TicketStatus | None = None,
    note: str | None = None,
):
    db_activity = models.TicketActivity(
        ticket_id=ticket_id,
        actor=actor,
        action=action,
        old_status=old_status,
        new_status=new_status,
        note=note,
    )
    db.add(db_activity)
    return db_activity


def create_ticket(
    db: Session,
    session_id: str,
    subject: str | None,
    category: models.TicketCategory,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    customer_address: str | None = None,
):
    customer = _get_or_create_customer_for_ticket(db, customer_name, customer_phone, customer_address)
    db_ticket = models.Ticket(
        session_id=session_id,
        customer_id=customer.id if customer else None,
        subject=subject,
        category=category,
        status=models.TicketStatus.OPEN,
    )
    db.add(db_ticket)
    db.flush()
    add_ticket_activity(
        db,
        ticket_id=db_ticket.id,
        action="ticket_created",
        actor="system",
        old_status=None,
        new_status=db_ticket.status,
        note="Ticket mới được tạo",
    )
    return db_ticket


def add_ticket_message(db: Session, ticket_id: int, role: str, message: str):
    db_message = models.TicketMessage(ticket_id=ticket_id, role=role, message=message)
    db.add(db_message)
    return db_message


def update_ticket_classification(
    db: Session,
    ticket: models.Ticket,
    category: models.TicketCategory,
    subject: str | None = None,
):
    ticket.category = category
    if subject:
        ticket.subject = subject
    return ticket


def update_ticket_status(db: Session, ticket: models.Ticket, status: models.TicketStatus):
    old_status = ticket.status
    ticket.status = status
    if old_status != status:
        add_ticket_activity(
            db,
            ticket_id=ticket.id,
            action="status_changed",
            actor="system",
            old_status=old_status,
            new_status=status,
            note="Cập nhật trạng thái từ hệ thống",
        )
    return ticket


def set_ticket_ai_summary(db: Session, ticket: models.Ticket, ai_summary: str | None):
    ticket.ai_summary = ai_summary
    return ticket


def rate_ticket_satisfaction(db: Session, ticket: models.Ticket, score: int, note: str | None):
    old_status = ticket.status
    ticket.satisfaction_score = score
    ticket.satisfaction_note = note
    if ticket.status != models.TicketStatus.CLOSED:
        ticket.status = models.TicketStatus.CLOSED
    add_ticket_activity(
        db,
        ticket_id=ticket.id,
        action="satisfaction_submitted",
        actor="customer",
        old_status=old_status,
        new_status=ticket.status,
        note=f"Đánh giá {score}/5" + (f" - {note}" if note else ""),
    )
    return ticket


def admin_update_ticket(
    db: Session,
    ticket: models.Ticket,
    status: models.TicketStatus | None,
    note: str | None,
    actor: str,
):
    old_status = ticket.status
    if status is not None:
        ticket.status = status

    add_ticket_activity(
        db,
        ticket_id=ticket.id,
        action="admin_updated_ticket",
        actor=actor or "admin",
        old_status=old_status,
        new_status=ticket.status,
        note=note,
    )
    return ticket


def get_ticket_satisfaction_summary(db: Session):
    rated_tickets = db.query(models.Ticket).filter(models.Ticket.satisfaction_score.is_not(None)).all()
    total = len(rated_tickets)
    counts = {i: 0 for i in range(1, 6)}

    for ticket in rated_tickets:
        if ticket.satisfaction_score in counts:
            counts[ticket.satisfaction_score] += 1

    average = 0.0
    if total > 0:
        average = sum(score * count for score, count in counts.items()) / total

    return {
        "total_rated_tickets": total,
        "average_score": round(average, 2),
        "score_1": counts[1],
        "score_2": counts[2],
        "score_3": counts[3],
        "score_4": counts[4],
        "score_5": counts[5],
    }
