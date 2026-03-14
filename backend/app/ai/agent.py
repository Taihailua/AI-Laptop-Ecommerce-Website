import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import crud
from . import rag

# Khởi tạo model Gemini
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.2)

@tool
def search_laptops(query: str, max_price: float = None, min_price: float = None) -> str:
    """
    Search for laptops in the database based on a search query and optional price range.
    Use this tool when the user asks for laptop recommendations or asks about specific laptops.
    Args:
        query: Search keyword (brand name, spec, use case like 'gaming', 'coding')
        max_price: Maximum price in VND (optional)
        min_price: Minimum price in VND (optional)
    """
    db: Session = SessionLocal()
    try:
        # Nếu query có chứa từ khóa chung chung như "laptop dưới 20 triệu", "máy tính gaming", thì sẽ tìm rộng hơn dựa trên use case.
        generic_keywords = ["laptop", "máy tính", "máy", "computer", "all", "tất cả"]
        is_generic = any(kw in query.lower() for kw in generic_keywords)
        
        if is_generic:
            products = crud.get_products(db, limit=50)  # Lấy tất cả
        else:
            products = crud.get_products(db, search=query, limit=20)

        # Normalize giá: nếu LLM truyền vào 20 thay vì 20000000
        def normalize_price(price):
            if price is None:
                return None
            if price < 1000:        # 20 → 20 triệu
                return price * 1000000
            elif price < 1000000: # 20000 → có thể là 20 nghìn (nghìn đồng)
                return price * 1000
            return price            # 20000000 → giữ nguyên

        max_price = normalize_price(max_price)
        min_price = normalize_price(min_price)

        def parse_ram(ram_value) -> int: # Biến đổi str sang int để dễ so sánh (ví dụ '8GB' → 8, '16GB' → 16, 8 → 8)
            """Convert '8GB', '16GB', 8 → số nguyên GB"""
            if isinstance(ram_value, int):
                return ram_value
            if isinstance(ram_value, str):
                return int(''.join(filter(str.isdigit, ram_value)) or 0)
            return 0

        # Filter dựa trên use case nếu query chứa từ khóa
        if "văn phòng" in query.lower() or "office" in query.lower() or "business" in query.lower():
            # Văn phòng: CPU i5/i7, RAM <=16GB, không GPU rời mạnh, màn hình <=15.6"
            products = [p for p in products if 
                       ("i5" in str(p.specs.get('cpu', '')) or "i7" in str(p.specs.get('cpu', '')) or "M2" in str(p.specs.get('cpu', ''))) and
                       (parse_ram(p.specs.get('ram', 0)) <= 16) and
                       ("rtx" not in str(p.specs.get('gpu', '')).lower() or not p.specs.get('gpu')) and
                       (p.specs.get('screen', '').startswith(('13', '14', '15.6')) or not p.specs.get('screen'))]
        elif "gaming" in query.lower():
            # Gaming: GPU RTX/GTX, RAM >=8GB, CPU mạnh
            products = [p for p in products if 
                       ("rtx" in str(p.specs.get('gpu', '')).lower() or "gtx" in str(p.specs.get('gpu', '')).lower()) and
                       parse_ram(p.specs.get('ram', 0)) >= 8]
        
        # Filter giá
        if max_price is not None:
            products = [p for p in products if p.price <= max_price]
        if min_price is not None:
            products = [p for p in products if p.price >= min_price]

        if not products:
            return "Không tìm thấy laptop nào phù hợp với yêu cầu của bạn trong cửa hàng."

        result = "Danh sách laptop tìm thấy trong cửa hàng:\n"
        for p in products[:10]:  # Giới hạn 10 để không quá dài
            specs_str = ""
            if p.specs:
                if isinstance(p.specs, dict):
                    specs_str = " | ".join(f"{k}: {v}" for k, v in p.specs.items())
                else:
                    specs_str = str(p.specs)
            result += f"- [ID: {p.id}] **{p.name}** (Hãng: {p.brand}) - Giá: {p.price:,.0f} VND - Tồn kho: {p.stock_quantity}\n"
            if specs_str:
                result += f"  Cấu hình: {specs_str}\n"
        return result
    finally:
        db.close()

