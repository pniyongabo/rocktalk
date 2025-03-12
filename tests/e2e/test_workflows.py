from datetime import datetime, timezone
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

from rocktalk.models.interfaces import (
    ChatContentItem,
    ChatMessage,
    ChatSession,
    LLMConfig,
)


def test_complete_chat_workflow(mock_app_context, temp_database):
    """Test a complete chat workflow from start to finish"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Set up session state
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = []

    # Run the app
    at.run()

    # Start a new chat session
    new_chat_button = at.sidebar.button[0]  # Assuming "New Chat" is first button
    new_chat_button.click().run()

    # Send a message
    at.chat_input[0].set_value("Hello, how are you?").run()

    # Verify response
    assert mock_app_context.llm.stream.called
    assert len(at.chat_message) >= 2  # User message + assistant response

    # Save the session
    save_button = at.sidebar.button[1]  # Assuming "Save" is second button
    save_button.click().run()

    # Verify session was saved
    assert mock_app_context.storage.store_session.called


def test_template_creation_workflow(mock_app_context, temp_database):
    """Test creating and using a chat template"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Set up session state
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = []

    # Run the app
    at.run()

    # Create a new session with some messages
    messages = [
        ChatMessage.create(
            role="user",
            content=[ChatContentItem(text="Hello")],
            index=0,
            created_at=datetime.now(timezone.utc),
        ),
        ChatMessage.create(
            role="assistant",
            content=[ChatContentItem(text="Hi there!")],
            index=1,
            created_at=datetime.now(timezone.utc),
        ),
    ]
    at.session_state["messages"] = messages

    # Open template creation dialog
    template_button = [b for b in at.sidebar.button if "Template" in str(b.label)][0]
    template_button.click().run()

    # Fill template details
    at.text_input[0].input("Test Template").run()  # Template name
    at.text_area[0].input("A test template").run()  # Description

    # Save template
    save_button = [b for b in at.button if "Save" in str(b.label)][0]
    save_button.click().run()

    # Verify template was saved
    assert mock_app_context.storage.store_chat_template.called


def test_authentication_workflow(mock_app_context):
    """Test complete authentication workflow"""
    # Initialize app test with auth enabled
    at = AppTest.from_file("rocktalk/app.py")

    # Configure mock auth
    mock_app_context.using_auth = True
    mock_app_context.auth = mock.MagicMock()
    at.session_state["app_context"] = mock_app_context

    # Run the app
    at.run()

    # Verify login form is shown
    assert any(
        "username" in str(text_input.label).lower() for text_input in at.text_input
    )
    assert any(
        "password" in str(text_input.label).lower() for text_input in at.text_input
    )

    # Enter credentials
    username_input = [t for t in at.text_input if "username" in str(t.label).lower()][0]
    password_input = [t for t in at.text_input if "password" in str(t.label).lower()][0]

    username_input.input("testuser").run()
    password_input.input("password123").run()

    # Submit login
    login_button = [b for b in at.button if "login" in str(b.label).lower()][0]
    login_button.click().run()

    # Verify authentication was attempted
    assert mock_app_context.auth.login.called


def test_search_workflow(mock_app_context, temp_database):
    """Test session search workflow"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Set up session state
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = []

    # Configure mock to return search results
    mock_app_context.storage.search_sessions.return_value = [
        ChatSession(
            session_id="test-session",
            title="Test Session",
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
            config=mock_app_context.llm.get_config(),
        )
    ]

    # Run the app
    at.run()

    # Open search dialog
    search_button = [b for b in at.sidebar.button if "Search" in str(b.label)][0]
    search_button.click().run()

    # Enter search term
    search_input = [t for t in at.text_input if "search" in str(t.label).lower()][0]
    search_input.input("test").run()

    # Verify search was performed
    assert mock_app_context.storage.search_sessions.called

    # Select a search result
    result_button = [b for b in at.button if "Test Session" in str(b.label)][0]
    result_button.click().run()

    # Verify session was loaded
    assert mock_app_context.storage.get_messages.called


def test_error_recovery_workflow(mock_app_context, temp_database):
    """Test error recovery in user workflows"""
    # Initialize app test
    at = AppTest.from_file("rocktalk/app.py")

    # Set up session state
    at.session_state["app_context"] = mock_app_context
    at.session_state["messages"] = []

    # Configure mock to raise an error
    mock_app_context.llm.stream.side_effect = Exception("Test error")

    # Run the app
    at.run()

    # Send a message
    at.chat_input[0].set_value("Hello").run()

    # Verify error is displayed
    assert any("error" in str(element.value).lower() for element in at.error)

    # Fix the mock and try again
    mock_app_context.llm.stream.side_effect = None
    at.chat_input[0].set_value("Hello again").run()

    # Verify recovery
    assert mock_app_context.llm.stream.called
    assert len(at.chat_message) >= 2  # User message + assistant response
