import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

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
        Be polite, classy, and brief - answer in 1-2 sentences maximum.
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

def format_greeting() -> str:
    """
    Returns the standard greeting for starting a conversation
    """
    return "Hi my name is Freya, this is Bliss Salon, how may I help you?"