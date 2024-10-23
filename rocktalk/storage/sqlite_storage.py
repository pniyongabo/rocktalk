import sqlite3
from datetime import datetime
import uuid
import json
from typing import Optional, List, Dict
from pathlib import Path
from .storage import ChatStorage

class SQLiteChatStorage(ChatStorage):
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
            raise RuntimeError(f"Failed to connect to database at {self.db_path}: {str(e)}")

    def init_db(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP,
                    last_active TIMESTAMP,
                    subject TEXT,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                );

                -- Indexes for better search performance
                CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                ON messages(session_id);
                
                CREATE INDEX IF NOT EXISTS idx_sessions_last_active 
                ON chat_sessions(last_active);
                
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_messages_content 
                ON messages(content);
            ''')

    def create_session(self, title: str, subject: Optional[str] = None, 
                  metadata: Optional[Dict] = None,
                  created_at: Optional[datetime] = None,
                  last_active: Optional[datetime] = None) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        # Use provided timestamps or default to current time
        created_at = created_at or current_time
        last_active = last_active or created_at
        
        # Format timestamps consistently
        created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
        last_active_str = last_active.strftime('%Y-%m-%d %H:%M:%S')
        
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO chat_sessions 
                (session_id, title, created_at, last_active, subject, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, title, created_at_str, last_active_str, subject, 
                json.dumps(metadata) if metadata else None))
        return session_id

    def save_message(self, session_id: str, role: str, content: str, 
                    metadata: Optional[Dict] = None,
                    created_at: Optional[datetime] = None):
        """Save a message to a chat session and update last_active"""
        current_time = datetime.now()
        message_time = created_at or current_time
        
        # Format timestamp consistently
        message_time_str = message_time.strftime('%Y-%m-%d %H:%M:%S')
        
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO messages 
                (message_id, session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(uuid.uuid4()), session_id, role, content, 
                message_time_str, json.dumps(metadata) if metadata else None))
            
            # Update session's last_active timestamp
            conn.execute('''
                UPDATE chat_sessions 
                SET last_active = ? 
                WHERE session_id = ?
            ''', (message_time_str, session_id))



    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a session"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM messages 
                WHERE session_id = ? 
                ORDER BY timestamp
            ''', (session_id,))
            return [dict(row) for row in cursor.fetchall()]

    def search_sessions(self, query: str) -> List[Dict]:
        """Search sessions by content, title, or subject"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT DISTINCT 
                    s.*,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM chat_sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                WHERE m.content LIKE ?
                OR s.title LIKE ?
                OR s.subject LIKE ?
                GROUP BY s.session_id
                ORDER BY MAX(m.timestamp) DESC NULLS LAST
            ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
            return [dict(row) for row in cursor.fetchall()]

    def get_active_sessions_by_date_range(self, start_date: datetime, 
                                        end_date: datetime) -> List[Dict]:
        """Get sessions that have messages within the date range"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT DISTINCT 
                    s.*,
                    MIN(m.timestamp) as first_message,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM chat_sessions s
                INNER JOIN messages m ON s.session_id = m.session_id
                WHERE m.timestamp BETWEEN ? AND ?
                GROUP BY s.session_id
                ORDER BY MAX(m.timestamp) DESC
            ''', (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]

    def get_session_info(self, session_id: str) -> Dict:
        """Get detailed information about a specific session"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    s.*,
                    MIN(m.timestamp) as first_message,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM chat_sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                WHERE s.session_id = ?
                GROUP BY s.session_id
            ''', (session_id,))
            return dict(cursor.fetchone())

    def delete_session(self, session_id: str):
        """Delete a session and its messages"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
            conn.execute('DELETE FROM chat_sessions WHERE session_id = ?', (session_id,))

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get most recently active sessions"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT DISTINCT 
                    s.*,
                    MAX(m.timestamp) as last_message,
                    COUNT(m.message_id) as message_count
                FROM chat_sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                GROUP BY s.session_id
                ORDER BY s.last_active DESC, s.created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def rename_session(self, session_id: str, new_title: str):
        """Rename a chat session"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE chat_sessions 
                SET title = ?, last_active = ?
                WHERE session_id = ?
            ''', (new_title, datetime.now(), session_id))