@tool
def compare_laptops(product_ids: list[int]) -> str:
    """
    Compare up to 3 laptops by their IDs, showing key specs, price, and pros/cons.
    Use this tool when the user wants to compare specific laptops.
    Args:
        product_ids: List of up to 3 product IDs to compare
    """
    if len(product_ids) > 3:
        return "Chỉ có thể so sánh tối đa 3 laptop cùng lúc."
    
    db: Session = SessionLocal()
    try:
        products = [p for pid in product_ids if (p := crud.get_product(db, pid))]
        if not products:
            return "Không tìm thấy sản phẩm nào để so sánh."
        
        result = "So sánh laptop:\n"
        for i, p in enumerate(products, 1):
            specs_str = ""
            if p.specs and isinstance(p.specs, dict):
                specs_str = " | ".join(f"{k}: {v}" for k, v in p.specs.items())
            result += f"{i}. **{p.name}** (Hãng: {p.brand})\n"
            result += f"   - Giá: {p.price:,.0f} VND\n"
            result += f"   - Cấu hình: {specs_str or 'N/A'}\n"
            result += f"   - Tồn kho: {p.stock_quantity}\n\n"
        
        # Thêm nhận xét chung dựa trên giá và specs
        prices = [p.price for p in products]
        min_price = min(prices)
        max_price = max(prices)
        cheapest = next(p for p in products if p.price == min_price)
        most_expensive = next(p for p in products if p.price == max_price)
        
        result += "Kết luận:\n"
        result += f"- Laptop rẻ nhất: {cheapest.name} ({min_price:,.0f} VND) - Phù hợp ngân sách thấp.\n"
        result += f"- Laptop đắt nhất: {most_expensive.name} ({max_price:,.0f} VND) - Cấu hình mạnh nhất.\n"
        if len(products) > 1:
            result += "- Khuyến nghị: Chọn dựa trên nhu cầu (gaming cần specs cao, văn phòng specs nhẹ)."
        
        return result
    finally:
        db.close()

@tool
def highlight_product_advantages(product_id: int) -> str:
    """
    Highlight the advantages of a specific laptop compared to similar products in the store.
    Use this tool when the user asks what makes a product stand out or unique.
    Args:
        product_id: The ID of the product to highlight
    """
    db: Session = SessionLocal()
    try:
        product = crud.get_product(db, product_id)
        if not product:
            return "Không tìm thấy sản phẩm này."
        
        # Tìm sản phẩm tương tự (cùng brand hoặc giá gần)
        all_products = crud.get_products(db, limit=20)  # Lấy nhiều sản phẩm
        similar = [p for p in all_products if p.id != product_id and (p.brand == product.brand or abs(p.price - product.price) < 5000000)]
        
        if not similar:
            return f"Sản phẩm {product.name} là duy nhất trong cửa hàng, không có sản phẩm tương tự để so sánh."
        
        advantages = []
        for sim in similar:
            if product.price < sim.price:
                advantages.append(f"Rẻ hơn {sim.name} ({sim.price - product.price:,.0f} VND)")
            if product.stock_quantity > sim.stock_quantity:
                advantages.append(f"Tồn kho nhiều hơn {sim.name}")
            # Thêm so sánh specs nếu cần (ví dụ CPU mạnh hơn)
            if product.specs and sim.specs:
                prod_cpu = product.specs.get('cpu', '')
                sim_cpu = sim.specs.get('cpu', '')
                if 'i7' in prod_cpu and 'i5' in sim_cpu:
                    advantages.append(f"CPU mạnh hơn {sim.name}")
        
        result = f"Điểm nổi bật của {product.name}:\n"
        if advantages:
            result += "\n".join(f"- {adv}" for adv in advantages)
        else:
            result += "- Sản phẩm này có giá cả hợp lý và cấu hình cân bằng."
        
        return result
    finally:
        db.close()

