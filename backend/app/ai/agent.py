import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import crud

# Khởi tạo model Gemini
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

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
        products = crud.get_products(db, search=query, limit=10)

        if max_price is not None:
            products = [p for p in products if p.price <= max_price]
        if min_price is not None:
            products = [p for p in products if p.price >= min_price]

        if not products:
            return "Không tìm thấy laptop nào phù hợp với yêu cầu của bạn trong cửa hàng."

        result = "Danh sách laptop tìm thấy trong cửa hàng:\n"
        for p in products:
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

tools = [search_laptops, draft_order]

SYSTEM_PROMPT = (
    "Bạn là trợ lý bán hàng AI cho website TechShop - chuyên bán Laptop. "
    "Nhiệm vụ của bạn:\n"
    "1. Tư vấn laptop phù hợp dựa trên nhu cầu và ngân sách khách hàng.\n"
    "2. Sử dụng tool search_laptops để tìm sản phẩm thực tế trong cửa hàng (KHÔNG tự bịa thông tin).\n"
    "3. Nếu khách muốn mua, hỏi thông tin: Họ tên và Số điện thoại (bắt buộc), CCCD và Địa chỉ (khuyến khích).\n"
    "4. Sau khi có đủ thông tin, gọi tool draft_order để tạo đơn hàng.\n"
    "Luôn trả lời bằng tiếng Việt, thân thiện và nhiệt tình."
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
        return result["messages"][-1].content
    except Exception as e:
        return f"Xin lỗi, tôi gặp lỗi kỹ thuật: {str(e)}. Vui lòng thử lại sau."
