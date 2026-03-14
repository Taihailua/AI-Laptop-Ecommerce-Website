"""
Test script cho RAG module.
Dùng để kiểm tra xem RAG hoạt động đúng không.

Cách chạy:
    python test_rag.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.ai.rag import (
    semantic_search_products,
    get_product_recommendations,
    format_products_for_chat,
    create_vector_store
)

def test_vector_database():
    """Kiểm tra xem vector database có tồn tại không"""
    print("\n" + "="*60)
    print("TEST 1: Kiểm tra Vector Database")
    print("="*60)
    
    try:
        vector_store = create_vector_store()
        collection = vector_store._client.get_collection(name="laptop_products")
        count = collection.count()
        print(f"✅ Vector database tồn tại")
        print(f"   - Collection: laptop_products")
        print(f"   - Số sản phẩm: {count}")
        
        if count == 0:
            print("   ⚠️  CẢNH BÁO: Database trống! Hãy chạy seed_vector_db.py")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        print("   Hãy chạy: python seed_vector_db.py")
        return False

def test_semantic_search():
    """Kiểm tra semantic search"""
    print("\n" + "="*60)
    print("TEST 2: Semantic Search")
    print("="*60)
    
    test_queries = [
        "Laptop gaming RTX 3060",
        "Máy tính cho lập trình Python",
        "Laptop văn phòng nhẹ dưới 15 triệu",
        "Máy gaming pin lâu 144Hz",
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            results = semantic_search_products(query, top_k=3)
            if results:
                print(f"✅ Tìm được {len(results)} kết quả:")
                for i, product in enumerate(results, 1):
                    print(f"   {i}. {product['name']} - {product['price']:,.0f} VND "
                          f"(độ phù hợp: {(1-product['relevance_score'])*100:.1f}%)")
            else:
                print("❌ Không tìm được kết quả")
        except Exception as e:
            print(f"❌ Lỗi: {str(e)}")

def test_recommendations():
    """Kiểm tra product recommendations"""
    print("\n" + "="*60)
    print("TEST 3: Product Recommendations")
    print("="*60)
    
    use_cases = [
        ("gaming", 30000000),
        ("coding", 20000000),
        ("văn phòng", 15000000),
    ]
    
    for use_case, budget in use_cases:
        print(f"\n📝 Use case: {use_case}, Budget: {budget:,.0f} VND")
        try:
            recommendations = get_product_recommendations(
                use_case=use_case,
                budget=budget,
                top_k=2
            )
            if recommendations:
                print(f"✅ Tìm được {len(recommendations)} khuyến nghị:")
                for product in recommendations:
                    print(f"   - {product['name']}: {product['price']:,.0f} VND")
            else:
                print("ℹ️  Không tìm được khuyến nghị (có thể budget quá thấp)")
        except Exception as e:
            print(f"❌ Lỗi: {str(e)}")

def test_formatting():
    """Kiểm tra format output"""
    print("\n" + "="*60)
    print("TEST 4: Format Products for Chat")
    print("="*60)
    
    query = "Laptop gaming dưới 25 triệu"
    print(f"\n📝 Query: {query}")
    
    try:
        products = semantic_search_products(query, top_k=3)
        if products:
            formatted = format_products_for_chat(products)
            print("✅ Formatted output:")
            print(formatted)
        else:
            print("❌ Không tìm được sản phẩm để format")
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")

def main():
    print("\n" + "="*60)
    print("🧪 RAG MODULE TEST SUITE")
    print("="*60)
    
    # Test 1: Vector database
    db_ok = test_vector_database()
    
    if not db_ok:
        print("\n" + "!"*60)
        print("⚠️  DỪNG: Vector database chưa được seed!")
        print("!"*60)
        print("\nHãy chạy: python seed_vector_db.py")
        return
    
    # Test 2-4: Các test khác
    try:
        test_semantic_search()
        test_recommendations()
        test_formatting()
    except Exception as e:
        print(f"\n❌ Lỗi không mong muốn: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ TESTING COMPLETED")
    print("="*60)
    print("\nℹ️  Nếu tất cả test pass, RAG đã sẵn sàng sử dụng!")
    print("\n💡 Để dùng trong agent:")
    print("   - AI agent sẽ tự động gọi semantic_search_laptops khi cần")
    print("   - Hoặc import từ app.ai.rag để dùng trực tiếp\n")

if __name__ == "__main__":
    main()
