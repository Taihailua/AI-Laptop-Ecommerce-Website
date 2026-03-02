# 💻 AI Laptop Ecommerce Website

Website bán Laptop tích hợp Trợ lý AI (Gemini) thông minh. Hệ thống gồm 3 tầng: **Frontend (HTML/JS/Tailwind)** — **Backend (FastAPI)** — **Database (PostgreSQL)**.

Đây là đồ án chuyên ngành xây dựng website thương mại điện tử trọn gói, tập trung vào trải nghiệm mua sắm được cá nhân hóa nhờ AI Agent.

---

## 🚀 Tính năng nổi bật

### 🛒 Khách hàng (Client Side)
- **Trang chủ (`index.html`)**: 
  - Hiển thị danh sách laptop với bộ lọc thông minh.
  - Tích hợp **AI Chatbot** (LangChain + Gemini) hỗ trợ tìm kiếm sản phẩm theo ngôn ngữ tự nhiên (VD: "Tìm máy văn phòng giá rẻ dưới 15 triệu").
- **Chi tiết sản phẩm (`product-detail.html`)**: Xem thông số kỹ thuật chi tiết.
- **Giỏ hàng & Thanh toán (`checkout.html`)**: Quy trình đặt hàng đơn giản, lưu đơn hàng vào hệ thống.
- **Tra cứu đơn hàng (`track-order.html`)**: Cho phép khách hàng tự kiểm tra trạng thái vận chuyển.

### 🔧 Quản trị viên (Admin Side)
- **Đăng nhập bảo mật (`admin-login.html`)**: Sử dụng JWT Token.
- **Dashboard (`admin.html`)**: Tổng quan đơn hàng, doanh thu.
- **Quản lý sản phẩm (`admin-products.html`)**: 
  - **CRUD đầy đủ**: Thêm, Sửa, Xóa sản phẩm.
  - **New Feature**: Upload hình ảnh trực tiếp từ máy tính (Local Storage).
  - Quản lý kho hàng và giá bán.

---

## 🛠️ Yêu cầu hệ thống

- **Docker Desktop** (Để chạy PostgreSQL database)
- **Python 3.10+**
- **Git**
- **Google API Key** (Từ [Google AI Studio](https://aistudio.google.com/)) để chạy Chatbot.

---

## ⚙️ Hướng dẫn cài đặt và chạy (Local Development)

### Bước 1: Khởi động Database (Docker)

Mở terminal tại thư mục gốc dự án:

```bash
docker-compose up -d
```
*Lệnh này sẽ tải và chạy container PostgreSQL tại port `5432`.*

### Bước 2: Thiết lập Backend (FastAPI)

1. **Di chuyển vào thư mục backend:**
   ```bash
   cd backend
   ```

2. **Tạo môi trường ảo và cài đặt thư viện:**
   ```bash
   python -m venv venv
   
   # Windows:
   .\venv\Scripts\activate
   
   # Mac/Linux:
   # source venv/bin/activate 
   
   pip install -r requirements.txt
   ```

3. **Cấu hình biến môi trường:**
   - Tạo file `.env` từ file mẫu (nếu chưa có):
     ```bash
     cp .env.example .env
     ```
   - Mở file `.env` và cập nhật khóa API của Google:
     ```env
     GOOGLE_API_KEY=your_actual_api_key_here
     DATABASE_URL=postgresql://ai_user:ai_password@localhost:5432/ecommerce_ai
     SECRET_KEY=your_secret_key
     ```

4. **Khởi tạo dữ liệu mẫu (Seeding):**
   ```bash
   python seed_data.py
   ```
   *Script này sẽ tạo bảng trong database và insert Admin user + Sản phẩm mẫu.*
   
   **Tài khoản Admin mặc định:**
   - User: `admin`
   - Password: `admin123`

5. **Chạy Server Backend:**
   ```bash
   uvicorn app.main:app --reload
   ```
   - Backend chạy tại: `http://localhost:8000`
   - Tài liệu API (Swagger UI): `http://localhost:8000/docs`
   - Thư mục ảnh Upload: `http://localhost:8000/static/`

### Bước 3: Chạy Frontend (Client)

Frontend sử dụng Tailwind CSS qua CDN và ES Modules, cần chạy qua HTTP Server để tránh lỗi CORS.

1. **Mở một terminal mới** (giữ nguyên terminal backend đang chạy).
2. **Di chuyển vào thư mục frontend:**
   
   ```bash
   cd frontend
   ```

3. **Chạy server frontend:**

   - **Cách 1 (Khuyên dùng - Python):**
     ```bash
     python -m http.server 3000
     ```
   - **Cách 2 (VS Code Live Server):**
     Click chuột phải vào file `index.html` chọn "Open with Live Server".

4. **Truy cập Website:**
   - Khách hàng: `http://localhost:3000`
   - Admin Panel: `http://localhost:3000/admin-login.html`

---

## 📂 Cấu trúc thư mục chính

```
/
├── backend/
│   ├── app/
│   │   ├── main.py        # Entry point của FastAPI
│   │   ├── models.py      # SQLAlchemy Models
│   │   ├── routers/       # API Endpoints (Products, Orders, Chat...)
│   │   └── ai/            # Logic xử lý AI (LangChain agent)
│   ├── uploads/           # Thư mục lưu ảnh upload
│   ├── requirements.txt   # Các thư viện Python
│   └── seed_data.py       # Script khởi tạo dữ liệu
├── frontend/              # Giao diện HTML/JS thuần
├── docker-compose.yml     # Cấu hình Docker cho DB
└── README.md
```

## 📝 Ghi chú phát triển
- Ảnh upload được lưu cục bộ tại `backend/uploads`. Trong môi trường production thực tế, nên chuyển sang AWS S3 hoặc Cloudinary.
- Chatbot sử dụng `langchain-google-genai` để kết nối với Gemini Pro.
