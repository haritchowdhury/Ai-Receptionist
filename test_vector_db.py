import asyncio
import os
from dotenv import load_dotenv
from tools import query_knowledge_base, text_supervisor
from livekit.agents import RunContext

# Mock RunContext for testing
class MockRunContext:
    pass

async def test_vector_db():
    """Test the vector database functionality"""
    load_dotenv()
    
    # Check if environment variables are set
    if not os.getenv("UPSTASH_VECTOR_REST_URL") or not os.getenv("UPSTASH_VECTOR_REST_TOKEN"):
        print("ERROR: Missing Upstash environment variables")
        return
    
    print("SUCCESS: Environment variables found")
    
    # Test query_knowledge_base
    mock_context = MockRunContext()
    
    try:
        print("\nTesting vector database query...")
        result = await query_knowledge_base(mock_context, "What are your spa services?")
        print(f"Result: {result}")
        print("SUCCESS: Vector database query test completed")
        
        print("\nTesting text_supervisor fallback...")
        fallback_result = await text_supervisor(mock_context, "Test fallback query")
        print(f"Fallback result: {fallback_result}")
        print("SUCCESS: Text supervisor test completed")
        
    except Exception as e:
        print(f"ERROR: Error during testing: {e}")

if __name__ == "__main__":
    asyncio.run(test_vector_db())