import os
import pprint
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, cast

import streamlit as st
from langchain.schema import AIMessage, BaseMessage, HumanMessage
from langchain_aws import ChatBedrockConverse
from langchain_core.messages.ai import AIMessageChunk, UsageMetadata
from langchain_core.messages.base import BaseMessageChunk
from pydantic import BaseModel, Field
from services.creds import get_cached_aws_credentials
from utils.log import logger
from utils.streamlit_utils import escape_dollarsign

from .interfaces import (
    ChatContent,
    ChatContentItem,
    ChatMessage,
    ChatSession,
    LLMConfig,
)
from .rate_limiter import TokenRateLimiter
from .storage.storage_interface import StorageInterface


class TurnState(Enum):
    """Enum representing the current turn state in the conversation.

    Attributes:
        HUMAN_TURN: Waiting for human input.
        AI_TURN: Waiting for AI response.
        COMPLETE: Conversation is complete.
    """

    HUMAN_TURN = "human_turn"
    AI_TURN = "ai_turn"
    COMPLETE = "complete"


MODEL_CONTEXT_LIMITS = {
    # Claude models
    # Claude 3.5 models
    "anthropic.claude-3-5-haiku-20241022-v1:0": 200_000,
    "anthropic.claude-3-5-sonnet-20240620-v1:0": 200_000,
    "anthropic.claude-3-5-sonnet-20241022-v2:0": 200_000,
    # Claude 3.7 models
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0": 200_000,
    # Claude 3 models
    "anthropic.claude-3-haiku-20240307-v1:0": 200_000,
    "anthropic.claude-3-sonnet-20240229-v1:0": 200_000,
    "anthropic.claude-3-opus-20240229-v1:0": 200_000,
    # Older Claude models (keeping for backward compatibility)
    "anthropic.claude-v2": 200_000,
    "anthropic.claude-v2:1": 200_000,
    # Llama models
    "meta.llama2-13b-chat-v1": 4_096,
    "meta.llama2-70b-chat-v1": 4_096,
    "meta.llama3-8b-instruct": 8_192,
    "meta.llama3-70b-instruct": 8_192,
    # Titan models
    "amazon.titan-text-express-v1": 8_000,
    "amazon.titan-text-lite-v1": 4_000,
    "amazon.titan-text-premier-v1:0": 32_000,
    # Mistral models
    "mistral.mistral-7b-instruct-v0:2": 8_000,
    "mistral.mixtral-8x7b-instruct-v0:1": 32_000,
    "mistral.mistral-large-2402-v1:0": 32_000,
    "mistral.mistral-small-2402-v1:0": 32_000,
    # Default fallback value
    "default": 100_000,
}


def model_supports_thinking(model_id: str) -> bool:
    """Check if a model supports extended thinking.

    Args:
        model_id: The Bedrock model identifier

    Returns:
        True if the model supports extended thinking
    """
    # Current models with thinking support
    thinking_models = [
        # Claude 3.7 models
        "claude-3-7",
        # Add future models here
    ]

    return any(model_type in model_id.lower() for model_type in thinking_models)


