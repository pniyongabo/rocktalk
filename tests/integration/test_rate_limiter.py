import time
from datetime import datetime, timezone
from unittest import mock

import pytest

from rocktalk.models.interfaces import ChatContentItem, ChatMessage
from rocktalk.models.rate_limiter import TokenRateLimiter
from rocktalk.models.llm import BedrockLLM


def test_rate_limiter_integration(temp_database):
    """Test rate limiter integration with LLM"""
    # Create LLM with a very low rate limit for testing
    llm = BedrockLLM(storage=temp_database)
    llm._rate_limiter = TokenRateLimiter(tokens_per_minute=100)

    # Create test messages
    messages = []
    for i in range(5):
        message = ChatMessage.create(
            session_id="test-session",
            role="user",
            content=[ChatContentItem(text=f"Test message {i}")],
            index=i,
            created_at=datetime.now(timezone.utc),
        )
        messages.append(message.convert_to_llm_message())

    # Send messages rapidly to trigger rate limiting
    responses = []
    start_time = time.time()

    for message in messages:
        # Get rate limiter state before request
        pre_usage = llm.get_rate_limiter().get_current_usage()

        # Send message
        response = llm.invoke([message])
        responses.append(response)

        # Get rate limiter state after request
        post_usage = llm.get_rate_limiter().get_current_usage()

        # Verify rate limiter was updated
        assert post_usage > pre_usage

    # Verify all messages were processed
    assert len(responses) == 5

    # Verify rate limiting added appropriate delays
    total_time = time.time() - start_time
    assert total_time >= 0.5  # Should take at least 0.5 seconds due to rate limiting


def test_rate_limiter_streaming(temp_database):
    """Test rate limiter with streaming responses"""
    # Create LLM with a very low rate limit
    llm = BedrockLLM(storage=temp_database)
    llm._rate_limiter = TokenRateLimiter(tokens_per_minute=100)

    # Create a test message
    message = ChatMessage.create(
        session_id="test-session",
        role="user",
        content=[ChatContentItem(text="Test streaming message")],
        index=0,
        created_at=datetime.now(timezone.utc),
    )

    # Stream response
    chunks = list(llm.stream([message.convert_to_llm_message()]))

    # Verify streaming worked with rate limiting
    assert len(chunks) > 0
    assert any(chunk["done"] for chunk in chunks)

    # Verify rate limiter was updated
    usage = llm.get_rate_limiter().get_current_usage()
    assert usage > 0


def test_rate_limiter_recovery(temp_database):
    """Test rate limiter recovery after waiting"""
    # Create LLM with a very low rate limit
    llm = BedrockLLM(storage=temp_database)
    llm._rate_limiter = TokenRateLimiter(tokens_per_minute=100)

    # Create a test message
    message = ChatMessage.create(
        session_id="test-session",
        role="user",
        content=[ChatContentItem(text="Test message")],
        index=0,
        created_at=datetime.now(timezone.utc),
    )
    langchain_message = message.convert_to_llm_message()

    # Send multiple messages to hit rate limit
    for _ in range(3):
        llm.invoke([langchain_message])

    # Record usage after hitting limit
    usage_at_limit = llm.get_rate_limiter().get_current_usage()

    # Wait for rate limiter to recover
    time.sleep(61)  # Wait just over a minute

    # Verify usage has decreased
    current_usage = llm.get_rate_limiter().get_current_usage()
    assert current_usage < usage_at_limit

    # Verify can send new messages
    response = llm.invoke([langchain_message])
    assert response is not None


def test_rate_limiter_concurrent_sessions(temp_database):
    """Test rate limiter handles concurrent sessions properly"""
    # Create LLM with a moderate rate limit
    llm = BedrockLLM(storage=temp_database)
    llm._rate_limiter = TokenRateLimiter(tokens_per_minute=1000)

    # Create test messages for different sessions
    session_messages = {}
    for session_id in ["session1", "session2", "session3"]:
        message = ChatMessage.create(
            session_id=session_id,
            role="user",
            content=[ChatContentItem(text=f"Test message for {session_id}")],
            index=0,
            created_at=datetime.now(timezone.utc),
        )
        session_messages[session_id] = message.convert_to_llm_message()

    # Simulate concurrent session activity
    for _ in range(2):  # Two rounds of messages
        for session_id, message in session_messages.items():
            # Get rate limiter state before request
            pre_usage = llm.get_rate_limiter().get_current_usage()

            # Send message
            response = llm.invoke([message])
            assert response is not None

            # Verify rate limiter was updated
            post_usage = llm.get_rate_limiter().get_current_usage()
            assert post_usage > pre_usage


def test_rate_limiter_error_handling(temp_database):
    """Test rate limiter handles errors properly"""
    # Create LLM with a very low rate limit
    llm = BedrockLLM(storage=temp_database)
    llm._rate_limiter = TokenRateLimiter(tokens_per_minute=100)

    # Create a test message
    message = ChatMessage.create(
        session_id="test-session",
        role="user",
        content=[ChatContentItem(text="Test message")],
        index=0,
        created_at=datetime.now(timezone.utc),
    )
    langchain_message = message.convert_to_llm_message()

    # Configure mock to raise an error
    with mock.patch.object(llm._llm, "invoke", side_effect=Exception("Test error")):
        # Record usage before error
        pre_usage = llm.get_rate_limiter().get_current_usage()

        # Attempt request that will fail
        with pytest.raises(Exception):
            llm.invoke([langchain_message])

        # Verify rate limiter was still updated
        post_usage = llm.get_rate_limiter().get_current_usage()
        assert post_usage > pre_usage
