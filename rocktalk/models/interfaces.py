import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from langchain.schema import BaseMessage
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    session_id: str
    role: str
    content: str
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    session_id: str
    title: str
    subject: Optional[str] = None
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    message_count: Optional[int] = None
    first_message: Optional[datetime] = None
    last_message: Optional[datetime] = None

    @classmethod
    def create(
        self,
        title: str,
        subject: Optional[str] = None,
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
        last_active: Optional[datetime] = None,
    ) -> "ChatSession":
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        current_time = datetime.now()
        created_at = created_at or current_time
        last_active = last_active or created_at

        return ChatSession(
            session_id=session_id,
            title=title,
            subject=subject,
            metadata=metadata or {},
            created_at=created_at,
            last_active=last_active,
        )


class ChatExport(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]
    exported_at: datetime = Field(default_factory=datetime.now)


class StorageInterface(Protocol):
    """Protocol defining the interface for chat storage implementations"""

    def store_session(self, session: ChatSession) -> None:
        """Store a new chat session"""
        ...

    def save_message(self, message: ChatMessage) -> None:
        """Save a message to a chat session"""
        ...

    def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session"""
        ...

    def search_sessions(self, query: str) -> List[ChatSession]:
        """Search sessions by content, title, or subject"""
        ...

    def get_active_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[ChatSession]:
        """Get sessions that have messages within the date range"""
        ...

    def get_session_info(self, session_id: str) -> ChatSession:
        """Get detailed information about a specific session"""
        ...

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its messages"""
        ...

    def get_recent_sessions(self, limit: int = 10) -> List[ChatSession]:
        """Get most recently active sessions"""
        ...

    def rename_session(self, session_id: str, new_title: str) -> None:
        """Rename a chat session"""
        ...


class LLMInterface(Protocol):
    def stream(self, messages: List[BaseMessage]) -> Any: ...