class LLMInterface(ABC):
    _config: LLMConfig
    _llm: ChatBedrockConverse
    _storage: StorageInterface

    def __init__(
        self, storage: StorageInterface, config: Optional[LLMConfig] = None
    ) -> None:
        self._storage = storage
        if config is None:
            config = storage.get_default_template().config
        self.update_config(config=config)

    @abstractmethod
    def stream(self, input: List[BaseMessage]) -> Iterator[Dict[str, Any]]: ...
    @abstractmethod
    def invoke(self, input: List[BaseMessage]) -> BaseMessage: ...
    @abstractmethod
    def update_config(self, config: Optional[LLMConfig] = None) -> None: ...
    @abstractmethod
    def get_config(self) -> LLMConfig: ...
    @abstractmethod
    def is_thinking_supported(self) -> bool: ...
    @abstractmethod
    def is_image_supported(self) -> bool: ...

    def get_rate_limiter(self) -> Optional[TokenRateLimiter]:
        return None

    def get_state_system_message(self) -> ChatMessage | None:
        if self.get_config().system:
            return ChatMessage.from_system_message(
                system_message=self.get_config().system,
                session_id=st.session_state.get("current_session_id"),
            )
        else:
            return None

    def convert_messages_to_llm_format(
        self, session: Optional[ChatSession] = None
    ) -> List[BaseMessage]:
        """Convert stored ChatMessages to LLM format.

        Returns:
            List of BaseMessage objects in LLM format.
        """
        system_message: ChatMessage | None
        conversation_messages: List[ChatMessage]
        if session:
            system_message = ChatMessage.from_system_message(
                system_message=session.config.system,
                session_id=session.session_id,
            )
            conversation_messages = self._storage.get_messages(session.session_id)
        else:
            system_message = self.get_state_system_message()
            # Use session_state.messages directly for now as it's part of the component state
            conversation_messages = st.session_state.messages

        messages: List[ChatMessage] = [system_message] if system_message else []
        messages.extend(conversation_messages)

        langchain_messages = [msg.convert_to_llm_message() for msg in messages]

        return langchain_messages

    def generate_session_title(self, session: Optional[ChatSession] = None) -> str:
        """Generate a concise session title using the LLM.

        Returns:
            A concise title for the chat session (2-4 words).

        Note:
            Falls back to timestamp-based title if LLM fails to generate one.
        """
        logger.info("Generating session title...")

        title_prompt: HumanMessage = HumanMessage(
            content=f"""Summarize this conversation's topic in up to 5 words or about 28 characters.
            More details are useful, but space is limited to show this summary, so ideally 2-4 words.
            Be direct and concise, no explanations needed. If there are missing messages, do the best you can to keep the summary short."""
        )
        title_response: BaseMessage = self.invoke(
            [
                *self.convert_messages_to_llm_format(session=session),
                title_prompt,
            ]
        )
        title_content: str | list[str | dict] = title_response.content

        if isinstance(title_content, str):
            title: str = escape_dollarsign(title_content.strip('" \n').strip())
        elif isinstance(title_content, list):
            # Extract text content from structured response
            text_parts = []
            for item in title_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))

            title = escape_dollarsign("".join(text_parts).strip('" \n').strip())
        else:
            logger.warning(f"Unexpected generated title response: {title_content}")
            return f"Chat {datetime.now(timezone.utc)}"

        # Fallback to timestamp if we get an empty or invalid response
        if not title:
            title = f"Chat {datetime.now(timezone.utc)}"

        logger.info(f"New session title: {title}")
        return title


