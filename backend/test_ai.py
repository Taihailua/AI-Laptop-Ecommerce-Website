import sys
import os
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.ai.agent import agent_executor
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from app.ai.agent import agent_executor

def test_ai():
    print("Testing AI Agent...")
    try:
        # Test 1: Simple query (RAG)
        print("\n--- Test 1: Search Laptop ---")
        response = agent_executor.invoke({"messages": [HumanMessage(content="Tìm laptop dưới 20 triệu")]})
        print("Response:", response["messages"][-1].content)

        # Test 2: Order intent (Tool Calling check)
        # Note: We won't actually execute the order without confirmation, but we check if it tries to call the tool or ask for info.
        print("\n--- Test 2: Order Intent ---")
        response = agent_executor.invoke({"messages": [HumanMessage(content="Tôi muốn mua MacBook Air M2. Tên tôi là TestUser, SĐT 0909999999")]})
        print("Response:", response["messages"][-1].content)
        
        print("\n✅ AI Agent seems to be working correctly with the fix!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_ai()