import os
from dotenv import load_dotenv
from upstash_vector import Index
import hashlib
from sentence_transformers import SentenceTransformer

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks for better vector search"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks

def create_vector_id(text):
    """Create a unique ID for each text chunk"""
    return hashlib.md5(text.encode()).hexdigest()

def get_embeddings(texts, model):
    """Get embeddings using sentence-transformers"""
    embeddings = model.encode(texts)
    return embeddings.tolist()

def ingest_salon_data():
    """Ingest salon data into Upstash Vector database"""
    load_dotenv()
    
    # Check environment variables
    if not os.getenv("UPSTASH_VECTOR_REST_URL") or not os.getenv("UPSTASH_VECTOR_REST_TOKEN"):
        print("ERROR: Missing Upstash environment variables")
        return
    
    namespace = os.getenv("NAMESPACE")
    if not namespace:
        print("ERROR: Missing NAMESPACE environment variable")
        return
    
    # Initialize embedding model
    try:
        print("INFO: Loading BAAI/bge-small-en-v1.5 model...")
        model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        print("SUCCESS: Model loaded")
    except Exception as e:
        print(f"ERROR: Failed to load embedding model: {e}")
        return
    
    # Initialize Upstash Vector client
    try:
        vector_client = Index(
            url=os.getenv("UPSTASH_VECTOR_REST_URL"),
            token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        )
        print(f"SUCCESS: Connected to Upstash Vector database with namespace: {namespace}")
    except Exception as e:
        print(f"ERROR: Failed to connect to vector database: {e}")
        return
    
    # Read salon data
    try:
        with open('salon_data.txt', 'r', encoding='utf-8') as file:
            content = file.read()
        print("SUCCESS: Loaded salon data file")
    except Exception as e:
        print(f"ERROR: Failed to read salon data file: {e}")
        return
    
    # Split content into logical sections
    sections = content.split('=== ')
    processed_sections = []
    
    for section in sections:
        if section.strip():
            # Clean up section header
            if section.startswith('LUXURY SPA'):
                section_title = "General Information"
                section_content = section
            else:
                lines = section.split('\n', 1)
                section_title = lines[0].replace('===', '').strip()
                section_content = lines[1] if len(lines) > 1 else ""
            
            # Further chunk large sections
            if len(section_content) > 1000:
                chunks = chunk_text(section_content, chunk_size=400, overlap=50)
                for i, chunk in enumerate(chunks):
                    processed_sections.append({
                        'title': f"{section_title} - Part {i+1}",
                        'content': chunk.strip(),
                        'category': section_title
                    })
            else:
                processed_sections.append({
                    'title': section_title,
                    'content': section_content.strip(),
                    'category': section_title
                })
    
    print(f"INFO: Created {len(processed_sections)} sections for ingestion")
    
    # Reset/clear the namespace before inserting new data
    try:
        print(f"INFO: Resetting namespace '{namespace}'...")
        vector_client.reset(namespace=namespace)
        print("SUCCESS: Namespace reset completed")
    except Exception as e:
        print(f"WARNING: Failed to reset namespace (this is okay if namespace doesn't exist yet): {e}")
    
    # Prepare texts for embedding
    texts_to_embed = [section['content'] for section in processed_sections]
    
    # Get embeddings using the model
    try:
        print("INFO: Generating embeddings...")
        embeddings = get_embeddings(texts_to_embed, model)
        print(f"SUCCESS: Generated {len(embeddings)} embeddings")
    except Exception as e:
        print(f"ERROR: Failed to get embeddings: {e}")
        return
    
    # Ingest data into vector database with batch processing
    successful_inserts = 0
    failed_inserts = 0
    batch_size = 500
    batch = []
    
    for i, section in enumerate(processed_sections):
        try:
            vector_id = create_vector_id(section['content'])
            
            # Create vector data in correct dictionary format for Upstash
            vector_data = {
                "id": vector_id,
                "vector": embeddings[i],
                "metadata": {
                    'title': section['title'],
                    'category': section['category'],
                    'content': section['content']
                },
                "data": section['content']
            }
            
            batch.append(vector_data)
            
            # Process batch when it reaches batch_size or is the last item
            if len(batch) >= batch_size or i == len(processed_sections) - 1:
                try:
                    response = vector_client.upsert(
                        vectors=batch,
                        namespace=namespace
                    )
                    successful_inserts += len(batch)
                    print(f"SUCCESS: Batch processed {len(batch)} vectors. Response: {response}")
                    batch = []  # Clear batch
                except Exception as batch_error:
                    failed_inserts += len(batch)
                    print(f"ERROR: Failed to process batch of {len(batch)} vectors: {batch_error}")
                    batch = []  # Clear batch even on error
            
        except Exception as e:
            failed_inserts += 1
            print(f"ERROR: Failed to prepare vector for '{section['title']}': {e}")
    
    print(f"\nINGESTION COMPLETE:")
    print(f"Successful inserts: {successful_inserts}")
    print(f"Failed inserts: {failed_inserts}")
    

if __name__ == "__main__":
    ingest_salon_data()