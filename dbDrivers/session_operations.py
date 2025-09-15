import logging
from typing import Optional
from datetime import datetime
from .database import DatabaseDriver
from dataclasses import dataclass


@dataclass
class MemberSession:
    id: int
    phone_number: str
    session_id: str
    created_at: datetime
    question: Optional[str] = None
    status: Optional[str] = None
    answer: Optional[str] = None

class SessionOperations(DatabaseDriver):
    """Extended DatabaseDriver class with additional member and session operations"""

    def add_member_session(self, phone_number: str, session_id: str) -> bool:
        """Add a phone number and session_id to the member_sessions table. Returns True if successful."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO member_sessions (phone_number, session_id) VALUES (?, ?)", (phone_number, session_id))
                conn.commit()
                logging.info(f"Added session entry for phone number {phone_number} with session_id {session_id}")
                return True
        except Exception as e:
            logging.error(f"Error adding session entry for phone number {phone_number}: {e}")
            return False

    def get_member_sessions(self, phone_number: str) -> list[MemberSession]:
        """Get all sessions for a phone number"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM member_sessions WHERE phone_number = ?", (phone_number,))
            rows = cursor.fetchall()
            
            return [
                MemberSession(
                    id=row[0],
                    phone_number=row[1],
                    session_id=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    question=row[4] if len(row) > 4 else None,
                    status=row[5] if len(row) > 5 else None,
                    answer=row[6] if len(row) > 6 else None
                )
                for row in rows
            ]

    def update_member_session(self, session_id: str, status: str, question: Optional[str] = None, answer: Optional[str] = None) -> bool:
        """
        Update the status and optionally question and/or answer for a specific session. Returns True if successful.
        
        Use cases:
        1. Update only status: update_member_session(session_id, "RESOLVED")
        2. Update status + question: update_member_session(session_id, "PENDING", question=query)
        3. Update status + answer: update_member_session(session_id, "RESOLVED", answer=response)
        4. Update all three: update_member_session(session_id, "RESOLVED", question=query, answer=response)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic query based on what fields are provided
                update_fields = ["status = ?"]
                params = [status]
                
                if question is not None:
                    # Get current question to append to it
                    cursor.execute("SELECT question FROM member_sessions WHERE session_id = ?", (session_id,))
                    current_row = cursor.fetchone()
                    current_question = current_row[0] if current_row and current_row[0] else ""

                    # Append new question to existing question
                    if current_question:
                        combined_question = current_question + "," + question
                    else:
                        combined_question = question

                    update_fields.append("question = ?")
                    params.append(combined_question)
                    
                if answer is not None:
                    update_fields.append("answer = ?")
                    params.append(answer)
                
                params.append(session_id)  # Add session_id for WHERE clause
                
                query = f"UPDATE member_sessions SET {', '.join(update_fields)} WHERE session_id = ?"
                cursor.execute(query, params)
                conn.commit()
                
                if cursor.rowcount > 0:
                    updated_fields = f"status: {status}"
                    if question is not None:
                        updated_fields += f", question: '{combined_question}'"
                    if answer is not None:
                        updated_fields += f", answer: '{answer}'"
                    logging.info(f"Updated session {session_id} with {updated_fields}")
                    return True
                else:
                    logging.warning(f"No session found with session_id: {session_id}")
                    return False
                    
        except Exception as e:
            logging.error(f"Error updating session {session_id}: {e}")
            return False

    def get_all_member_sessions(self, status: Optional[str] = None) -> list[dict]:
        """Get all member sessions from the database, optionally filtered by status"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if status is not None:
                cursor.execute("""
                    SELECT id, phone_number, session_id, created_at, question, status, answer
                    FROM member_sessions
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT id, phone_number, session_id, created_at, question, status, answer
                    FROM member_sessions
                    WHERE status IS NOT NULL AND status != ''
                    ORDER BY created_at DESC
                """)
            rows = cursor.fetchall()

            sessions = []
            for row in rows:
                sessions.append({
                    'id': row[0],
                    'phone_number': row[1],
                    'session_id': row[2],
                    'created_at': row[3],
                    'question': row[4],
                    'status': row[5],
                    'answer': row[6]
                })

            return sessions

    @staticmethod
    def clean_phone_number(phone_number: str) -> Optional[str]:
        """Clean phone number by removing non-digit characters"""
        cleaned_phone = ''.join(filter(str.isdigit, phone_number))
        return cleaned_phone if cleaned_phone else None