import sqlite3
import logging
from utils import setup_logging
from typing import Optional
from contextlib import contextmanager
from datetime import datetime



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
            # Create index for fast status queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_member_sessions_status ON member_sessions(status)
            """)
            
            conn.commit()
            logging.info("Database initialized successfully")

