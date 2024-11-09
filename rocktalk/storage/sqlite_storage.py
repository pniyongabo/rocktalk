import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from devtools import debug

from models.interfaces import ChatMessage, ChatSession
from utils.datetime_utils import format_datetime, parse_datetime


class SQLiteChatStorage:
    def __init__(self, db_path: str = "chat_database.db"):
        # Ensure database directory exists
        Path(db_path).parent.mkdir(exist_ok=True, parents=True)
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Create a new connection with row factory for dict results"""
        try:
            # Connect to database (creates file if it doesn't exist)
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to database at {self.db_path}: {str(e)}"
            )

    def init_db(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    subject TEXT,
                    created_at TIMESTAMP NOT NULL,  -- Using TIMESTAMP type
                    last_active TIMESTAMP NOT NULL, -- Using TIMESTAMP type
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,   -- Using TIMESTAMP type
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                -- Indexes for better search performance
                CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                ON messages(session_id);
                
                CREATE INDEX IF NOT EXISTS idx_sessions_last_active 
                ON sessions(last_active);
                
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_messages_content 
                ON messages(content);
            """
            )

    def store_session(self, session: ChatSession):

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions 
                (session_id, title, created_at, last_active, subject, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.title,
                    format_datetime(session.created_at),
                    format_datetime(session.last_active),
                    session.subject,
                    json.dumps(session.metadata),
                ),
            )
        return session

    def save_message(self, message: ChatMessage) -> None:
        """Save a message to a chat session and update last_active"""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages 
                (session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    message.session_id,
                    message.role,
                    json.dumps(message.content),
                    format_datetime(message.created_at),
                    json.dumps(message.metadata),
                ),
            )

            # Update session's last_active timestamp
            conn.execute(
                """
                UPDATE sessions 
                SET last_active = ? 
                WHERE session_id = ?
            """,
                (format_datetime(message.created_at), message.session_id),
            )

    def _deserialize_message(self, row: sqlite3.Row) -> ChatMessage:
        """Deserialize a message from the database row"""
        return ChatMessage(
            session_id=row["session_id"],
            role=row["role"],
            content=json.loads(row["content"]),
            created_at=parse_datetime(row["timestamp"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _deserialize_session(self, row: sqlite3.Row) -> ChatSession:
        """Deserialize a session from the database row"""
        session_data = dict(row)
        return ChatSession(
            session_id=session_data["session_id"],
            title=session_data["title"],
            subject=session_data["subject"],
            created_at=parse_datetime(session_data["created_at"]),
            last_active=parse_datetime(session_data["last_active"]),
            metadata=(
                json.loads(session_data["metadata"]) if session_data["metadata"] else {}
            ),
            message_count=session_data.get("message_count"),
            first_message=(
                parse_datetime(session_data["first_message"])
                if session_data.get("first_message")
                else None
            ),
            last_message=(
                parse_datetime(session_data["last_message"])
                if session_data.get("last_message")
                else None
            ),
        )

    def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM messages 
                WHERE session_id = ? 
                ORDER BY timestamp
            """,
                (session_id,),
            )
            return [self._deserialize_message(row) for row in cursor.fetchall()]

    def search_sessions(self, query: str) -> List[ChatSession]:
        """Search sessions by content, title, or subject"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT 
                    s.*,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                WHERE m.content LIKE ?
                OR s.title LIKE ?
                OR s.subject LIKE ?
                GROUP BY s.session_id
                ORDER BY MAX(m.timestamp) DESC NULLS LAST
            """,
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            )
            return [self._deserialize_session(row) for row in cursor.fetchall()]

    def get_active_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[ChatSession]:
        """Get sessions that have messages within the date range"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT 
                    s.*,
                    MIN(m.timestamp) as first_message,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM sessions s
                INNER JOIN messages m ON s.session_id = m.session_id
                WHERE m.timestamp BETWEEN ? AND ?
                GROUP BY s.session_id
                ORDER BY MAX(m.timestamp) DESC
            """,
                (format_datetime(start_date), format_datetime(end_date)),
            )
            return [self._deserialize_session(row) for row in cursor.fetchall()]

    def get_session_info(self, session_id: str) -> ChatSession:
        """Get detailed information about a specific session"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT 
                    s.*,
                    MIN(m.timestamp) as first_message,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                WHERE s.session_id = ?
                GROUP BY s.session_id
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._deserialize_session(row)
            else:
                raise ValueError(f"No session found with id {session_id}")

    def get_recent_sessions(self, limit: int = 10) -> List[ChatSession]:
        """Get most recently active sessions"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT s.*, 
                    (SELECT COUNT(*) FROM messages WHERE messages.session_id = s.session_id) as message_count,
                    (SELECT MIN(timestamp) FROM messages WHERE messages.session_id = s.session_id) as first_message,
                    (SELECT MAX(timestamp) FROM messages WHERE messages.session_id = s.session_id) as last_message
                FROM sessions s
                ORDER BY last_active DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [self._deserialize_session(row) for row in cursor.fetchall()]

    def rename_session(self, session_id: str, new_title: str) -> None:
        """Rename a chat session"""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions 
                SET title = ?, last_active = ?
                WHERE session_id = ?
            """,
                (new_title, format_datetime(datetime.now()), session_id),
            )

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its messages"""
        with self.get_connection() as conn:
            try:
                # Start a transaction
                conn.execute("BEGIN TRANSACTION")

                # Delete all messages associated with the session
                conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

                # Delete the session itself
                result = conn.execute(
                    "DELETE FROM sessions WHERE session_id = ?", (session_id,)
                )

                # Check if a session was actually deleted
                if result.rowcount == 0:
                    raise ValueError(f"No session found with id {session_id}")

                # Commit the transaction
                conn.execute("COMMIT")
            except Exception as e:
                # If any error occurs, rollback the transaction
                conn.execute("ROLLBACK")
                raise e  # Re-raise the exception after rollback
