# tests/test_storage.py
import pytest
from datetime import datetime, timedelta
from abc import ABC
from typing import Type, Dict

from storage.storage import ChatStorage
from storage.sqlite_storage import SQLiteChatStorage
# Future implementations would be imported here
# from storage.postgres_storage import PostgresChatStorage

class AbstractStorageTest(ABC):
    """
    Abstract base class for storage tests.
    Any new storage implementation should be tested using this suite.
    """
    
    storage_class: Type[ChatStorage] = None
    
    @pytest.fixture
    def storage(self) -> ChatStorage:
        """Should be implemented by concrete test classes"""
        raise NotImplementedError
        
    @pytest.fixture
    def sample_session(self, storage: ChatStorage) -> Dict:
        """Create a sample session with messages for testing"""
        session_id = storage.create_session(
            title="Test Session",
            subject="Testing",
            metadata={"test": True}
        )
        
        # Add some test messages
        messages = [
            ("user", "Hello"),
            ("assistant", "Hi there"),
            ("user", "How are you?"),
            ("assistant", "I'm doing well")
        ]
        
        for role, content in messages:
            storage.save_message(
                session_id=session_id,
                role=role,
                content=content,
                metadata={"test": True}
            )
            
        return {"session_id": session_id, "messages": messages}

    def test_create_session(self, storage: ChatStorage):
        """Test creating a new session"""
        session_id = storage.create_session(
            title="Test Session",
            subject="Testing",
            metadata={"test": True}
        )
        
        session_info = storage.get_session_info(session_id)
        assert session_info["title"] == "Test Session"
        assert session_info["subject"] == "Testing"
        assert session_info["message_count"] == 0

    def test_save_and_retrieve_message(self, storage: ChatStorage, sample_session):
        """Test saving and retrieving messages"""
        session_id = sample_session["session_id"]
        
        # Get all messages
        messages = storage.get_session_messages(session_id)
        
        # Verify message count
        assert len(messages) == len(sample_session["messages"])
        
        # Verify message content
        for saved_msg, (role, content) in zip(messages, sample_session["messages"]):
            assert saved_msg["role"] == role
            assert saved_msg["content"] == content

    def test_date_range_search(self, storage: ChatStorage, sample_session):
        """Test searching sessions by date range"""
        now = datetime.now()
        
        # Should find our session
        recent_sessions = storage.get_active_sessions_by_date_range(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1)
        )
        assert len(recent_sessions) == 1
        assert recent_sessions[0]["session_id"] == sample_session["session_id"]
        
        # Should not find any sessions
        old_sessions = storage.get_active_sessions_by_date_range(
            start_date=now - timedelta(days=2),
            end_date=now - timedelta(days=1)
        )
        assert len(old_sessions) == 0

    def test_search_sessions(self, storage: ChatStorage, sample_session):
        """Test searching sessions"""
        # Search by content
        results = storage.search_sessions("Hello")
        assert len(results) == 1
        assert results[0]["session_id"] == sample_session["session_id"]
        
        # Search by title
        results = storage.search_sessions("Test Session")
        assert len(results) == 1
        
        # Search with no matches
        results = storage.search_sessions("NonexistentContent")
        assert len(results) == 0

    def test_delete_session(self, storage: ChatStorage, sample_session):
        """Test deleting a session"""
        session_id = sample_session["session_id"]
        
        # Verify session exists
        assert storage.get_session_info(session_id) is not None
        
        # Delete session
        storage.delete_session(session_id)
        
        # Verify session is gone
        with pytest.raises(Exception):  # Specific exception type depends on implementation
            storage.get_session_info(session_id)

class TestSQLiteStorage(AbstractStorageTest):
    """Concrete test class for SQLite implementation"""
    
    storage_class = SQLiteChatStorage
    
    @pytest.fixture
    def storage(self, tmp_path) -> ChatStorage:
        """Create a temporary SQLite database for testing"""
        db_path = tmp_path / "test_chat.db"
        return SQLiteChatStorage(db_path=str(db_path))

# Future implementation tests would follow the same pattern
# class TestPostgresStorage(AbstractStorageTest):
#     storage_class = PostgresChatStorage
#     
#     @pytest.fixture
#     def storage(self) -> ChatStorage:
#         # Setup test postgres database
#         pass
