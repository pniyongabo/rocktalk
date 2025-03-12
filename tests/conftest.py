import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest
import streamlit as st
from langchain_aws.chat_models import ChatBedrockConverse

from rocktalk.models.interfaces import (
    ChatContentItem,
    ChatMessage,
    ChatSession,
    LLMConfig,
    LLMParameters,
)
from rocktalk.models.storage.sqlite import SQLiteChatStorage


@pytest.fixture
def temp_database():
    """Create a temporary SQLite database for testing"""
    db_fd, db_path = tempfile.mkstemp()
    storage = SQLiteChatStorage(db_path=db_path)

    yield storage

    # Clean up the temporary file
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def mock_bedrock_client():
    """Mock the boto3 client for Bedrock"""
    with mock.patch("boto3.client") as mock_client:
        # Configure the mock to return predictable responses
        mock_invoke = mock.MagicMock()
        mock_invoke.return_value = {
            "body": mock.MagicMock(),
            "contentType": "application/json",
        }
        mock_client.return_value.invoke_model = mock_invoke
        yield mock_client


@pytest.fixture
def mock_langchain_bedrock():
    """Mock the LangChain ChatBedrockConverse class"""
    with mock.patch("langchain_aws.chat_models.ChatBedrockConverse") as mock_chat:
        # Configure the mock to return predictable responses
        mock_instance = mock.MagicMock()
        mock_instance.invoke.return_value.content = (
            "This is a test response from the LLM"
        )
        mock_chat.return_value = mock_instance
        yield mock_chat


@pytest.fixture
def mock_streamlit_session_state():
    """Mock Streamlit session state"""
    original_session_state = getattr(st, "session_state", {})
    session_state = {}

    # Create a context manager to mock session_state
    class SessionStateMock:
        def __init__(self, initial_state=None):
            self.initial_state = initial_state or {}

        def __enter__(self):
            # Set up mock session state
            for key, value in self.initial_state.items():
                session_state[key] = value
            # Replace st.session_state with our mock
            setattr(st, "session_state", session_state)
            return session_state

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Restore original session state
            setattr(st, "session_state", original_session_state)

    return SessionStateMock


@pytest.fixture
def test_session():
    """Create a test chat session"""
    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return ChatSession(
        session_id="test-session-id",
        title="Test Session",
        created_at=created_at,
        last_active=created_at,
        config=LLMConfig(
            bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            parameters=LLMParameters(
                temperature=0.7,
                max_output_tokens=4096,
                top_p=0.9,
            ),
        ),
    )


@pytest.fixture
def test_messages():
    """Create a list of test messages"""
    return [
        ChatMessage.create(
            session_id="test-session-id",
            role="user",
            content=[ChatContentItem(text="Hello, how are you?")],
            index=0,
            created_at=datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc),
        ),
        ChatMessage.create(
            session_id="test-session-id",
            role="assistant",
            content=[ChatContentItem(text="I'm doing well, thank you for asking!")],
            index=1,
            created_at=datetime(2024, 1, 1, 12, 2, 0, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def mock_app_context():
    """Create a mock AppContext"""
    with mock.patch("rocktalk.app_context.AppContext") as mock_ctx:
        mock_instance = mock.MagicMock()
        mock_storage = mock.MagicMock()
        mock_llm = mock.MagicMock()

        # Configure storage mock
        mock_storage.get_sessions.return_value = [
            {
                "id": "test-session-id",
                "name": "Test Session",
                "created_at": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                "last_active": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            }
        ]

        # Configure LLM mock
        mock_llm.generate_response.return_value = "This is a test response"

        # Set up AppContext properties
        mock_instance.storage = mock_storage
        mock_instance.llm = mock_llm
        mock_instance.using_auth = False

        mock_ctx.return_value = mock_instance
        yield mock_instance
