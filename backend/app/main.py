from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # Add
from . import models
from .database import engine
import os # Add

# Tạo các bảng trong DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Laptop Ecommerce API")

# Mount upload folder
upload_dir = "uploads"
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)

app.mount("/static", StaticFiles(directory=upload_dir), name="static")

# Cấu hình CORS để cho phép Frontend từ Stitch gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Cho phép tất cả trên môi trường dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import products, orders, chat, auth

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Laptop Ecommerce API"}

app.include_router(products.router)
app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(auth.router)


