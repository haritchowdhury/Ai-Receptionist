import requests
import os
from dotenv import load_dotenv
from groq import Groq
import logging
from datetime import datetime
import hashlib
from upstash_vector import Index
from sentence_transformers import SentenceTransformer
import json

# Load environment variables
load_dotenv()

AGENT_INSTRUCTION = """
<persona>
You are Freya, you are a receptionist at Bliss salon. It is your job
to give your customers appropriate information about your salon. You want the customers
to visit your salon, so you speak in a way that helps the salon to grow in business.
</persona>

<specifications>
- Be polite.
- Only answer questions about your salon.
- If the customer asks something else politely inform them that you can only answer to relevant questions.
- ALWAYS use your available tools to find accurate information about the salon before responding.
- Use the <tool_name> query_knowledge_base </tool_name> tool for any salon-related questions to ensure you provide current and accurate information.
- Only if you cannot find information using <tool_name> query_knowledge_base </tool_name> tool, use <tool_name> text_supervisor </tool_name> tool.
</specifications>


<tool_usage_priority>
1. For salon services, pricing, hours, policies: Use <tool_name> query_knowledge_base </tool_name> tool first
2. If tools don't provide sufficient information: call <tool_name> text_supervisor </tool_name> tool
</tool_usage_priority>

<example_qa>
<user_query> "Hi can you tell me <question /> ?" </user_query>
<assistant_response> "Yes, we do provide <answer /> " </assistant_response>
</example_qa>

<example_qa>
<user_query> "Are you <question /> ?" </user_query>
<assistant_response> "Now we do not <answer /> " </assistant_response>
</example_qa>

<example_qa>
<user_query> "What is the <question /> ?" </user_query>
<case> 
    <tool_call> 
        <tool_name> query_knowledge_base </tool_name> does not return relevant information.
    </tool_call> 
    use 
    <tool_call> 
        <tool_name> text_supervisor </tool_name>
    </tool_call> 
</case>
<assistant_response> "I currently do not have the information, let me check with my supervisor and get back to you over text." </assistant_response>
</example_qa>

"""

SESSION_INSTRUCTION = """
    <task>
        You MUST use your available tools for every salon-related question to provide accurate information.
    </task>
    <tool_usage_rules>
        - For ANY question about salon services, pricing, hours, treatments, policies, or general information: Use <tool_name> query_knowledge_base </tool_name> tool
        - Use tools BEFORE attempting to answer from memory or assumptions
        - Only provide direct answers if the tools have provided the information
    </tool_usage_rules>
    Begin the conversation by saying: " Hi my name is Freya, this is Bliss Salon, how may I help you? "
"""


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


def format_response_with_ai(
    vectorstore_text: str,
    user_query: str,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.7
) -> str:
    """
    Takes text from vectorstore and formats it as a proper salon receptionist response
    using Groq AI based on the instructions.

    Args:
        vectorstore_text: Raw text retrieved from vectorstore
        user_query: The customer's original question
        model: Groq model to use
        temperature: Response creativity (0-1)

    Returns:
        Formatted response as Freya the receptionist
    """
    try:
        # Initialize Groq client
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # Create context from vectorstore text
        context_prompt = f"""
        Based on the following salon information, provide a response as Freya the receptionist:

        <salon_information>
        {vectorstore_text}
        </salon_information>

        <customer_query> 
        {user_query}
        </customer_query> 
        """

        # Streamlined instructions for the AI
        system_message = """
        You are Freya, a receptionist at Bliss Salon.
        <character_traits>
        - Avoid unnecessary pleasantries. 
        - Be polite, classy, and brief - answer in 1-2 sentences maximum.
        - Do not use markdowns or extra formatting.
        - Only answer questions about the salon using the provided information.
        - If the provided information does not contain relevant details to answer the customer's question, return a blank string.
        - If you don't know something or the information is insufficient, return a blank string.
        </character_traits>
        """

        # Make API call to Groq
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": context_prompt}
            ],
            temperature=temperature,
            max_tokens=150
        )

        return completion.choices[0].message.content

    except Exception as error:
        # Print the actual error for debugging (avoid emoji for Windows compatibility)
        print(f"AI Formatter Error: {str(error)}")
        print(f"Error Type: {type(error).__name__}")
        # Fallback response in case of API error
        return "I apologize, but I'm having technical difficulties at the moment. Please call us directly, and we'll be happy to assist you."