@tool
def explain_specs(use_case: str) -> str:
    """
    Explain basic specs recommendations for a use case.
    Use this tool when the user doesn't know specs and asks for guidance.
    Args:
        use_case: The intended use (e.g., 'văn phòng', 'gaming')
    """
    if "văn phòng" in use_case.lower() or "office" in use_case.lower():
        return (
            "Đối với laptop văn phòng:\n"
            "- CPU: i5/i7 hoặc Apple M2 (đủ cho Word, Excel, trình duyệt).\n"
            "- RAM: 8-16GB (đa nhiệm nhẹ).\n"
            "- Ổ cứng: SSD 256-512GB (nhanh khởi động).\n"
            "- Màn hình: 13-15.6 inch (dễ di chuyển).\n"
            "- Không cần GPU rời mạnh.\n"
            "Hãng phổ biến: Dell, HP, Lenovo, Apple."
        )
    elif "gaming" in use_case.lower():
        return (
            "Đối với laptop gaming:\n"
            "- CPU: i5/i7 trở lên (xử lý game mượt).\n"
            "- RAM: 16GB+ (chạy game nặng).\n"
            "- GPU: RTX 3050/3060 trở lên (đồ họa cao).\n"
            "- Ổ cứng: SSD 512GB+ (lưu game).\n"
            "- Màn hình: 15.6 inch 144Hz+ (mượt mà).\n"
            "Hãng phổ biến: Asus, Lenovo, Acer."
        )
    elif "coding" in use_case.lower() or "lập trình" in use_case.lower():
        return (
            "Đối với laptop coding/lập trình:\n"
            "- CPU: i5/i7 hoặc Apple M2/M3 (xử lý code nhanh).\n"
            "- RAM: 16GB+ (chạy IDE, server).\n"
            "- Ổ cứng: SSD 512GB+ (lưu project).\n"
            "- Màn hình: 14-16 inch (đủ rộng).\n"
            "- GPU: Không bắt buộc, nhưng tốt nếu làm AI/ML.\n"
            "Hãng phổ biến: Apple, Dell, Lenovo."
        )
    else:
        return "Hãy cho tôi biết mục đích sử dụng (văn phòng, gaming, coding, v.v.) để tôi giải thích specs phù hợp."

@tool
def generate_product_description(product_id: int) -> str:
    """..."""
    db: Session = SessionLocal()
    try:
        product = crud.get_product(db, product_id)
        if not product:
            return "Không tìm thấy sản phẩm."
        
        specs_text = ""
        if product.specs and isinstance(product.specs, dict):
            specs_text = ", ".join(f"{k}: {v}" for k, v in product.specs.items())
        
        # Trả về data thô, để agent tự mô tả — KHÔNG gọi llm.invoke nữa
        return f"Thông tin sản phẩm {product.name}: {specs_text}. Giá: {product.price:,.0f} VND."
    finally:
        db.close()

@tool
def draft_order(customer_name: str, phone_number: str, product_ids: list[int], quantities: list[int], cccd: str = None, address: str = None) -> str:
    """
    Create a new order for a customer with specified products.
    IMPORTANT: You MUST ask for customer_name and phone_number before calling this tool.
    CCCD and address are optional but recommended.
    product_ids: list of product IDs (integers) to order
    quantities: list of quantities corresponding to each product_id
    """
    if len(product_ids) != len(quantities):
        return "Lỗi: Số lượng sản phẩm và số lượng không khớp nhau."

    db: Session = SessionLocal()
    try:
        from ..schemas import OrderCreate, OrderItemCreate
        items = [OrderItemCreate(product_id=int(pid), quantity=int(q)) for pid, q in zip(product_ids, quantities)]

        order_data = OrderCreate(
            items=items,
            customer_name=customer_name,
            customer_phone=phone_number,
            customer_cccd=cccd,
            customer_address=address
        )

        order = crud.create_order(db, order_data)
        return (
            f"✅ Đã tạo đơn hàng thành công!\n"
            f"- Mã đơn hàng: #{order.id}\n"
            f"- Tổng tiền: {order.total_amount:,.0f} VND\n"
            f"- Trạng thái: {order.status}\n"
            f"Khách hàng có thể tra cứu đơn hàng bằng số điện thoại {phone_number}."
        )
    except Exception as e:
        return f"Lỗi khi tạo đơn hàng: {str(e)}"
    finally:
        db.close()

