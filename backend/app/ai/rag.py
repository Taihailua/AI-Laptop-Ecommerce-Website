"""
RAG (Retrieval-Augmented Generation) module cho AI Laptop Ecommerce.
Sử dụng Chroma vector database và sentence-transformers để semantic search.
"""

import os
import json
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import crud

# Khởi tạo embedding model (mô hình nhẹ, hỗ trợ tiếng Việt)
embedding_function = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"  # Model nhẹ (~80MB), hỗ trợ 100+ ngôn ngữ
)

# Đường dẫn đến Chroma persistent database
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "../../chroma_db")

def create_vector_store() -> Chroma:
    """
    Tạo hoặc load Chroma vector store.
    Nếu DB chưa tồn tại, sẽ tạo mới.
    """
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    
    vector_store = Chroma(
        collection_name="laptop_products",
        embedding_function=embedding_function,
        persist_directory=CHROMA_DB_PATH
    )
    return vector_store

def seed_vector_database():
    """
    Seed vector database từ SQL database.
    Chạy lần đầu hoặc khi muốn update lại embeddings.
    """
    db: Session = SessionLocal()
    try:
        vector_store = create_vector_store()
        
        # Xóa collection cũ nếu tồn tại
        try:
            vector_store.delete_collection()
            vector_store = create_vector_store()
        except:
            pass
        
        # Lấy tất cả products từ DB
        products = crud.get_products(db, limit=10000)
        
        documents = []
        metadatas = []
        
        for product in products:
            # Tạo text content để search
            specs_text = ""
            if product.specs and isinstance(product.specs, dict):
                specs_text = ". ".join(f"{k}: {v}" for k, v in product.specs.items())
            
            # Content: combine tất cả thông tin sản phẩm
            content = (
                f"Tên: {product.name}. "
                f"Hãng: {product.brand}. "
                f"Giá: {product.price:,.0f} VND. "
                f"Cấu hình: {specs_text}. "
                f"Tồn kho: {product.stock_quantity} cái."
            )
            
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "product_id": product.id,
                        "name": product.name,
                        "brand": product.brand,
                        "price": product.price,
                        "stock": product.stock_quantity,
                        "specs": json.dumps(product.specs) if product.specs else "{}"
                    }
                )
            )
        
        if documents:
            # Thêm tất cả documents vào vector store
            vector_store.add_documents(documents)
            print(f"✅ Đã seed {len(documents)} sản phẩm vào vector database")
        else:
            print("⚠️ Không tìm thấy sản phẩm nào trong database")
    
    finally:
        db.close()

def semantic_search_products(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Tìm kiếm sản phẩm dựa trên semantic similarity.
    
    Args:
        query: Mô tả hoặc yêu cầu từ user (ví dụ: "laptop gaming mạnh nhất dưới 30 triệu")
        top_k: Số lượng kết quả trả về (mặc định 5)
    
    Returns:
        List of dictionaries với thông tin sản phẩm
    """
    try:
        vector_store = create_vector_store()
        
        # Tìm kiếm similarity-based
        results = vector_store.similarity_search_with_score(query, k=top_k)
        
        products = []
        for doc, score in results:
            metadata = doc.metadata
            products.append({
                "id": metadata.get("product_id"),
                "name": metadata.get("name"),
                "brand": metadata.get("brand"),
                "price": metadata.get("price"),
                "stock": metadata.get("stock"),
                "specs": json.loads(metadata.get("specs", "{}")),
                "relevance_score": float(score)  # Score thấp hơn = match tốt hơn
            })
        
        return products
    
    except Exception as e:
        print(f"❌ Lỗi semantic search: {str(e)}")
        return []

def hybrid_search(query: str, keyword_search_func, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Tìm kiếm hybrid: kết hợp semantic search + keyword search.
    
    Args:
        query: Query string
        keyword_search_func: Function thực hiện keyword search (ví dụ: crud.get_products)
        top_k: Số kết quả trả về
    
    Returns:
        Danh sách sản phẩm được sắp xếp theo độ liên quan
    """
    # Semantic search
    semantic_results = semantic_search_products(query, top_k=top_k)
    
    if not semantic_results:
        print("⚠️ Semantic search không tìm thấy kết quả, fallback to keyword search")
        # Fallback: keyword search
        db: Session = SessionLocal()
        try:
            products = keyword_search_func(db, search=query, limit=top_k)
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "brand": p.brand,
                    "price": p.price,
                    "stock": p.stock_quantity,
                    "specs": p.specs,
                    "relevance_score": 0.0  # Không có relevance score cho keyword search
                }
                for p in products
            ]
        finally:
            db.close()
    
    return semantic_results

def get_product_recommendations(use_case: str, budget: float = None, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Lấy các khuyến nghị sản phẩm dựa trên use case và ngân sách.
    
    Args:
        use_case: Mục đích sử dụng (gaming, coding, văn phòng, etc)
        budget: Ngân sách tối đa (VND) - optional
        top_k: Số lượng recommendations
    
    Returns:
        Danh sách sản phẩm được khuyến nghị
    """
    query = f"Laptop tốt cho {use_case}"
    if budget:
        query += f" giá dưới {budget:,.0f} VND"
    
    results = semantic_search_products(query, top_k=top_k)
    
    # Filter theo budget nếu có
    if budget:
        results = [p for p in results if p.get("price", float("inf")) <= budget]
    
    return results

def format_products_for_chat(products: List[Dict[str, Any]]) -> str:
    """
    Format danh sách sản phẩm thành text dễ đọc cho chatbot.
    """
    if not products:
        return "Không tìm thấy sản phẩm phù hợp."
    
    result = "Các sản phẩm được gợi ý (dựa trên semantic search):\n"
    for i, p in enumerate(products, 1):
        specs_text = ""
        if p.get("specs") and isinstance(p["specs"], dict):
            specs_text = " | ".join(f"{k}: {v}" for k, v in p["specs"].items())
        
        result += (
            f"{i}. **{p.get('name')}** (Hãng: {p.get('brand')})\n"
            f"   - Giá: {p.get('price', 0):,.0f} VND\n"
            f"   - Cấu hình: {specs_text or 'N/A'}\n"
            f"   - Tồn kho: {p.get('stock', 0)} cái\n"
            f"   - Độ phù hợp: {(1 - p.get('relevance_score', 0)) * 100:.1f}%\n"
        )
    
    return result
