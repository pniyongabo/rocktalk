# storage_interface.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict

class ChatStorage(ABC):
    """Abstract base class defining the interface for chat storage implementations"""
    
    @abstractmethod
    def create_session(self, title: str, subject: Optional[str] = None, 
                      metadata: Optional[Dict] = None) -> str:
        """Create a new chat session"""
        pass

    @abstractmethod
    def save_message(self, session_id: str, role: str, content: str, 
                    metadata: Optional[Dict] = None):
        """Save a message to a chat session"""
        pass

    @abstractmethod
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a session"""
        pass

    @abstractmethod
    def search_sessions(self, query: str) -> List[Dict]:
        """Search sessions by content, title, or subject"""
        pass

    @abstractmethod
    def get_active_sessions_by_date_range(self, start_date: datetime, 
                                        end_date: datetime) -> List[Dict]:
        """Get sessions that have messages within the date range"""
        pass

    @abstractmethod
    def get_session_info(self, session_id: str) -> Dict:
        """Get detailed information about a specific session"""
        pass

    @abstractmethod
    def delete_session(self, session_id: str):
        """Delete a session and its messages"""
        pass

    @abstractmethod
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get most recently active sessions"""
        pass

    @abstractmethod
    def rename_session(self, session_id: str, new_title: str):
        """Rename a chat session"""
        pass