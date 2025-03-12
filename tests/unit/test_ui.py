from datetime import datetime, timezone
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

from rocktalk.models.interfaces import ChatContentItem, ChatMessage


def test_chat_interface(mock_app_context):
    """Test the chat interface functionality"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Set up session state with mock context
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = []
    at.session_state["current_session_id"] = "test-session-id"

    # Run the app
    at.run()

    # Verify chat input exists
    assert len(at.chat_input) > 0

    # Test sending a message
    at.chat_input[0].set_value("Hello, how are you?").run()

    # Verify message was processed
    assert mock_app_context.llm.generate_response.called
    assert len(at.chat_message) >= 2  # User message + assistant response


def test_sidebar_template_selector(mock_app_context):
    """Test template selector in sidebar"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Set up session state with mock context
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = []

    # Configure mock storage to return templates
    mock_app_context.storage.get_chat_templates.return_value = [
        {
            "template_id": "test-template",
            "name": "Test Template",
            "description": "A test template",
        }
    ]

    # Run the app
    at.run()

    # Find and interact with template selector
    template_selector = at.sidebar.selectbox[0]  # Assuming it's the first selectbox
    template_selector.select("Test Template").run()

    # Verify template was applied
    assert mock_app_context.storage.get_chat_template_by_name.called


def test_session_list(mock_app_context):
    """Test session list functionality"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Set up session state with mock context
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = []

    # Configure mock storage to return sessions
    mock_app_context.storage.get_recent_sessions.return_value = [
        {
            "session_id": "test-session-1",
            "title": "Test Session 1",
            "created_at": datetime.now(timezone.utc),
        }
    ]

    # Run the app
    at.run()

    # Verify sessions are displayed
    assert any("Test Session 1" in str(element.value) for element in at.sidebar.text)


def test_message_display(mock_app_context):
    """Test message display functionality"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Create test messages
    messages = [
        ChatMessage.create(
            session_id="test-session",
            role="user",
            content=[ChatContentItem(text="Hello")],
            index=0,
            created_at=datetime.now(timezone.utc),
        ),
        ChatMessage.create(
            session_id="test-session",
            role="assistant",
            content=[ChatContentItem(text="Hi there!")],
            index=1,
            created_at=datetime.now(timezone.utc),
        ),
    ]

    # Set up session state
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = messages
    at.session_state["current_session_id"] = "test-session"

    # Run the app
    at.run()

    # Verify messages are displayed
    assert len(at.chat_message) == 2
    assert "Hello" in str(at.chat_message[0].markdown[0].value)
    assert "Hi there!" in str(at.chat_message[1].markdown[0].value)


def test_thinking_display(mock_app_context):
    """Test display of thinking blocks"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Create test message with thinking block
    messages = [
        ChatMessage.create(
            session_id="test-session",
            role="assistant",
            content=[
                ChatContentItem(thinking="Let me think about this..."),
                ChatContentItem(text="Here's my response"),
            ],
            index=0,
            created_at=datetime.now(timezone.utc),
        ),
    ]

    # Set up session state
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = messages
    at.session_state["current_session_id"] = "test-session"

    # Run the app
    at.run()

    # Verify thinking block is displayed
    assert len(at.chat_message) == 1
    assert "Let me think about this..." in str(at.expander[0].markdown[0].value)
    assert "Here's my response" in str(at.chat_message[0].markdown[0].value)


def test_error_handling(mock_app_context):
    """Test UI error handling"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Set up session state
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = []

    # Configure mock to raise an error
    mock_app_context.llm.generate_response.side_effect = Exception("Test error")

    # Run the app and trigger an error
    at.run()
    at.chat_input[0].set_value("Hello").run()

    # Verify error is displayed
    assert any("error" in str(element.value).lower() for element in at.error)