class BedrockLLM(LLMInterface):
    def _init_rate_limiter(self) -> None:
        """Initialize the rate limiter using config or environment values"""
        # Get rate limit from config or environment
        config_rate_limit = self.get_config().rate_limit
        env_rate_limit = os.getenv("BEDROCK_TOKENS_PER_MINUTE")

        # Environment variable overrides config if present
        if env_rate_limit:
            try:
                tokens_per_minute = int(env_rate_limit)
                logger.debug(
                    f"Using environment token rate limit: {tokens_per_minute} tokens/min"
                )
            except ValueError:
                logger.warning(
                    f"Invalid BEDROCK_TOKENS_PER_MINUTE value: {env_rate_limit}"
                )
                tokens_per_minute = config_rate_limit
        else:
            tokens_per_minute = config_rate_limit
            logger.debug(
                f"Using configured token rate limit: {tokens_per_minute} tokens/min"
            )

        self._rate_limiter = TokenRateLimiter(tokens_per_minute=tokens_per_minute)

    def get_rate_limiter(self) -> TokenRateLimiter:
        return self._rate_limiter

    def update_config(self, config: Optional[LLMConfig] = None) -> None:
        if config:
            self._config: LLMConfig = config.model_copy(deep=True)
        else:
            self._config = self._storage.get_default_template().config
        self._update_llm()

    def get_config(self) -> LLMConfig:
        return self._config

    def is_thinking_supported(self) -> bool:
        return (
            model_supports_thinking(self._config.bedrock_model_id)
            and self._config.parameters.thinking.enabled
        )

    def is_image_supported(self) -> bool:
        # TODO list models where images are supported? expand to other types like documents, audio, etc.
        return True

    def _update_llm(self) -> None:
        additional_model_request_fields: Dict[str, Any] = {}

        # Handle thinking parameters for Claude 3.7 Sonnet
        if self.is_thinking_supported():
            # Add thinking parameters
            additional_model_request_fields["thinking"] = {
                "type": "enabled",
                "budget_tokens": self._config.parameters.thinking.budget_tokens,
            }
            # When thinking is enabled, we can't use temperature, top_p, or top_k
            temperature = None
            top_p = None
            top_k = None
            logger.info(
                f"Extended thinking enabled with thinking budget of {self._config.parameters.thinking.budget_tokens:,} tokens"
            )
        else:
            # Non-Claude 3.7 models don't support thinking
            temperature = self._config.parameters.temperature
            top_p = self._config.parameters.top_p
            top_k = self._config.parameters.top_k
            if top_k is not None:
                additional_model_request_fields["top_k"] = top_k
            if self._config.parameters.thinking.enabled:
                logger.warning(
                    f"Extended thinking is enabled, however model {self._config.bedrock_model_id} is not known to support it. Automatically disabling extended thinking now."
                )
                self._config.parameters.thinking.enabled = False

        creds = get_cached_aws_credentials()
        region_name = (
            creds.aws_region if creds else os.getenv("AWS_REGION", "us-west-2")
        )

        if creds:
            self._llm = ChatBedrockConverse(
                region_name=region_name,
                model=self._config.bedrock_model_id,
                temperature=temperature,
                max_tokens=self._config.parameters.max_output_tokens,
                stop=self._config.stop_sequences,
                top_p=top_p,
                additional_model_request_fields=additional_model_request_fields,
                aws_access_key_id=creds.aws_access_key_id,
                aws_secret_access_key=creds.aws_secret_access_key,
                aws_session_token=(
                    creds.aws_session_token if creds.aws_session_token else None
                ),
            )
        else:
            # Let boto3 manage credentials
            self._llm = ChatBedrockConverse(
                region_name=region_name,
                model=self._config.bedrock_model_id,
                temperature=temperature,
                max_tokens=self._config.parameters.max_output_tokens,
                stop=self._config.stop_sequences,
                top_p=top_p,
                additional_model_request_fields=additional_model_request_fields,
            )
        self._init_rate_limiter()  # Re-initialize rate limiter when config changes

    def _estimate_tokens(self, messages: List[BaseMessage]) -> int:
        """Estimate the number of tokens for input messages.

        Args:
            messages: The input messages

        Returns:
            Estimated input token count
        """
        # Simple estimation: ~4 chars per token
        input_text = " ".join(str(msg.content) for msg in messages)
        input_tokens = len(input_text) // 4

        # Add safety margin (30%)
        return int(input_tokens * 1.3)

    def get_model_context_limit(self) -> int:
        """Get the context token limit for the current model.

        Returns:
            Maximum context size in tokens
        """
        model_id = self.get_config().bedrock_model_id
        return MODEL_CONTEXT_LIMITS.get(model_id, MODEL_CONTEXT_LIMITS["default"])

    def get_token_usage_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get token usage statistics for a session

        Args:
            session_id: Optional session ID. If None, uses current session.

        Returns:
            Dictionary with token usage statistics
        """
        # Check for temporary session first
        if st.session_state.get("temporary_session", False):
            input_tokens = st.session_state.get("temp_session_input_tokens", 0)
            output_tokens = st.session_state.get("temp_session_output_tokens", 0)
            model_limit = self.get_model_context_limit()
            context_used_percent = (
                (input_tokens / model_limit) * 100 if model_limit > 0 else 0
            )

            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "model_limit": model_limit,
                "context_used_percent": context_used_percent,
                "rate_limit": self._rate_limiter.tokens_per_minute,
                "rate_usage": self._rate_limiter.get_current_usage(),
                "rate_used_percent": self._rate_limiter.get_usage_percentage(),
                "is_temporary": True,
            }

        # For persistent sessions
        target_session_id = session_id or st.session_state.get("current_session_id")

        if not target_session_id:
            return {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "model_limit": self.get_model_context_limit(),
                "context_used_percent": 0,
                "rate_limit": self._rate_limiter.tokens_per_minute,
                "rate_usage": self._rate_limiter.get_current_usage(),
                "rate_used_percent": self._rate_limiter.get_usage_percentage(),
            }

        try:
            session = self._storage.get_session(target_session_id)
            model_limit = self.get_model_context_limit()

            # Get input/output tokens, defaulting to 0 if not present
            input_tokens = getattr(session, "input_tokens_used", 0)
            output_tokens = getattr(session, "output_tokens_used", 0)

            # Calculate context window usage based on input tokens only
            # TODO what if user deletes messages, we'll need to update this per reduced input size -- maybe response metadata is enough?
            # in other words, we want the current input tokens, not the cumulative input tokens
            context_used_percent = (
                (input_tokens / model_limit) * 100 if model_limit > 0 else 0
            )

            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "model_limit": model_limit,
                "context_used_percent": context_used_percent,
                "rate_limit": self._rate_limiter.tokens_per_minute,
                "rate_usage": self._rate_limiter.get_current_usage(),
                "rate_used_percent": self._rate_limiter.get_usage_percentage(),
                "session_id": target_session_id,
                "session_title": session.title,
            }
        except Exception as e:
            logger.warning(f"Failed to get token usage statistics: {e}")
            return {
                "total_tokens": 0,
                "model_limit": self.get_model_context_limit(),
                "context_used_percent": 0,
                "rate_limit": self._rate_limiter.tokens_per_minute,
                "rate_usage": self._rate_limiter.get_current_usage(),
                "rate_used_percent": self._rate_limiter.get_usage_percentage(),
                "error": str(e),
            }

    def _update_session_tokens(
        self, input_tokens: int, output_tokens: int, session_id: Optional[str] = None
    ) -> None:
        """Update token counts for the current session

        Args:
            input_tokens: Number of input tokens used in this request
            output_tokens: Number of output tokens used in this request
            session_id: Optional session ID. If None, uses current session.
        """
        target_session_id = session_id or st.session_state.get("current_session_id")

        # For temporary sessions, we track in session state
        if st.session_state.get("temporary_session", False) or not target_session_id:
            if "temp_session_input_tokens" not in st.session_state:
                st.session_state.temp_session_input_tokens = 0
            if "temp_session_output_tokens" not in st.session_state:
                st.session_state.temp_session_output_tokens = 0

            st.session_state.temp_session_input_tokens += input_tokens
            st.session_state.temp_session_output_tokens += output_tokens

            # Log milestone achievements for temp session
            total_input_tokens = st.session_state.temp_session_input_tokens
            if total_input_tokens % 10_000 < input_tokens:
                logger.info(
                    f"Temporary session reached {total_input_tokens:,} total input tokens"
                )

                # Warn if approaching model limit based on input tokens
                model_limit = self.get_model_context_limit()
                usage_percent = (total_input_tokens / model_limit) * 100
                if usage_percent > 75:
                    logger.warning(
                        f"Temporary session is using {usage_percent:.1f}% "
                        f"of model's context window ({total_input_tokens:,}/{model_limit:,} input tokens)"
                    )

                    if usage_percent > 90:
                        st.warning(
                            f"⚠️ This conversation is approaching {usage_percent:.1f}% of the model's "
                            f"context window ({total_input_tokens:,}/{model_limit:,} input tokens). "
                            f"Consider saving and starting a new chat soon."
                        )

            return

        try:
            # Get the session from storage
            session = self._storage.get_session(target_session_id)

            # Initialize token counters if they don't exist
            if not hasattr(session, "input_tokens_used"):
                session.input_tokens_used = 0
            if not hasattr(session, "output_tokens_used"):
                session.output_tokens_used = 0

            # Update token counts
            session.input_tokens_used += input_tokens
            session.output_tokens_used += output_tokens

            # Save updated session
            self._storage.update_session(session)

            # Log milestone achievements based on input tokens
            if session.input_tokens_used % 10_000 < input_tokens:
                logger.info(
                    f"Session '{session.title}' reached {session.input_tokens_used:,} input tokens"
                )

                # Warn if approaching model limit based on input tokens
                model_limit = self.get_model_context_limit()
                usage_percent = (session.input_tokens_used / model_limit) * 100
                if usage_percent > 75:
                    logger.warning(
                        f"Session '{session.title}' is using {usage_percent:.1f}% "
                        f"of model's context window ({session.input_tokens_used:,}/{model_limit:,} input tokens)"
                    )

                    if usage_percent > 90:
                        st.warning(
                            f"⚠️ This conversation is approaching {usage_percent:.1f}% of the model's "
                            f"context window ({session.input_tokens_used:,}/{model_limit:,} input tokens). "
                            f"Consider starting a new chat soon."
                        )

        except Exception as e:
            logger.warning(f"Failed to update session token counts: {e}")

    def handle_usage_data(self, usage_data: UsageMetadata | None) -> None:
        if usage_data:
            # Update rate limiter with total tokens
            self._rate_limiter.update_usage(usage_data["input_tokens"])

            # Update session token tracking with separate input/output counts
            self._update_session_tokens(
                input_tokens=usage_data["input_tokens"],
                output_tokens=usage_data["output_tokens"],
                session_id=st.session_state.current_session_id,
            )

            # Log token usage details
            session_type = (
                "Temporary"
                if st.session_state.get("temporary_session", False)
                else "Session"
            )
            session_tokens = self.get_token_usage_stats().get("total_tokens", 0)

            logger.info(
                f"Request used {usage_data['total_tokens']:,} tokens "
                f"({usage_data['input_tokens']:,} input, {usage_data['output_tokens']:,} output). "
                f"{session_type} total: {session_tokens:,}. "
                f"Rate usage: {self._rate_limiter.get_current_usage():,}/{self._rate_limiter.tokens_per_minute:,} tokens/min "
                f"({self._rate_limiter.get_usage_percentage():.1f}%)"
            )

    def pause_for_rate_limit(self, input: list[BaseMessage]):
        # Estimate token usage
        estimated_input_tokens = self._estimate_tokens(input)

        # For thinking-enabled responses, we need a larger buffer
        if (
            model_supports_thinking(self._config.bedrock_model_id)
            and self._config.parameters.thinking.enabled
        ):
            # Thinking can use up to budget_tokens plus regular response
            estimated_total = (
                estimated_input_tokens
                + self._config.parameters.thinking.budget_tokens
                + estimated_input_tokens
            )
        else:
            # Regular response estimation
            estimated_total = estimated_input_tokens * 2

        # Check rate limit
        is_allowed, wait_time = self._rate_limiter.check_rate_limit(estimated_total)

        if not is_allowed:
            # Inform user about rate limiting
            wait_time_rounded = round(wait_time, 1)
            usage_percent = self._rate_limiter.get_usage_percentage()
            message = f"Rate limit {self._rate_limiter.tokens_per_minute} tokens/min reached ({usage_percent:.1f}% used). Please wait {wait_time_rounded} seconds."
            logger.warning(message)
            st.warning(message)
            with st.spinner("Waiting for..", show_time=True):
                st.markdown("")
                time.sleep(wait_time)

    def stream(self, input: List[BaseMessage]) -> Iterator[Dict[str, Any]]:
        """Stream a response with rate limiting, processing thinking blocks internally.

        This version yields simplified dictionaries for easy consumption by the UI:
        {
            "content": "text chunk",
            "type": "thinking" | "text",
            "is_thinking_block": bool,  # True if this is a thinking block
            "done": bool,               # True for the last chunk
            "metadata": {...}           # Optional metadata
        }
        """

        self.pause_for_rate_limit(input)

        # Track state
        usage_data: UsageMetadata | None = None
        current_thinking_block = ""
        current_thinking_signature: str | None = None
        current_text_block = ""
        all_content_items: ChatContent = []

        try:
            # Process chunks from the LLM stream
            for chunk in self._llm.stream(input=input):
                chunk = cast(AIMessageChunk, chunk)
                # logger.info(f"Chunk received: {pprint.pformat(chunk)}")
                # Extract usage data if available
                if chunk.usage_metadata:
                    usage_data = chunk.usage_metadata

                # Process content
                if isinstance(chunk.content, str):
                    # Simple text chunk
                    current_text_block += chunk.content
                    yield {
                        "content": chunk.content,
                        "type": "text",
                        "is_thinking_block": False,
                        "done": False,
                    }
                elif isinstance(chunk.content, list):
                    # Structured content
                    for item in chunk.content:
                        if isinstance(item, dict):
                            if item.get("type") == "reasoning_content":
                                # Accumulate thinking content
                                thinking_chunk = item.get("reasoning_content", {}).get(
                                    "text"
                                )

                                if thinking_chunk:
                                    current_thinking_block += thinking_chunk

                                if item.get("reasoning_content", {}).get("signature"):
                                    current_thinking_signature = item[
                                        "reasoning_content"
                                    ]["signature"]

                                yield {
                                    "content": thinking_chunk,
                                    "type": "thinking",
                                    "is_thinking_block": True,
                                    "done": False,
                                }

                            elif item.get("type") == "text":
                                # Accumulate text content
                                text = item.get("text", "")
                                current_text_block += text
                                yield {
                                    "content": text,
                                    "type": "text",
                                    "is_thinking_block": False,
                                    "done": False,
                                }

            # Ensure we save accumulated content even if there were no empty chunks
            # Add thinking block if we have accumulated content
            if current_thinking_block:
                all_content_items.append(
                    ChatContentItem(
                        thinking=current_thinking_block,
                        thinking_signature=current_thinking_signature,
                    )
                )

            # Add text block if we have accumulated content
            if current_text_block:
                all_content_items.append(ChatContentItem(text=current_text_block))
            streaming_output = dict(
                usage_data=usage_data,
                current_thinking_block=current_thinking_block,
                current_thinking_signature=current_thinking_signature,
                current_text_block=current_text_block,
                all_content_items=all_content_items,
            )
            logger.debug(f"Streaming complete: {streaming_output}")

            # Send final completion chunk
            yield {
                "content": "",
                "type": "text",
                "is_thinking_block": False,
                "done": True,
                "metadata": {"usage_data": usage_data},
            }

            # After streaming completes, save the full message if not temporary
            if all_content_items:
                assistant_message = ChatMessage.create(
                    role="assistant",
                    content=all_content_items,
                    index=len(st.session_state.messages),
                    session_id=st.session_state.get("current_session_id", ""),
                )

                logger.info(
                    f"Saving assistant message: {pprint.pformat(assistant_message)}"
                )

                # Store in session state
                st.session_state.messages.append(assistant_message)
                if not st.session_state.get(
                    "temporary_session", False
                ) and st.session_state.get("current_session_id"):
                    # Store in storage
                    self._storage.save_message(assistant_message)

        finally:
            # After stream completes (or errors), extract and update token usage
            self.handle_usage_data(usage_data)

    def invoke(self, input: list[BaseMessage]) -> AIMessage:
        """Invoke the model with rate limiting"""
        self.pause_for_rate_limit(input)

        # Get response
        response: AIMessage = cast(AIMessage, self._llm.invoke(input=input))
        logger.info(f"Response: {pprint.pformat(response)}")

        # Extract token usage
        self.handle_usage_data(response.usage_metadata)

        return response
