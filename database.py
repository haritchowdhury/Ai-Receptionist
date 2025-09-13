import sqlite3
import logging
from logging_config import setup_logging
from typing import Optional
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Member:
    id: int
    phone_number: str
    created_at: datetime

@dataclass
class MemberSession:
    id: int
    phone_number: str
    session_id: str
    created_at: datetime
    question: Optional[str] = None
    status: Optional[str] = None
    answer: Optional[str] = None

class DatabaseDriver:
    def __init__(self, db_path: str = "members.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create members table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create member_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS member_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    question TEXT,
                    status TEXT,
                    answer TEXT
                )
            """)
            
            conn.commit()
            logging.info("Database initialized successfully")

