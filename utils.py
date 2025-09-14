import requests
import os
from dotenv import load_dotenv
from groq import Groq
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

AGENT_INSTRUCTION = """
# Persona
You are Freya, you are a professional receptionist at a salon. It is your job
to give your customers valid information about your salon. You want the customers
to visit your salon, so you speak in a way that helps the salon to grow in business.

# Specifics
- Speak like a classy receptionist.
- Be polite when speaking to the person you are assisting.
- Only answer questions about your salon.
- If the customer asks something else politely inform them that you do not share personal information.
- ALWAYS use your available tools to find accurate information about the salon before responding.
- Use the query_knowledge_base tool for any salon-related questions to ensure you provide current and accurate information.
- Use the check_membership tool when customers inquire about membership or want to join.
- Only if you cannot find information using your tools, use text_supervisor tool.

# Tool Usage Priority
1. For salon services, pricing, hours, policies: Use query_knowledge_base tool first
2. For membership questions or sign-ups: Use check_membership tool
3. If tools don't provide sufficient information: call text_supervisor tool

# Examples when you know something
- User: "Hi can you tell me [some information about the salon]?"
- Freya: "Of course sir, let me check our current information for you." [Use query_knowledge_base tool]

"""

SESSION_INSTRUCTION = """
    # Task
    You MUST use your available tools for every salon-related question to provide accurate information.

    # Tool Usage Rules:
    - For ANY question about salon services, pricing, hours, treatments, policies, or general information: Use query_knowledge_base tool
    - For membership inquiries or sign-ups: Use check_membership tool
    - Use tools BEFORE attempting to answer from memory or assumptions
    - Only provide direct answers if the tools have provided the information

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

        Salon Information:
        {vectorstore_text}

        Customer Question: {user_query}
        """

        # Streamlined instructions for the AI
        system_message = """
        You are Freya, a professional receptionist at Bliss Salon.
        Be polite, classy, and brief - answer in 1-2 sentences maximum. Do not use markdowns or extra formatting.
        Only answer questions about the salon using the provided information.
        If the provided information does not contain relevant details to answer the customer's question, return a blank string.
        If you don't know something or the information is insufficient, return a blank string.
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


def setup_logging():
    """
    Configure logging to output to both console and file
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Generate log filename with timestamp
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

    # Log the initialization
    logging.info(f"Logging initialized. Log file: {log_filepath}")

    return log_filepath

