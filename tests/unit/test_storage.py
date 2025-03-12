import json
from datetime import datetime, timedelta, timezone

import pytest

from rocktalk.models.interfaces import (
    ChatContentItem,
    ChatMessage,
    ChatSession,
    LLMConfig,
)
from rocktalk.models.storage.storage_interface import SearchOperator


def test_create_session(temp_database, test_session):
    """Test creating a new chat session"""
    # Store the session
    temp_database.store_session(test_session)

    # Retrieve and verify
    sessions = temp_database.get_recent_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == test_session.session_id
    assert sessions[0].title == test_session.title


def test_save_and_retrieve_messages(temp_database, test_session, test_messages):
    """Test saving and retrieving messages"""
    # Store the session and messages
    temp_database.store_session(test_session)
    for message in test_messages:
        temp_database.save_message(message)

    # Retrieve and verify messages
    retrieved_messages = temp_database.get_messages(test_session.session_id)
    assert len(retrieved_messages) == len(test_messages)

    for orig, retrieved in zip(test_messages, retrieved_messages):
        assert retrieved.session_id == orig.session_id
        assert retrieved.role == orig.role
        assert retrieved.index == orig.index
        assert len(retrieved.content) == len(orig.content)
        assert retrieved.content[0].text == orig.content[0].text


def test_delete_message(temp_database, test_session, test_messages):
    """Test deleting a specific message"""
    # Store the session and messages
    temp_database.store_session(test_session)
    for message in test_messages:
        temp_database.save_message(message)

    # Delete the first message
    temp_database.delete_message(test_session.session_id, 0)

    # Verify message was deleted and indexes were updated
    messages = temp_database.get_messages(test_session.session_id)
    assert len(messages) == 1
    assert messages[0].index == 0  # Index should have been updated
    assert messages[0].content[0].text == "I'm doing well, thank you for asking!"


def test_search_sessions(temp_database, test_session, test_messages):
    """Test searching sessions"""
    # Store the session and messages
    temp_database.store_session(test_session)
    for message in test_messages:
        temp_database.save_message(message)

    # Search for a term that should match
    results = temp_database.search_sessions(["hello"], operator=SearchOperator.AND)
    assert len(results) == 1
    assert results[0].session_id == test_session.session_id

    # Search for a term that shouldn't match
    results = temp_database.search_sessions(
        ["nonexistent"], operator=SearchOperator.AND
    )
    assert len(results) == 0

    # Test AND operator with multiple terms
    results = temp_database.search_sessions(
        ["hello", "well"], operator=SearchOperator.AND
    )
    assert len(results) == 1

    # Test OR operator with multiple terms
    results = temp_database.search_sessions(
        ["hello", "nonexistent"], operator=SearchOperator.OR
    )
    assert len(results) == 1


def test_date_range_search(temp_database, test_session, test_messages):
    """Test searching sessions by date range"""
    # Store the session and messages
    temp_database.store_session(test_session)
    for message in test_messages:
        temp_database.save_message(message)

    # Test date range that includes the messages
    start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

    results = temp_database.get_active_sessions_by_date_range(start_date, end_date)
    assert len(results) == 1
    assert results[0].session_id == test_session.session_id

    # Test date range that doesn't include the messages
    start_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
    end_date = datetime(2024, 1, 3, tzinfo=timezone.utc)

    results = temp_database.get_active_sessions_by_date_range(start_date, end_date)
    assert len(results) == 0


def test_update_session(temp_database, test_session):
    """Test updating a session"""
    # Store the initial session
    temp_database.store_session(test_session)

    # Update the session
    test_session.title = "Updated Title"
    test_session.last_active = datetime.now(timezone.utc)
    temp_database.update_session(test_session)

    # Verify the update
    retrieved = temp_database.get_session(test_session.session_id)
    assert retrieved.title == "Updated Title"
    assert retrieved.last_active > test_session.created_at


def test_delete_session(temp_database, test_session, test_messages):
    """Test deleting a session"""
    # Store the session and messages
    temp_database.store_session(test_session)
    for message in test_messages:
        temp_database.save_message(message)

    # Delete the session
    temp_database.delete_session(test_session.session_id)

    # Verify session and messages are gone
    with pytest.raises(ValueError):
        temp_database.get_session(test_session.session_id)

    messages = temp_database.get_messages(test_session.session_id)
    assert len(messages) == 0


def test_session_privacy(temp_database, test_session):
    """Test session privacy settings"""
    # Store a private session
    test_session.is_private = True
    temp_database.store_session(test_session)

    # Verify it's not included in regular recent sessions
    sessions = temp_database.get_recent_sessions(include_private=False)
    assert len(sessions) == 0

    # Verify it is included when explicitly requesting private sessions
    sessions = temp_database.get_recent_sessions(include_private=True)
    assert len(sessions) == 1
    assert sessions[0].session_id == test_session.session_id
