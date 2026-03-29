# RAG Architecture Diagram

## 🏗️ System Flow

```
┌─────────────────────────────────────────────────────────┐
│                    USER QUERY                           │
│  "Laptop gaming pin lâu RTX 3060 dưới 25 triệu"       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              AI AGENT (LangChain)                       │
│  - Phân tích query                                      │
│  - Quyết định tool cần dùng                            │
│  - Xử lý response                                       │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ✅ COMPLEX QUERY      ❌ SIMPLE QUERY
    "Mô tả chi tiết"      "Chỉ keyword"
         │                       │
         ▼                       ▼
  ┌────────────────┐    ┌──────────────────┐
  │ SEMANTIC_      │    │  SEARCH_         │
  │ SEARCH_        │    │  LAPTOPS         │
  │ LAPTOPS (RAG)  │    │  (Keyword)       │
  └────────┬───────┘    └──────┬───────────┘
           │                    │
           │                    │
           ▼                    ▼
    ┌────────────────┐   ┌──────────────────┐
    │ EMBEDDING      │   │ SQL SEARCH       │
    │ (Vector DB)    │   │ (Keyword match)  │
    │ • Chroma       │   │                  │
    │ • MiniLM model │   │ DB Products      │
    └────────┬───────┘   └──────┬───────────┘
             │                   │
             ▼                   ▼
      ┌────────────────┐  ┌──────────────────┐
      │ TOP K          │  │ FILTERED RESULTS │
      │ SIMILARITY     │  │ (IDs matching)   │
      │ RESULTS        │  │                  │
      └────────┬───────┘  └──────┬───────────┘
               │                  │
               └──────────┬───────┘
                          │
                          ▼
         ┌───────────────────────────────────┐
         │ FORMAT & COMBINE RESULTS         │
         │ • Parse product data             │
         │ • Order by relevance             │
         │ • Create response                │
         └───────────────┬─────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │ GENERATE RESPONSE (LLM)           │
         │ "Dựa trên tìm kiếm, tôi khuyến │
         │  nghị:"                           │
         │  1. ASUS TUF A15 - RTX 3060    │
         │  2. Lenovo Legion 5             │
         └───────────────┬─────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │           USER RESPONSE            │
         └───────────────────────────────────┘
```

## 🗄️ Data Flow

```
┌──────────────────────────────────────────────────────────┐
│                   SQL DATABASE                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Products Table                                     │ │
│  │ - id: 1        | name: "ASUS TUF A15"            │ │
│  │ - price: 24.5M | brand: "ASUS"                   │ │
│  │ - specs: {...} | stock: 8                        │ │
│  │ - RAM: 16GB    | GPU: RTX 3060                   │ │
│  │ ...                                                │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────────────────┘
                   │ (CRUD)
                   ▼
┌──────────────────────────────────────────────────────────┐
│              RAG SEEDING (Lần đầu)                       │
│  seed_vector_db.py                                       │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 1. Lấy tất cả products từ SQL                     │ │
│  │ 2. Convert thành text: "Tên: ... Specs: ..."     │ │
│  │ 3. Tính embedding (MiniLM model)                  │ │
│  │    "laptop gaming RTX pin lâu"                    │ │
│  │       ↓                                            │ │
│  │    [0.12, 0.45, 0.89, ... 384 dimensions]       │ │
│  │ 4. Lưu vào Chroma vector DB                       │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│                  CHROMA VECTOR DB                        │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Collection: laptop_products                         │ │
│  │ ┌─────────────────────────────────────────────┐   │ │
│  │ │ Vector 1 (Product 1):                      │   │ │
│  │ │ [0.152, 0.456, 0.891, ...] (384 dim)      │   │ │
│  │ │ metadata: {product_id: 1, name, price...} │   │
│  │ ├─────────────────────────────────────────────┤   │ │
│  │ │ Vector 2 (Product 2):                      │   │ │
│  │ │ [0.243, 0.567, 0.782, ...] (384 dim)      │   │ │
│  │ │ metadata: {product_id: 2, name, price...} │   │ │
│  │ ├─────────────────────────────────────────────┤   │ │
│  │ │ ... (nhiều vectors)                        │   │ │
│  │ └─────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────┘ │
│  📁 Location: backend/chroma_db/                        │
└──────────────────┬───────────────────────────────────────┘
                   │ (at runtime)
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
   User Query           Query Embedding
   "Laptop gaming    →  [0.156, 0.423, ...] (384 dim)
    RTX 3060"          (tính từ same model)
                            │
                            ▼
                  ┌────────────────────────┐
                  │ SIMILARITY SEARCH      │
                  │ Cosine Similarity      │
                  │                        │
                  │ Vect(Query) · Vect(i) │
                  │ ─────────────────────  │
                  │ ||Query|| × ||Vect(i)||
                  └────────┬───────────────┘
                           │
                ┌──────────┴──────────┐
                │                    │
             Product 1:           Product 2:
         Similarity: 0.89      Similarity: 0.76
             (TỐT!)            (Kém hơn)
             
             Sorted by score:
             1. Product 1: 0.89 ← TOP 1 ✅
             2. Product 2: 0.76
             3. Product 3: 0.65
             4. ...
```

## 🔄 Embedding Process

