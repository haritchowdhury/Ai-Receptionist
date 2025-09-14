import logging
from livekit.agents import function_tool, RunContext
from dbDrivers.session_operations import SessionOperations
import os
from upstash_vector import Index
import json
from utils import format_response_with_ai, setup_logging, get_huggingface_embedding

db = SessionOperations()

# Global variable to store current session_id
current_session_id = None
current_phone_number = None


@function_tool()
async def query_knowledge_base(
    context: RunContext,
    query: str
) -> str:
    """
    Query the vector database for spa-related information, FAQs, and customer support documents.
    Falls back to text_supervisor if no relevant information is found.

    Args:
        query: The user's question or search query
    """
    try:
        logging.info(f"query_knowledge_base called with query: {query}")
        # Initialize Upstash Vector client
        vector_client = Index(
            url=os.getenv("UPSTASH_VECTOR_REST_URL"),
            token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        )
        
        # Get embedding for the query using HuggingFace API
        hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        query_embedding = get_huggingface_embedding(query, hf_api_key)
        
        # Query the vector database using vector embedding with namespace
        namespace = os.getenv("NAMESPACE")
        results = vector_client.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True,
            include_vectors=False,
            namespace=namespace
        )
        
        # Debug logging
        logging.info(f"Query results: {len(results) if results else 0} results found")
        if results and len(results) > 0:
            logging.info(f"Top result score: {results[0].score}")
        
        # Check if we have relevant results (lowered similarity threshold)
        if results and len(results) > 0 and results[0].score > 0.7:
            # Combine all relevant content for AI formatting
            combined_content = ""
            for result in results:
                if result.metadata:
                    content = result.metadata.get('content', '')
                    combined_content += f"{content}\n\n"
            
            # Use AI formatter to create professional receptionist response
            try:
                ai_response = format_response_with_ai(combined_content.strip(), query)
                if len(ai_response) == 0:
                    logging.info(f"Vector database did not return relevant results")
                    return await text_supervisor(context, query)
                else:
                    logging.info(f"Vector database returned relevant results for query: {query}")
                    logging.info(f"Ai's response: {ai_response}")
                    return ai_response
            except Exception as e:
                logging.error(f"AI formatting failed, falling back to raw response: {e}")
                # Fallback to original formatting if AI fails
                response = "Based on our spa information:\n\n"
                for i, result in enumerate(results[:2]):  # Use top 2 results
                    if result.metadata:
                        content = result.metadata.get('content', 'No content available')
                        category = result.metadata.get('category', '')
                        title = result.metadata.get('title', '')
                        
                        # Add some structure to the response
                        if title and title != category:
                            response += f"{title}\n"
                        response += f"{content}\n\n"
                
                logging.info(f"Vector database returned relevant results for query: {query}")
                return response.strip()
        else:
            # No relevant results found, fall back to text_supervisor
            logging.info(f"No relevant results in vector database for query: {query}, falling back to text_supervisor")
            return await text_supervisor(context, query)
            
    except Exception as e:
        logging.error(f"Error querying vector database: {e}")
        # Fall back to text_supervisor on error
        return await text_supervisor(context, query)

@function_tool()
async def text_supervisor(
    context: RunContext,
    query: str
) -> str:
    """
    Fallback function when vector database doesn't have relevant information.
    Updates the current session with the query and sets status to PENDING.
    
    Args:
        query: The user's question or search query
    """
    global current_session_id
    session_id = current_session_id or 'Unknown'
    
    logging.info(f"Text supervisor called with query: {query}")
    
    # Update the current session with the question and status
    if session_id != 'Unknown':
        try:
            update_success = db.update_member_session(session_id, "PENDING", question=query)
            if update_success:
                logging.info(f"Updated session {session_id} with question and PENDING status")
            else:
                logging.warning(f"Failed to update session {session_id}")
        except Exception as e:
            logging.error(f"Error updating session status: {e}")
    else:
        logging.warning("Session ID is unknown, cannot update session status")
    
    return "I don't have specific information about that in our spa knowledge base. Let me check with my supervisor, I will get back to you over text message."