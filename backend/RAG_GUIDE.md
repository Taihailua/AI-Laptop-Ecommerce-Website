# 🤖 Hướng dẫn sử dụng RAG cho Website AI Laptop Ecommerce

## 📚 Mục lục
1. [RAG là gì?](#rag-là-gì)
2. [Cài đặt](#cài-đặt)
3. [Cách hoạt động](#cách-hoạt-động)
4. [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
5. [Ví dụ thực tế](#ví-dụ-thực-tế)
6. [Troubleshooting](#troubleshooting)

---

## RAG là gì?

**RAG** (Retrieval-Augmented Generation) là kỹ thuật kết hợp:
- **Retrieval**: Tìm kiếm thông tin liên quan từ cơ sở dữ liệu vector (semantic search)
- **Augmentation**: Tăng cường dữ liệu cho LLM
- **Generation**: LLM tạo ra câu trả lời dựa trên dữ liệu tìm được

### Ưu điểm RAG so với keyword search:
| Khía cạnh | Keyword Search | RAG (Semantic Search) |
|-----------|----------------|----------------------|
| Tìm kiếm "laptop chơi game mạnh" | Chỉ match từ khóa chính xác | Hiểu ý nghĩa, tìm GPU RTX/GTX, RAM cao |
| Tìm kiếm "máy cho lập trình Python" | Không tìm được nếu product name không có "Python" | Tìm được laptop có RAM/CPU cao phù hợp |
| Tìm kiếm "laptop pin lâu dưới 20 triệu" | Chỉ search "pin lâu" hoặc "20 triệu" | Hiểu toàn bộ yêu cầu, kết hợp cả ba điều kiện |
| Tốc độ | ⚡ Cực nhanh (SQL index) | 🚶 Chậm hơn (AI processing) |
| Độ chính xác | ⭐⭐ Phụ thuộc vào keyword | ⭐⭐⭐⭐⭐ Rất cao với mô tả |

---

## Cài đặt

### 1️⃣ Cập nhật requirements.txt
Các thư viện cần thiết đã được thêm:
```
langchain-chroma
chromadb
sentence-transformers
```

### 2️⃣ Cài đặt các dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3️⃣ Seed Vector Database
Trước lần sử dụng đầu tiên, cần tạo embeddings cho tất cả sản phẩm:

```bash
python seed_vector_db.py
```

**Output mong đợi:**
```
============================================================
SEEDING VECTOR DATABASE FOR RAG
============================================================
✅ Đã seed 15 sản phẩm vào vector database
📁 Embeddings được lưu trong folder: backend/chroma_db/
✅ Vector database seeding completed successfully!
```

### 4️⃣ Cấu trúc thư mục sau seeding
```
backend/
├── chroma_db/                  # Vector database (được tạo tự động)
│   ├── chroma.sqlite3
│   ├── 0e844e15.bin            # Embeddings data
│   └── ...
├── app/
│   ├── ai/
│   │   ├── agent.py            # ✨ Đã cập nhật với RAG
│   │   ├── rag.py              # 🆕 Module RAG
│   │   └── __pycache__/
│   └── ...
└── seed_vector_db.py           # 🆕 Script để seed database
```

---

## Cách hoạt động

### 🔄 Luồng xử lý User Query

```
User: "Laptop gaming dưới 30 triệu với card NVIDIA RTX"
  │
  ├─► AI Agent nhận câu hỏi
  │
  ├─► Quyết định dùng tool nào:
  │   - Nếu có mô tả chi tiết ➜ semantic_search_laptops (RAG) ✨
  │   - Nếu chỉ keyword đơn giản ➜ search_laptops
  │
  ├─► RAG Tool chạy:
  │   1. Convert câu hỏi thành vector (embedding)
  │   2. So sánh cosine similarity với tất cả products
  │   3. Trả về top 5 sản phẩm phù hợp nhất + relevance score
  │
  ├─► AI xử lý kết quả:
  │   - Format dữ liệu
  │   - Tạo câu trả lời bằng tiếng Việt
  │   - Thêm giải thích vì sao chọn những sản phẩm này
  │
  └─► Return cho User
      "Dựa trên semantic search, tôi khuyến nghị:
       1. ASUS TUF A15 (RTX 3060) - 28 triệu (độ phù hợp: 94%)
       2. Lenovo Legion 5 (RTX 3050 Ti) - 25 triệu (độ phù hợp: 89%)
       ..."
```

### 📊 Embedding Model
Sử dụng: **all-MiniLM-L6-v2**
- 📦 Kích thước: ~80MB (nhẹ, nhanh)
- 🌐 Hỗ trợ: 100+ ngôn ngữ (bao gồm Tiếng Việt)
- ⚡ Tốc độ: ~0.3 giây/câu hỏi
- 🎯 Độ chính xác: Tốt cho retrieval tasks

---

## Hướng dẫn sử dụng

### 📝 Cách sử dụng RAG trong chatbot

#### Bước 1: Đảm bảo vector database đã seed
```bash
python seed_vector_db.py
```

#### Bước 2: Chạy FastAPI server
```bash
uvicorn app.main:app --reload
```

#### Bước 3: Gửi message qua chat API
**Endpoint:** `POST /chat/send_message`

```json
{
  "message": "Em muốn tìm laptop gaming pin lâu, có NVIDIA RTX, dưới 25 triệu"
}
```

**Response:**
```json
{
  "response": "Dựa trên semantic search, tôi tìm được:\n1. ASUS TUF 15 (RTX 3050)...",
  "sources": ["product_id_1", "product_id_2", ...]
}
```

### 🎯 Lựa chọn đúng câu hỏi cho RAG

#### ✅ CÓ NÊN dùng `semantic_search_laptops` khi:
1. **Mô tả chi tiết yêu cầu:**
   - "Laptop cho lập trình với RAM lớn, SSD 512GB, CPU mạnh"
   - "Máy gaming pin lâu, màn hình 144Hz, nhẹ dưới 2kg"
   - "Laptop sinh viên vừa chơi game vừa học tập"

2. **Yêu cầu phức tạp:**
   - "Laptop dưới 20 triệu, performance cao, hãng nào chất lượng?"
   - "Máy thích hợp cho video editing, cần GPU mạnh"

3. **Câu hỏi mô tả tự nhiên:**
   - "Cái nào tốt nhất cho chơi game và học code?"
   - "Máy nào pin lâu, không quá nặng?"

#### ❌ KHÔNG NÊN dùng `semantic_search_laptops` khi:
1. **Tìm kiếm keyword đơn:**
   - "Laptop Dell" ➜ Dùng `search_laptops` với query="Dell"
   - "Laptop i7" ➜ Dùng `search_laptops` với query="i7"

2. **Specific product ID:**
   - "Xem chi tiết sản phẩm #5" ➜ Gọi trực tiếp API `/products/5`

3. **Comparision:**
   - "So sánh sản phẩm 1 và 2" ➜ Dùng `compare_laptops`

### 🛠️ Cách dùng RAG module trực tiếp (Python code)

```python
from app.ai.rag import semantic_search_products, get_product_recommendations

# ✨ Cách 1: Semantic search
query = "Laptop gaming RTX 3060 pin lâu dưới 30 triệu"
results = semantic_search_products(query, top_k=5)

for product in results:
    print(f"Tên: {product['name']}")
    print(f"Giá: {product['price']:,.0f} VND")
    print(f"Độ phù hợp: {(1 - product['relevance_score']) * 100:.1f}%")
    print()

# ✨ Cách 2: Lấy recommendations theo use case
recommendations = get_product_recommendations(
    use_case="gaming",
    budget=30000000,  # 30 triệu VND
    top_k=5
)
```

---

## Ví dụ thực tế

### 📌 Ví dụ 1: User hỏi về laptop gaming

**User:** "Tôi cần laptop gaming pin lâu, có RTX 3060 trở lên, dưới 25 triệu"

**AI Agent:**
1. ✅ Nhận biết đây là câu hỏi phức tạp
2. ✅ Gọi `semantic_search_laptops` với query đầy đủ
3. ✅ RAG trả về top 5 sản phẩm phù hợp
4. ✅ AI tổng hợp kết quả + giải thích

**Response:**
```
Dựa trên AI semantic search, tôi tìm được 5 laptop gaming phù hợp:

1. [ID: 3] **ASUS TUF Gaming A15** (Hãng: ASUS)
   - Giá: 24,500,000 VND
   - Cấu hình: CPU: i7-11800H | RAM: 16GB | GPU: RTX 3060 | Pin: 90Wh
   - Tồn kho: 8 cái
   - Độ phù hợp: 96% ⭐⭐⭐⭐⭐ (TỐT NHẤT!)

2. [ID: 7] **Lenovo Legion 5** (Hãng: Lenovo)
   - Giá: 23,000,000 VND
   - Cấu hình: CPU: i5-10400H | RAM: 8GB | GPU: RTX 3050 Ti | Pin: 80Wh
   - Tồn kho: 5 cái
   - Độ phù hợp: 88%

...

Khuyến nghị: **ASUS TUF A15** có RTX 3060 + pin 90Wh lâu nhất, 
hoàn toàn phù hợp với yêu cầu của bạn!
```

### 📌 Ví dụ 2: User hỏi về laptop lập trình

**User:** "Tôi muốn laptop dùng cho lập trình Python, design, cần RAM 16GB+"

**Query được gửi đến RAG:**
```
"Laptop lập trình Python design RAM 16GB trở lên"
```

**RAG sẽ:**
1. 🧠 Hiểu rằng "lập trình Python" = cần CPU/RAM cao, không cần GPU mạnh
2. 🧠 Hiểu rằng "design" = cần màn hình tốt, có thể cần GPU
3. 🧠 Filter tất cả products có RAM >= 16GB
4. 🧠 Ưu tiên những laptop có CPU/GPU cân bằng

**Kết quả:** Trả về MacBook Pro, Dell XPS, ThinkPad X1 Pro (những máy cao cấp phù hợp)

### 📌 Ví dụ 3: User hỏi về laptop văn phòng

**User:** "Laptop dùng cho làm việc văn phòng, Excel, Word, lightweight"

**Query:**
```
"Laptop văn phòng Excel Word lightweight nhẹ"
```

**RAG sẽ:**
1. 🧠 Hiểu = cần CPU vừa đủ, RAM 8-16GB, không cần GPU mạnh
2. 🧠 Ưu tiên những máy nhẹ (< 1.5kg)
3. 🧠 Ưu tiên màn hình < 14 inch

**Kết quả:** Dell Inspiron 14, HP Pavilion, Lenovo IdeaPad (máy lightweight, giá tốt)

---

## Troubleshooting

### ❌ Lỗi: "Vector database not found"
```
🔧 Giải pháp: Chạy seed script
   python seed_vector_db.py
```

### ❌ Lỗi: "CUDA/GPU not available"
```
🔧 Giải pháp: RAG chạy trên CPU, không cần GPU
   Nhưng sẽ chậm hơn. Cài torch với GPU support nếu cần tốc độ
```

### ❌ Kết quả semantic search không chính xác
```
🔧 Giải pháp:
   1. Re-seed vector database: python seed_vector_db.py
   2. Kiểm tra database có dữ liệu: Chạy script test_rag.py
   3. Nếu vẫn lỗi, try embedding model khác:
      - Đổi "all-MiniLM-L6-v2" thành "all-mpnet-base-v2" (chính xác hơn nhưng nặng hơn)
```

### ❌ Tốc độ semantic search chậm
```
🔧 Giải pháp:
   1. Giảm top_k: semantic_search_products(query, top_k=3) => top_k=3
   2. Cài CUDA support cho torch
   3. Nếu database lớn, dùng hybrid search (kết hợp semantic + keyword)
```

### ❌ Lỗi: "Embedding model not found"
```
🔧 Giải pháp: 
   Model sẽ download tự động lần đầu (~80MB)
   Đảm bảo có internet connection
   Hoặc manually download: 
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-MiniLM-L6-v2')
```

---

## 📊 So sánh trước/sau khi thêm RAG

### Trước (chỉ dùng Keyword Search)
```
User: "Tôi cần laptop gaming pin lâu dưới 25 triệu"
AI: search_laptops(query="gaming") ➜ Chỉ match keyword "gaming"
Kết quả: Tất cả laptop gaming, bất kể pin hay giá

❌ Bỏ qua điều kiện "pin lâu" và "dưới 25 triệu"
```

### Sau (có RAG)
```
User: "Tôi cần laptop gaming pin lâu dưới 25 triệu"
AI: semantic_search_laptops(query="...") ➜ AI hiểu toàn bộ yêu cầu
Kết quả: Chỉ laptop gaming + pin > 80Wh + giá < 25 triệu

✅ Hoàn toàn chính xác, đáp ứng tất cả điều kiện
```

---

## 🚀 Nâng cao

### Tùy chỉnh embedding model
Sửa file [app/ai/rag.py](app/ai/rag.py):
```python
# Thay đổi dòng:
embedding_function = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"  # ← Đổi tên model
)

# Các model khác hỗ trợ tiếng Việt:
# - "all-mpnet-base-v2" (chính xác hơn, ~430MB)
# - "paraphrase-multilingual-MiniLM-L12-v2" (multilingual, ~65MB)
# - "sentence-bert-vietnamese" (chuyên Việt, tốt nhất)
```

### Tùy chỉnh thông tin trong embeddings
Sửa ở hàm `seed_vector_database()`:
```python
# Hiện tại embeddings chứa:
content = f"Tên: {product.name}. Hãng: {product.brand}. ..."

# Có thể thêm thêm thông tin:
content = f"Tên: {product.name}. {product.description}. ..."
```

---

## 📞 Hỗ trợ
Nếu gặp vấn đề:
1. Kiểm tra console logs
2. Xem section [Troubleshooting](#troubleshooting)
3. Chạy test script: `python test_rag.py`

---

**✨ Chúc bạn sử dụng RAG thành công! ✨**
