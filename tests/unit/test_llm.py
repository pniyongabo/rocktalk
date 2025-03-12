from datetime import datetime, timezone
from unittest import mock

import pytest
from langchain.schema import AIMessage, HumanMessage

from rocktalk.models.interfaces import ChatContentItem, ChatMessage
from rocktalk.models.llm import BedrockLLM


def test_invoke_response(mock_langchain_bedrock, temp_database):
    """Test generating a response using the LLM's invoke method"""
    llm = BedrockLLM(storage=temp_database)

    # Create a test message
    message = ChatMessage.create(
        session_id="test-session",
        role="user",
        content=[ChatContentItem(text="Hello, how are you?")],
        index=0,
        created_at=datetime.now(timezone.utc),
    )

    # Convert to LangChain format
    langchain_messages = [message.convert_to_llm_message()]

    # Generate a response
    response = llm.invoke(langchain_messages)

    # Verify the response
    assert response.content == "This is a test response from the LLM"
    mock_langchain_bedrock.assert_called_once()


def test_stream_response(mock_langchain_bedrock, temp_database):
    """Test streaming a response using the LLM's stream method"""
    llm = BedrockLLM(storage=temp_database)

    # Create a test message
    message = ChatMessage.create(
        session_id="test-session",
        role="user",
        content=[ChatContentItem(text="Hello, how are you?")],
        index=0,
        created_at=datetime.now(timezone.utc),
    )

    # Convert to LangChain format
    langchain_messages = [message.convert_to_llm_message()]

    # Configure mock to return chunks
    mock_instance = mock_langchain_bedrock.return_value
    mock_instance.stream.return_value = [
        AIMessage(content="This is "),
        AIMessage(content="a test "),
        AIMessage(content="response"),
    ]

    # Stream the response
    chunks = list(llm.stream(langchain_messages))

    # Verify the chunks
    assert len(chunks) > 0
    assert all(isinstance(chunk, dict) for chunk in chunks)
    assert any(chunk["done"] for chunk in chunks)  # Last chunk should have done=True
    mock_instance.stream.assert_called_once()


def test_thinking_response(mock_langchain_bedrock, temp_database):
    """Test handling of thinking blocks in responses"""
    llm = BedrockLLM(storage=temp_database)

    # Create a test message
    message = ChatMessage.create(
        session_id="test-session",
        role="user",
        content=[ChatContentItem(text="Hello, how are you?")],
        index=0,
        created_at=datetime.now(timezone.utc),
    )

    # Convert to LangChain format
    langchain_messages = [message.convert_to_llm_message()]

    # Configure mock to return a response with thinking blocks
    mock_instance = mock_langchain_bedrock.return_value
    mock_instance.stream.return_value = [
        AIMessage(
            content=[
                {
                    "type": "reasoning_content",
                    "reasoning_content": {
                        "text": "Let me think...",
                        "signature": "thinking",
                    },
                },
                {"type": "text", "text": "Here's my response"},
            ]
        ),
    ]

    # Stream the response
    chunks = list(llm.stream(langchain_messages))

    # Verify thinking blocks are handled
    thinking_chunks = [chunk for chunk in chunks if chunk["is_thinking_block"]]
    text_chunks = [chunk for chunk in chunks if not chunk["is_thinking_block"]]

    assert len(thinking_chunks) > 0
    assert len(text_chunks) > 0
    assert thinking_chunks[0]["content"] == "Let me think..."
    assert any("Here's my response" in chunk["content"] for chunk in text_chunks)


def test_rate_limiting(mock_langchain_bedrock, temp_database):
    """Test rate limiting functionality"""
    llm = BedrockLLM(storage=temp_database)

    # Create multiple test messages
    messages = []
    for i in range(5):
        message = ChatMessage.create(
            session_id="test-session",
            role="user",
            content=[ChatContentItem(text=f"Message {i}")],
            index=i,
            created_at=datetime.now(timezone.utc),
        )
        messages.append(message.convert_to_llm_message())

    # Generate responses in quick succession
    responses = []
    for message in messages:
        response = llm.invoke([message])
        responses.append(response)

    # Verify all responses were generated
    assert len(responses) == 5
    assert all(
        response.content == "This is a test response from the LLM"
        for response in responses
    )

    # Verify rate limiter was used
    mock_instance = mock_langchain_bedrock.return_value
    assert mock_instance.invoke.call_count == 5


def test_error_handling(mock_langchain_bedrock, temp_database):
    """Test error handling in LLM interactions"""
    llm = BedrockLLM(storage=temp_database)

    # Create a test message
    message = ChatMessage.create(
        session_id="test-session",
        role="user",
        content=[ChatContentItem(text="Hello")],
        index=0,
        created_at=datetime.now(timezone.utc),
    )

    # Configure mock to raise an exception
    mock_instance = mock_langchain_bedrock.return_value
    mock_instance.invoke.side_effect = Exception("Test error")

    # Verify error handling
    with pytest.raises(Exception) as exc_info:
        llm.invoke([message.convert_to_llm_message()])
    assert "Test error" in str(exc_info.value)
