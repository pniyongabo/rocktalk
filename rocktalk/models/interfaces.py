from typing import Protocol, Any, List
from langchain.schema import BaseMessage

from typing import Optional, List, Dict, Protocol
from datetime import datetime


class StorageInterface(Protocol):
    """Protocol defining the interface for chat storage implementations"""

    def create_session(
        self,
        title: str,
        subject: Optional[str] = None,
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
        last_active: Optional[datetime] = None,
    ) -> str:
        """Create a new chat session"""
        ...

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        """Save a message to a chat session"""
        ...

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a session"""
        ...

    def search_sessions(self, query: str) -> List[Dict]:
        """Search sessions by content, title, or subject"""
        ...

    def get_active_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get sessions that have messages within the date range"""
        ...

    def get_session_info(self, session_id: str) -> Dict:
        """Get detailed information about a specific session"""
        ...

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its messages"""
        ...

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get most recently active sessions"""
        ...

    def rename_session(self, session_id: str, new_title: str) -> None:
        """Rename a chat session"""
        ...


class LLMInterface(Protocol):
    def stream(self, messages: List[BaseMessage]) -> Any: ...
