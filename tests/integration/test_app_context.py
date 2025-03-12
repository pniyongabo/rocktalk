from datetime import datetime, timezone
from unittest import mock

import pytest

from rocktalk.models.interfaces import (
    ChatContentItem,
    ChatMessage,
    ChatSession,
    LLMConfig,
)
from rocktalk.app_context import AppContext


def test_app_context_initialization(temp_database):
    """Test AppContext initializes all required services"""
    ctx = AppContext()

    # Verify core services are initialized
    assert ctx.storage is not None
    assert ctx.llm is not None
    assert hasattr(ctx, "auth")  # May be None if no auth configured


def test_chat_session_workflow(temp_database):
    """Test complete chat session workflow through AppContext"""
    ctx = AppContext()

    # Create a new session
    session = ChatSession(
        title="Test Session",
        created_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc),
        config=ctx.llm.get_config(),
    )

    # Store the session
    ctx.storage.store_session(session)

    # Create and store messages
    messages = [
        ChatMessage.create(
            session_id=session.session_id,
            role="user",
            content=[ChatContentItem(text="Hello")],
            index=0,
            created_at=datetime.now(timezone.utc),
        ),
        ChatMessage.create(
            session_id=session.session_id,
            role="assistant",
            content=[ChatContentItem(text="Hi there!")],
            index=1,
            created_at=datetime.now(timezone.utc),
        ),
    ]

    for message in messages:
        ctx.storage.save_message(message)

    # Verify session retrieval
    retrieved_session = ctx.storage.get_session(session.session_id)
    assert retrieved_session.session_id == session.session_id

    # Verify message retrieval
    retrieved_messages = ctx.storage.get_messages(session.session_id)
    assert len(retrieved_messages) == 2
    assert retrieved_messages[0].content[0].text == "Hello"
    assert retrieved_messages[1].content[0].text == "Hi there!"


def test_llm_integration(temp_database):
    """Test LLM integration through AppContext"""
    ctx = AppContext()

    # Create a session
    session = ChatSession(
        title="Test Session",
        created_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc),
        config=ctx.llm.get_config(),
    )
    ctx.storage.store_session(session)

    # Create a message
    message = ChatMessage.create(
        session_id=session.session_id,
        role="user",
        content=[ChatContentItem(text="Hello")],
        index=0,
        created_at=datetime.now(timezone.utc),
    )
    ctx.storage.save_message(message)

    # Get messages in LangChain format
    langchain_messages = ctx.llm.convert_messages_to_llm_format(session)

    # Verify message conversion
    assert len(langchain_messages) > 0
    if session.config.system:
        assert len(langchain_messages) == 2  # System message + user message
    else:
        assert len(langchain_messages) == 1  # Just user message


def test_template_workflow(temp_database):
    """Test template creation and application workflow"""
    ctx = AppContext()

    # Get default template
    default_template = ctx.storage.get_default_template()
    assert default_template is not None

    # Create a session using the template
    session = ChatSession(
        title="Template Test Session",
        created_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc),
        config=default_template.config,
    )
    ctx.storage.store_session(session)

    # Verify template config was applied
    retrieved_session = ctx.storage.get_session(session.session_id)
    assert (
        retrieved_session.config.bedrock_model_id
        == default_template.config.bedrock_model_id
    )


def test_authentication_flow():
    """Test authentication flow through AppContext"""
    # Mock auth configuration
    mock_auth_config = {
        "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
        "credentials": {
            "usernames": {
                "testuser": {"name": "Test User", "password": "hashedpassword"}
            }
        },
    }

    with mock.patch("yaml.safe_load", return_value=mock_auth_config):
        ctx = AppContext()

        # Verify auth is enabled
        assert ctx.using_auth
        assert ctx.auth is not None

        # Test authentication handling
        with mock.patch("streamlit.session_state", {"authentication_status": None}):
            assert not ctx.handle_authentication()

        with mock.patch("streamlit.session_state", {"authentication_status": True}):
            assert ctx.handle_authentication()


def test_error_handling(temp_database):
    """Test error handling in AppContext"""
    ctx = AppContext()

    # Test invalid session ID
    with pytest.raises(ValueError):
        ctx.storage.get_session("nonexistent-session")

    # Test invalid template ID
    with pytest.raises(ValueError):
        ctx.storage.get_chat_template_by_id("nonexistent-template")

    # Test database errors
    with mock.patch("sqlite3.connect", side_effect=Exception("Database error")):
        with pytest.raises(RuntimeError):
            ctx.storage.get_sessions()
