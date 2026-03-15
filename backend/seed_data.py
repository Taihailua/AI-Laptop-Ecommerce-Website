import sys
import os
import bcrypt  # Use bcrypt directly to avoid passlib version issues

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.database import SessionLocal, engine, Base
    from app.models import Product, Customer, Order, OrderItem, OrderStatus, User, UserRole
except ImportError:
    # Fallback if run from parent directory or different context
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from app.database import SessionLocal, engine, Base
    from app.models import Product, Customer, Order, OrderItem, OrderStatus, User, UserRole

# Password hashing helper
def get_password_hash(password):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

def seed_data():
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(Product).count() > 0:
        print("Data already exists. Skipping seed.")
        db.close()
        return

    print("Seeding data...")

    # 1. Users (Admin & Staff)
    # Admin: admin / admin123
    admin_user = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN
    )
    # Staff: staff / staff123
    staff_user = User(
        username="staff",
        password_hash=get_password_hash("staff123"),
        role=UserRole.STAFF
    )
    db.add(admin_user)
    db.add(staff_user)

    # 2. Products (Laptops)
    products = [
        Product(
            name="MacBook Air M2 2022",
            brand="Apple",
            specs={"cpu": "Apple M2", "ram": "8GB", "storage": "256GB SSD", "screen": "13.6 inch Liquid Retina"},
            price=26990000,
            stock_quantity=10,
            image_url="https://cdn.tgdd.vn/Products/Images/44/282827/macbook-air-m2-2022-1-600x600.jpg"
        ),
        Product(
            name="Asus TUF Gaming F15",
            brand="Asus",
            specs={"cpu": "Intel Core i5 11400H", "ram": "8GB", "storage": "512GB SSD", "gpu": "RTX 3050", "screen": "15.6 inch 144Hz"},
            price=19990000,
            stock_quantity=15,
            image_url="https://cdn.tgdd.vn/Products/Images/44/273394/asus-tuf-gaming-fx506lhb-i5-hn188w-1-600x600.jpg"
        ),
        Product(
            name="Dell XPS 13 Plus 9320",
            brand="Dell",
            specs={"cpu": "Intel Core i7 1260P", "ram": "16GB", "storage": "512GB SSD", "screen": "13.4 inch OLED 3.5K"},
            price=45990000,
            stock_quantity=5,
            image_url="https://cdn.tgdd.vn/Products/Images/44/287768/dell-xps-13-plus-9320-i7-71003184-1-600x600.jpg"
        ),
        Product(
            name="HP Pavilion 15",
            brand="HP",
            specs={"cpu": "Intel Core i5 1235U", "ram": "8GB", "storage": "512GB SSD", "screen": "15.6 inch FHD"},
            price=14990000,
            stock_quantity=20,
            image_url="https://cdn.tgdd.vn/Products/Images/44/282367/hp-pavilion-15-eg2056tu-i5-6k786pa-1-600x600.jpg"
        ),
        Product(
            name="Lenovo Legion 5",
            brand="Lenovo",
            specs={"cpu": "AMD Ryzen 7 5800H", "ram": "16GB", "storage": "512GB SSD", "gpu": "RTX 3050Ti", "screen": "15.6 inch 165Hz"},
            price=24990000,
            stock_quantity=8,
            image_url="https://cdn.tgdd.vn/Products/Images/44/277123/lenovo-legion-5-15ach6-r7-82jw00klvn-1-600x600.jpg"
        ),
        Product(
            name="Acer Aspire 7 Gaming",
            brand="Acer",
            specs={"cpu": "AMD Ryzen 5 5500U", "ram": "8GB", "storage": "256GB SSD", "gpu": "GTX 1650", "screen": "15.6 inch 144Hz"},
            price=16490000,
            stock_quantity=12,
            image_url="https://cdn.tgdd.vn/Products/Images/44/264257/acer-aspire-7-gaming-a715-42g-r05g-r5-nhqaysv007-1-600x600.jpg"
        )
    ]
    
    for p in products:
        db.add(p)
    
    db.commit()

    # 3. Sample Customer
    customer = Customer(
        full_name="Nguyễn Văn A",
        phone_number="0901234567",
        cccd="079123456789",
        address="123 Đường Số 1, Quận 1, TP.HCM"
    )
    db.add(customer)
    db.commit()

    # 4. Sample Order
    # Get the first product (MacBook)
    product1 = db.query(Product).filter(Product.name == "MacBook Air M2 2022").first()

    order = Order(
        customer_id=customer.id,
        total_amount=product1.price * 1,
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()

    order_item = OrderItem(
        order_id=order.id,
        product_id=product1.id,
        quantity=1,
        price_at_time=product1.price
    )
    db.add(order_item)
    
    db.commit()
    print("Seed data created successfully!")
    db.close()

if __name__ == "__main__":
    init_db()
    seed_data()