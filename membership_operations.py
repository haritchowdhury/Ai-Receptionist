import sqlite3
import logging
from typing import Optional
from datetime import datetime
from database import DatabaseDriver, Member, MemberSession


class MembershipOperations(DatabaseDriver):
    """Extended DatabaseDriver class with additional member and session operations"""
    
    def check_phone_number_exists(self, phone_number: str) -> bool:
        """Check if a phone number exists in the members database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT phone_number FROM members WHERE phone_number = ?", (phone_number,))
            existing_member = cursor.fetchone()
            return existing_member is not None

    def add_phone_number(self, phone_number: str) -> bool:
        """Add a phone number to the members database. Returns True if successful."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO members (phone_number) VALUES (?)", (phone_number,))
                conn.commit()
                logging.info(f"Phone number {phone_number} added to members database")
                return True
        except sqlite3.IntegrityError:
            logging.error(f"Phone number {phone_number} already exists")
            return False
        except Exception as e:
            logging.error(f"Error adding phone number {phone_number}: {e}")
            return False

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

    def get_member_by_phone(self, phone_number: str) -> Optional[Member]:
        """Get member by phone number"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM members WHERE phone_number = ?", (phone_number,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return Member(
                id=row[0],
                phone_number=row[1],
                created_at=datetime.fromisoformat(row[2])
            )

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
                    created_at=datetime.fromisoformat(row[3])
                )
                for row in rows
            ]

    @staticmethod
    def clean_phone_number(phone_number: str) -> Optional[str]:
        """Clean phone number by removing non-digit characters"""
        cleaned_phone = ''.join(filter(str.isdigit, phone_number))
        return cleaned_phone if cleaned_phone else None