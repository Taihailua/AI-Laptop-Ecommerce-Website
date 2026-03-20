"""
Script để seed vector database từ SQL database.
Chạy script này lần đầu hoặc khi muốn cập nhật embeddings.

Cách chạy:
    python seed_vector_db.py

Điều kiện tiên quyết:
    - DATABASE_URL trong .env được cấu hình đúng
    - Các dependencies trong requirements.txt đã được cài đặt
"""

import sys
import os
from sqlalchemy.exc import OperationalError

# Thêm đường dẫn của backend vào sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.ai.rag import seed_vector_database

if __name__ == "__main__":
    print("=" * 60)
    print("SEEDING VECTOR DATABASE FOR RAG")
    print("=" * 60)
    
    try:
        seed_vector_database()
        print("\n✅ Vector database seeding completed successfully!")
        print("📁 Embeddings được lưu trong folder: backend/chroma_db/")
    except OperationalError as e:
        print("\n❌ Không thể kết nối PostgreSQL để lấy dữ liệu sản phẩm.")
        print("Nguyên nhân thường gặp:")
        print("1) PostgreSQL chưa chạy")
        print("2) Sai host/port/user/password trong DATABASE_URL (.env)")
        print("3) Port DB đang khác (ví dụ script đang trỏ 5433)")
        print("\nCách xử lý nhanh:")
        print("- Mở PostgreSQL service/container")
        print("- Kiểm tra DATABASE_URL trong backend/.env")
        print("- Thử kết nối DB thủ công rồi chạy lại: python seed_vector_db.py")
        print(f"\nChi tiết lỗi: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
