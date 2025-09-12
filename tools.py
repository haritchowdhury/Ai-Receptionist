import logging
from logging_config import setup_logging
from livekit.agents import function_tool, RunContext
import requests
from database import DatabaseDriver

DB = DatabaseDriver()

# Global variable to store current session_id
current_session_id = None


@function_tool()
async def check_membership(
    context: RunContext,  # type: ignore
    phone_number: str) -> str:
    """
    Check if a phone number is in the members database and add it if not present.
    """
    try:
        # Access global session_id
        global current_session_id
        session_id = current_session_id or 'Unknown'
        logging.info(f"Session ID in tool: {session_id}")
        
        cleaned_phone = DB.clean_phone_number(phone_number)
        
        if not cleaned_phone:
            logging.error(f"Invalid phone number format: {phone_number}")
            return "Please provide a valid phone number." 
        
        isMember = DB.check_phone_number_exists(cleaned_phone)
        if isMember:
            #db_driver.add_member_session(cleaned_phone, context.session.agent_state)
            logging.info(f"Phone number {cleaned_phone} is already a member")
            return "You are already a member"
        else:
            createMember = DB.add_phone_number(cleaned_phone)
            if createMember:
                return "Your number has been added to member's database"
            else:
                return "You are already a member"
            
    except Exception as e:
        logging.error(f"Error processing membership for {phone_number}: {e}")
        return f"An error occurred while processing your membership request."