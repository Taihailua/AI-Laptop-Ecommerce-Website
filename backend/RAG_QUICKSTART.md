# 🚀 Quick Start - RAG cho Laptop Ecommerce

## ⚡ Bắt đầu trong 3 bước

### Bước 1: Cài đặt dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Bước 2: Seed vector database
```bash
python seed_vector_db.py
```
**Output:**
```
============================================================
SEEDING VECTOR DATABASE FOR RAG
============================================================
✅ Đã seed 15 sản phẩm vào vector database
📁 Embeddings được lưu trong folder: backend/chroma_db/
✅ Vector database seeding completed successfully!
```

### Bước 3: Chạy server
```bash
uvicorn app.main:app --reload
```

---

## 🧪 Kiểm tra xem RAG hoạt động không

```bash
python test_rag.py
```

---

## 🤖 Cách AI agent sử dụng RAG

### Trước (chỉ keyword search)
```
User: "Laptop gaming pin lâu RTX 3060 dưới 25 triệu"
AI: search_laptops("gaming") 
   ➜ ❌ Bỏ qua "pin lâu", "RTX 3060", "dưới 25 triệu"
```

### Sau (với RAG) ✨
```
User: "Laptop gaming pin lâu RTX 3060 dưới 25 triệu"
AI: semantic_search_laptops("Laptop gaming pin lâu RTX 3060 dưới 25 triệu")
   ➜ ✅ Hiểu toàn bộ yêu cầu, trả lại đúng sản phẩm
```

---

## 📝 Ví dụ sử dụng từ Python code

```python
from app.ai.rag import semantic_search_products

# Semantic search
query = "Laptop lập trình Python với RAM 16GB+"
results = semantic_search_products(query, top_k=5)

for product in results:
    print(f"{product['name']} - {product['price']:,.0f} VND")
    print(f"Độ phù hợp: {(1-product['relevance_score'])*100:.1f}%")
```

---

## 📚 Tài liệu chi tiết

Xem file: [RAG_GUIDE.md](RAG_GUIDE.md)

Gồm:
- ✅ Giới thiệu RAG chi tiết
- ✅ Cách hoạt động từng bước
- ✅ Ví dụ thực tế
- ✅ Troubleshooting
- ✅ Nâng cao

---

## 🎯 Khi nào dùng RAG?

### ✅ Dùng semantic_search_laptops khi:
- User mô tả chi tiết yêu cầu
- "Laptop gaming pin lâu RTX"
- "Máy coding Python RAM cao"
- "Laptop sinh viên vừa học vừa chơi game"

### ❌ Dùng search_laptops khi:
- User chỉ search keyword đơn
- "Laptop Dell"
- "Laptop i7"
- "Laptop dưới 20 triệu"

---

## 📊 Cứu cấp

### Vector database trống?
```bash
python seed_vector_db.py
```

### Muốn test RAG?
```bash
python test_rag.py
```

### Xem logs?
```bash
# Server sẽ print debug info
# Xem console khi gửi message
```

---

**🎉 RAG đã sẵn sàng! Bắt đầu chat với AI agent của bạn!**
