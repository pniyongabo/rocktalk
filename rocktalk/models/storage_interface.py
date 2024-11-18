from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from models.interfaces import ChatMessage, ChatSession


class StorageInterface(ABC):
    """Protocol defining the interface for chat storage implementations"""

    @abstractmethod
    def save_message(self, message: ChatMessage) -> None:
        """Save a message to a chat session"""
        ...

    @abstractmethod
    def get_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session"""
        ...

    @abstractmethod
    def search_sessions(self, query: str) -> List[ChatSession]:
        """Search sessions by content or title"""
        ...

    @abstractmethod
    def get_active_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[ChatSession]:
        """Get sessions that have messages within the date range"""
        ...

    @abstractmethod
    def update_session(self, session: ChatSession) -> None:
        """Update an existing chat session"""
        ...

    @abstractmethod
    def store_session(self, session: ChatSession) -> None:
        """Store a new chat session"""
        ...

    @abstractmethod
    def get_session(self, session_id: str) -> ChatSession:
        """Get a specific chat session"""
        ...

    @abstractmethod
    def delete_message(self, session_id: str, index: int) -> None:
        """Delete a specific message by its index.

        Args:
            session_id: ID of the session containing the message
            index: Index of the message to delete
        """
        ...

    @abstractmethod
    def delete_messages_from_index(self, session_id: str, from_index: int) -> None:
        """Delete all messages with index >= from_index for the given session."""
        ...

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete a session and its messages"""
        ...

    @abstractmethod
    def delete_all_sessions(self) -> None:
        """Delete all chat sessions and their messages"""
        ...

    @abstractmethod
    def get_recent_sessions(self, limit: int = 10) -> List[ChatSession]:
        """Get most recently active sessions"""
        ...

    @abstractmethod
    def rename_session(self, session_id: str, new_title: str) -> None:
        """Rename a chat session"""
        ...
