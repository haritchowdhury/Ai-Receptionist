import os
from dotenv import load_dotenv
from upstash_vector import Index
from sentence_transformers import SentenceTransformer
from ai_response_formatter import format_response_with_ai

def test_sample_queries():
    """Test various sample queries against the vector database"""
    load_dotenv()
    
    # Initialize environment variables
    url = os.getenv("UPSTASH_VECTOR_REST_URL")
    token = os.getenv("UPSTASH_VECTOR_REST_TOKEN")
    namespace = os.getenv("NAMESPACE")
    
    print("=== VECTOR DATABASE QUERY TEST ===")
    print(f"Namespace: {namespace}")
    print(f"URL: {url}")
    print()
    
    if not url or not token or not namespace:
        print("❌ ERROR: Missing environment variables")
        return
    
    # Initialize vector client
    try:
        vector_client = Index(url=url, token=token)
        print("✅ Vector client initialized successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize vector client: {e}")
        return
    
    # Initialize embedding model
    try:
        model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        print("✅ Embedding model loaded successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to load embedding model: {e}")
        return
    
    # Test queries
    test_queries = [
        "What is the distance to moon from earth?"
    ]
    
    print("\n=== TESTING SAMPLE QUERIES ===\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"🔍 Query {i}: \"{query}\"")
        
        try:
            # Get embedding for the query
            query_embedding = model.encode([query])[0].tolist()
            
            # Perform vector search
            results = vector_client.query(
                vector=query_embedding,
                top_k=3,
                include_metadata=True,
                include_vectors=False,
                namespace=namespace
            )
            
            if results and len(results) > 0:
                print(f"✅ Found {len(results)} results")
                
                # Combine all relevant content for AI formatting
                combined_content = ""
                for result in results:
                    content = result.metadata.get('content', '')
                    combined_content += f"{content}\n\n"
                
                print("\n" + "="*80)
                print("📄 RAW VECTORSTORE RESPONSE:")
                print("="*80)
                for j, result in enumerate(results[:2], 1):  # Show top 2 results
                    print(f"   Result {j}:")
                    print(f"   📊 Score: {result.score:.4f}")
                    print(f"   📁 Category: {result.metadata.get('category', 'Unknown')}")
                    print(f"   📄 Title: {result.metadata.get('title', 'Unknown')}")
                    
                    # Show content preview
                    content = result.metadata.get('content', '')
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   📝 Content: {preview}")
                    print()
                
                print("="*80)
                print("🤖 AI FORMATTED RESPONSE (as Freya):")
                print("="*80)
                
                # Get AI-formatted response
                try:
                    ai_response = format_response_with_ai(combined_content.strip(), query)
                    print(f"💬 {ai_response}", type(ai_response), len(ai_response))
                except Exception as e:
                    print(f"❌ AI formatting failed: {e}")
                    print("💬 I apologize, but I'm having technical difficulties at the moment. Please call us directly, and we'll be happy to assist you.")
                
                print("="*80)
                    
            else:
                print("❌ No results found")
                
        except Exception as e:
            print(f"❌ Query failed: {e}")
        
        print("-" * 60)
        print()
    
    # Test database info
    print("=== DATABASE INFO ===")
    try:
        # Get database info/stats if available
        info = vector_client.info()
        print(f"Database info: {info}")
    except Exception as e:
        print(f"Could not retrieve database info: {e}")

if __name__ == "__main__":
    test_sample_queries()