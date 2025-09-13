import logging
from logging_config import setup_logging
from livekit.agents import function_tool, RunContext
import requests
from membership_operations import MembershipOperations
import os
from upstash_vector import Index
import json
from ai_response_formatter import format_response_with_ai

Member = MembershipOperations()

# Global variable to store current session_id
current_session_id = None
current_phone_number = None

# HuggingFace embedding configuration
def get_huggingface_embedding(text, api_key, model_name="BAAI/bge-small-en-v1.5"):
    """Get embeddings from HuggingFace Inference API"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    url = f"https://api-inference.huggingface.co/models/{model_name}"

    response = requests.post(
        url,
        headers=headers,
        json={"inputs": text}
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"HuggingFace API error: {response.status_code} - {response.text}")


@function_tool()
async def check_membership(
    context: RunContext,  # type: ignore
    ) -> str:
    """
    Check if a phone number is in the members database and add it if not present.
    """
    try:
        logging.info(f"check_membership called")
        # Access global session_id
        global current_session_id
        session_id = current_session_id or 'Unknown'
        global current_phone_number
        phone_number = current_phone_number or 'Unknown'
        logging.info(f"Session ID in tool: {session_id}")
        
        cleaned_phone = Member.clean_phone_number(phone_number)
        
        if not cleaned_phone:
            logging.error(f"Invalid phone number format: {phone_number}")
            return "Please provide a valid phone number." 
        
        isMember = Member.check_phone_number_exists(cleaned_phone)
        if isMember:
            #db_driver.add_member_session(cleaned_phone, context.session.agent_state)
            logging.info(f"Phone number {cleaned_phone} is already a member")
            return "You are already a member"
        else:
            createMember = Member.add_phone_number(cleaned_phone)
            if createMember:
                return "Your number has been added to member's database"
            else:
                return "You are already a member"
            
    except Exception as e:
        logging.error(f"Error processing membership for {phone_number}: {e}")
        return f"An error occurred while processing your membership request."

# Removed get_query_embedding function - now using local sentence-transformers model

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
                            response += f"**{title}**\n"
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
    global current_phone_number
    phone_number = current_phone_number or 'Unknown'
    
    logging.info(f"Text supervisor called with query: {query}")
    
    # Update the current session with the question and status
    if session_id != 'Unknown':
        try:
            update_success = Member.update_member_session(session_id, "PENDING", question=query)
            if update_success:
                logging.info(f"Updated session {session_id} with question and PENDING status")
            else:
                logging.warning(f"Failed to update session {session_id}")
        except Exception as e:
            logging.error(f"Error updating session status: {e}")
    else:
        logging.warning("Session ID is unknown, cannot update session status")
    
    return "I don't have specific information about that in our spa knowledge base. Let me help you with general assistance or you can contact our spa directly for more detailed information."