@tool
def semantic_search_laptops(query: str, top_k: int = 5) -> str:
    """
    Search for laptops using RAG (semantic similarity).
    Use this tool when the user asks for recommendations with descriptive queries.
    This uses AI-powered semantic search (not just keyword matching).
    Args:
        query: Descriptive search query (e.g., 'laptop gaming mạnh dengan card đồ họa cao', 'máy tính cho lập trình với RAM lớn')
        top_k: Number of results to return (default 5)
    """
    try:
        products = rag.semantic_search_products(query, top_k=top_k)
        
        if not products:
            return "Không tìm thấy sản phẩm phù hợp với tìm kiếm của bạn."
        
        result = "Kết quả tìm kiếm (dựa trên semantic search - AI hiểu ý nghĩa):\n"
        for i, p in enumerate(products, 1):
            specs_text = ""
            if p.get("specs") and isinstance(p["specs"], dict):
                specs_text = " | ".join(f"{k}: {v}" for k, v in p["specs"].items())
            
            result += (
                f"{i}. [ID: {p.get('id')}] **{p.get('name')}** (Hãng: {p.get('brand')})\n"
                f"   - Giá: {p.get('price', 0):,.0f} VND\n"
                f"   - Cấu hình: {specs_text or 'N/A'}\n"
                f"   - Tồn kho: {p.get('stock', 0)} cái\n"
                f"   - Độ phù hợp: {(1 - p.get('relevance_score', 0)) * 100:.1f}%\n"
            )
        
        return result
    except Exception as e:
        return f"Lỗi khi thực hiện semantic search: {str(e)}"

tools = [search_laptops, compare_laptops, highlight_product_advantages, generate_product_description, explain_specs, semantic_search_laptops, draft_order]

SYSTEM_PROMPT = (
    "Bạn là trợ lý bán hàng AI cho website TechShop - chuyên bán Laptop. "
    "Nhiệm vụ của bạn:\n"
    "1. TƯ VẤN LAPTOP VỚI RAG (Semantic Search): Khi khách hỏi laptop với mô tả chi tiết hoặc yêu cầu phức tạp, "
    "NGAY LẬP TỨC dùng tool semantic_search_laptops thay vì search_laptops. "
    "Ví dụ: 'laptop cho lập trình Python với RAM cao', 'máy gaming pin lâu', 'laptop nhẹ cho sinh viên dưới 15 triệu'. "
    "Tool semantic_search_laptops sẽ dùng AI hiểu ý nghĩa câu, không chỉ keyword matching.\n"
    "2. FALLBACK: Nếu semantic search không tìm thấy, dùng search_laptops với keyword cụ thể (brand, CPU, giá).\n"
    "3. So sánh sản phẩm: Khi khách hỏi so sánh các sản phẩm đã đề cập, lấy ID từ kết quả search và gọi compare_laptops.\n"
    "4. Nhấn mạnh ưu điểm: Dùng highlight_product_advantages khi khách hỏi điểm nổi bật.\n"
    "5. Giải thích specs: Dùng explain_specs nếu khách không hiểu specs.\n"
    "6. Xử lý mua hàng: Hỏi thông tin khách (Họ tên, Số điện thoại, CCCD, Địa chỉ), rồi gọi draft_order.\n"
    "7. Lưu ý: Giá tính bằng VND đầy đủ. Luôn trả lời tiếng Việt, thân thiện, chuyên nghiệp.\n"
    "8. QUAN TRỌNG: Ưu tiên dùng semantic_search_laptops cho các câu hỏi mô tả, dùng search_laptops cho keyword ngắn."
)

# Tạo agent bằng langgraph prebuilt API (tương thích LangChain 0.3+)
agent_executor = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

def get_chat_response(message: str, chat_history: list = None) -> str:
    """
    Gửi tin nhắn tới AI agent và lấy phản hồi.
    chat_history: list of tuples [("human", msg), ("ai", response)]
    """
    messages = []

    # Thêm lịch sử chat
    if chat_history:
        for role, content in chat_history:
            if role == "human":
                messages.append({"role": "user", "content": content})
            elif role == "ai":
                messages.append({"role": "assistant", "content": content})

    # Thêm tin nhắn hiện tại
    messages.append({"role": "user", "content": message})

    try:
        result = agent_executor.invoke({"messages": messages})
        # Lấy tin nhắn cuối từ kết quả
        raw_content = result["messages"][-1].content
        # Xử lý content nếu là list (từ Gemini API)
        if isinstance(raw_content, list) and raw_content:
            # Extract text từ dict đầu tiên có 'text'
            for item in raw_content:
                if isinstance(item, dict) and 'text' in item:
                    response = item['text']
                    break
            else:
                response = str(raw_content)  # Fallback
        else:
            response = str(raw_content)  # Fallback cho string hoặc dict khác
        print(f"AI Response: {response}")  # Debug: In phản hồi để kiểm tra
        return response
    except Exception as e:
        print(f"AI Error: {e}")  # Debug: In lỗi
        return f"Xin lỗi, tôi gặp lỗi kỹ thuật: {str(e)}. Vui lòng thử lại sau."