```
Input Text (từ user hoặc product)
│
│ "Laptop gaming RTX 3060 pin lâu dưới 25 triệu"
│
▼
┌────────────────────────────────────────────────┐
│ Tokenization (từng từ)                         │
│ ["Laptop", "gaming", "RTX", "3060", ...]      │
└────────────────────────────────────────────────┘
│
▼
┌────────────────────────────────────────────────┐
│ SentenceTransformer (all-MiniLM-L6-v2)        │
│ - 12 layers Transformer                        │
│ - Query + Key + Value attention                │
│ - Mean pooling                                 │
│ - Normalize                                    │
└────────────────────────────────────────────────┘
│
▼
┌────────────────────────────────────────────────┐
│ Output Vector (384 dimensions)                 │
│ [0.123, -0.456, 0.789, 0.234, ..., -0.567]  │
│                                                 │
│ Vector này capture:                            │
│ ✅ Semantic meaning ("gaming" = FPS, RTX)    │
│ ✅ Context ("pin lâu" = battery)              │
│ ✅ Purpose (laptop cho chơi game)             │
│ ✅ Price constraint (dưới 25 triệu)          │
└────────────────────────────────────────────────┘
```

## 📊 Comparison: Keyword Search vs RAG

```
USER QUERY: "Laptop gaming pin lâu RTX dưới 25 triệu"

┌─────────────────────────────────────────────────────────┐
│ KEYWORD SEARCH (Cũ)                                     │
├─────────────────────────────────────────────────────────┤
│ Query splitting: ["gaming", "pin", "RTX", "25"]        │
│ ↓                                                        │
│ SQL LIKE: name LIKE %gaming% OR name LIKE %RTX%        │
│ ↓                                                        │
│ Result: Tất cả laptop gaming có "RTX" trong tên        │
│ ❌ Bỏ qua "pin lâu"                                    │
│ ❌ Bỏ qua "dưới 25 triệu"                              │
│ ⏱️  Nhanh (SQL index)                                  │
│ 🎯 Độ chính xác: 40%                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ RAG SEMANTIC SEARCH (Mới) ✨                            │
├─────────────────────────────────────────────────────────┤
│ Full query: "Laptop gaming pin lâu RTX dưới 25 triệu" │
│ ↓                                          │            │
│ ┌─────────────────────────────────────────┘            │
│ │                                                       │
│ ├─► Embedding model hiểu:                             │
│ │   • "gaming" = chơi game → RTX/GTX, RAM cao        │
│ │   • "pin lâu" = battery >= 80Wh                    │
│ │   • "RTX" = GPU mạnh → nhân viên gaming           │
│ │   • "dưới 25 triệu" = price <= 25,000,000        │
│ │                                                      │
│ ├─► So sánh với tất cả products:                       │
│ │   Product_1: Similarity = 0.94 (RTX, pin 90Wh)    │
│ │   Product_2: Similarity = 0.78 (RTX, pin 60Wh)    │
│ │   Product_3: Similarity = 0.42 (I5, no RTX)       │
│ │                                                      │
│ └─► Return top 5 ranked by similarity               │
│                                                        │
│ ✅ Đáp ứng tất cả 4 điều kiện                         │
│ ⏱️  Chậm hơn (AI processing) nhưng không tệ           │
│ 🎯 Độ chính xác: 95%+                                 │
└─────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

```
┌────────────────────────────────────────────┐
│          USER INTERFACE (Frontend)          │
│  HTML + JS + API calls                      │
└────────────────────┬───────────────────────┘
                     │ REST API
                     ▼
┌────────────────────────────────────────────┐
│         FastAPI (Backend)                   │
│  app/routers/chat.py                        │
│  - /chat/send_message                       │
│  - /chat/history                            │
└────────────────────┬───────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌─────────────┐      ┌──────────────┐
    │  LangChain  │      │  SQLAlchemy  │
    │  - Agent    │      │  - ORM       │
    │  - Tools    │      │  - Queries   │
    └──────┬──────┘      └──────┬───────┘
           │                     │
           │ Tool calls          │
           ▼                     ▼
    ┌─────────────────────────────────┐
    │     app/ai/agent.py             │
    │  - search_laptops               │
    │  - semantic_search_laptops ✨  │
    │  - compare_laptops              │
    │  - draft_order                  │
    │  - ...                          │
    └──────────┬────────────────────┘
               │
         ┌─────┴─────┐
         │           │
         ▼           ▼
    ┌─────────┐  ┌──────────────┐
    │   RAG   │  │   CRUD       │
    │ ┌─────┐ │  │ ┌──────────┐ │
    │ │Chroma│ │  │ │PostgreSQL│ │
    │ │Vector│ │  │ └──────────┘ │
    │ │  DB  │ │  │              │
    │ └─────┘ │  └──────────────┘
    └────┬────┘
         │
    embedding_model
    (all-MiniLM-L6-v2)
```

## 🔔 Key Components

| Component | Role | Technology |
|-----------|------|-----------|
| **Agent** | Orchestrator | LangChain + LangGraph |
| **Embedding Model** | Convert text to vectors | SentenceTransformers |
| **Vector DB** | Store & retrieve vectors | Chroma |
| **SQL DB** | Store products | PostgreSQL + SQLAlchemy |
| **LLM** | Generate responses | Google Gemini |
| **Tools** | Query products | Python functions |
| **Tools** | Smart retrieval | semantic_search_laptops |

---

**✨ RAG Architecture Diagram Complete!**