def setup_logging(session_id=None):
    """
    Configure logging to output to both console and file with graceful error handling
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Generate log filename with session_id if provided, otherwise use timestamp
    if session_id:
        log_filename = f"ai_receptionist_{session_id}.log"
    else:
        log_filename = f"ai_receptionist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Create file handler
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configure specific loggers to handle expected errors gracefully
    # Suppress verbose Cartesia connection errors in favor of clean messages
    cartesia_logger = logging.getLogger("livekit.plugins.cartesia")
    cartesia_logger.setLevel(logging.WARNING)

    # Add custom filter for Cartesia connection errors
    class CartesiaErrorFilter(logging.Filter):
        def filter(self, record):
            # Convert stack traces to simple messages for expected connection errors
            if "Cartesia connection closed unexpectedly" in str(record.getMessage()):
                record.msg = "TTS connection temporarily interrupted - retrying automatically"
                record.levelno = logging.INFO
                record.levelname = "INFO"
                return True
            if "APIConnectionError" in str(record.getMessage()) and "cartesia" in str(record.pathname).lower():
                record.msg = "TTS service reconnecting - temporary interruption"
                record.levelno = logging.INFO
                record.levelname = "INFO"
                return True
            return True

    # Apply filter to all handlers
    error_filter = CartesiaErrorFilter()
    for handler in root_logger.handlers:
        handler.addFilter(error_filter)

    # Log the initialization
    logging.info(f"Logging initialized. Log file: {log_filepath}")

    return log_filepath

def initialize_vector_components():
    """Initialize embedding model and vector client"""
    global embedding_model, vector_client

    try:
        # Initialize embedding model
        if embedding_model is None:
            embedding_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
            print("SUCCESS: Embedding model loaded")

        # Initialize Upstash Vector client
        if vector_client is None:
            if not os.getenv("UPSTASH_VECTOR_REST_URL") or not os.getenv("UPSTASH_VECTOR_REST_TOKEN"):
                print("WARNING: Missing Upstash environment variables - vector ingestion disabled")
                return False

            vector_client = Index(
                url=os.getenv("UPSTASH_VECTOR_REST_URL"),
                token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
            )
            print("SUCCESS: Connected to Upstash Vector database")

        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize vector components: {e}")
        return False

def create_vector_id(text):
    """Create a unique ID for each text"""
    return hashlib.md5(text.encode()).hexdigest()

def ingest_qa_to_vector_db(question, answer, session_id):
    """Ingest question-answer pair into vector database"""
    if not initialize_vector_components():
        print("WARNING: Vector database components not available - skipping ingestion")
        return False

    try:
        namespace = os.getenv("NAMESPACE")
        if not namespace:
            print("WARNING: Missing NAMESPACE environment variable - skipping vector ingestion")
            return False

        # Combine question and answer for better context
        qa_content = f"Q: {question}\nA: {answer}"

        # Get embedding
        embedding = embedding_model.encode([qa_content]).tolist()[0]

        # Create vector data
        vector_id = create_vector_id(qa_content)
        vector_data = {
            "id": vector_id,
            "vector": embedding,
            "metadata": {
                'title': f"Q&A - Session {session_id}",
                'category': 'Customer_QA',
                'question': question,
                'answer': answer,
                'session_id': session_id,
                'content': qa_content
            },
            "data": qa_content
        }

        # Upsert to vector database
        response = vector_client.upsert(
            vectors=[vector_data],
            namespace=namespace
        )

        print(f"SUCCESS: Q&A ingested to vector database for session {session_id}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to ingest Q&A to vector database: {e}")
        return False