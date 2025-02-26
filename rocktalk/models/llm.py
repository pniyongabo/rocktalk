import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

import streamlit as st
from langchain.schema import BaseMessage, HumanMessage
from langchain_aws import ChatBedrockConverse
from langchain_core.messages.base import BaseMessageChunk
from services.creds import get_cached_aws_credentials
from utils.log import logger
from utils.streamlit_utils import escape_dollarsign

from .interfaces import ChatMessage, ChatSession, LLMConfig
from .rate_limiter import TokenRateLimiter
from .storage_interface import StorageInterface


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
    def stream(self, input: List[BaseMessage]) -> Iterator[BaseMessageChunk]: ...
    @abstractmethod
    def invoke(self, input: List[BaseMessage]) -> BaseMessage: ...
    @abstractmethod
    def update_config(self, config: Optional[LLMConfig] = None) -> None: ...
    @abstractmethod
    def get_config(self) -> LLMConfig: ...

    def get_state_system_message(self) -> ChatMessage | None:
        if self.get_config().system:
            return ChatMessage.from_system_message(
                system_message=st.session_state.llm.get_config().system,
                session_id=st.session_state.current_session_id,
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

    def update_config(self, config: Optional[LLMConfig] = None) -> None:
        if config:
            self._config: LLMConfig = config.model_copy(deep=True)
        else:
            self._config = self._storage.get_default_template().config
        self._update_llm()

    def get_config(self) -> LLMConfig:
        return self._config

    def _update_llm(self) -> None:
        additional_model_request_fields: Optional[Dict[str, Any]] = None
        if self._config.parameters.top_k:
            additional_model_request_fields = {"top_k": self._config.parameters.top_k}

        creds = get_cached_aws_credentials()
        region_name = (
            creds.aws_region if creds else os.getenv("AWS_REGION", "us-west-2")
        )

        if creds:
            self._llm = ChatBedrockConverse(
                region_name=region_name,
                model=self._config.bedrock_model_id,
                temperature=self._config.parameters.temperature,
                max_tokens=self._config.parameters.max_output_tokens,
                stop=self._config.stop_sequences,
                top_p=self._config.parameters.top_p,
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
                temperature=self._config.parameters.temperature,
                max_tokens=self._config.parameters.max_output_tokens,
                stop=self._config.stop_sequences,
                top_p=self._config.parameters.top_p,
                additional_model_request_fields=additional_model_request_fields,
            )
        self._init_rate_limiter()  # Re-initialize rate limiter when config changes

    def _extract_token_usage(self, usage_data: Optional[Dict]) -> int:
        """Extract token usage from Bedrock response metadata

        Args:
            usage_data: Usage metadata from Bedrock response

        Returns:
            Total token count (input + output)
        """
        if not usage_data:
            return 0

        input_tokens = usage_data.get("input_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0)

        # Some Bedrock models use different keys
        if input_tokens == 0:
            input_tokens = usage_data.get("promptTokenCount", 0)
        if output_tokens == 0:
            output_tokens = usage_data.get("completionTokenCount", 0)

        # Return total tokens
        return input_tokens + output_tokens

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

    def stream(self, input: List[BaseMessage]) -> Iterator[BaseMessageChunk]:
        """Stream a response with rate limiting

        Uses estimated tokens for initial rate limiting check, but updates
        with actual token counts from the API response once available.
        """
        # Estimate token usage for input
        estimated_input_tokens = self._estimate_tokens(input)

        # Check rate limit with a buffer for expected output tokens
        # Assume roughly similar number of output tokens as input
        estimated_total = estimated_input_tokens * 2
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

        # Process the stream
        usage_data = None
        try:
            # Yield chunks from the LLM stream
            for chunk in self._llm.stream(input=input):
                yield chunk

                # Extract usage data if available
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    usage_data = chunk.usage_metadata

        finally:
            # After stream completes (or errors), update rate limiter with actual usage
            actual_tokens = self._extract_token_usage(usage_data)

            # If we couldn't get actual token count, use our estimate
            if actual_tokens == 0:
                logger.warning("No token usage data available, using estimate")
                actual_tokens = estimated_total

            # Update rate limiter with actual token usage
            self._rate_limiter.update_usage(actual_tokens)

            # Log current usage
            logger.info(
                f"Request used {actual_tokens} tokens. Current usage (last 1 min window): "
                f"{self._rate_limiter.get_current_usage()} tokens "
                f"({self._rate_limiter.get_usage_percentage():.1f}% of limit)"
            )

    def invoke(self, input: List[BaseMessage]) -> BaseMessage:
        """Invoke the model with rate limiting"""
        # Estimate token usage
        estimated_input_tokens = self._estimate_tokens(input)
        estimated_total = estimated_input_tokens * 2  # Assume output similar to input

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

        # Get response
        response = self._llm.invoke(input=input)

        # Extract actual token usage if available
        actual_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            actual_tokens = self._extract_token_usage(response.usage_metadata)

        # If we couldn't get actual usage, use our estimate
        if actual_tokens == 0:
            logger.warning("No token usage data available, using estimate")
            actual_tokens = estimated_total

        # Update rate limiter
        self._rate_limiter.update_usage(actual_tokens)

        # Log current usage
        logger.info(
            f"Request used {actual_tokens} tokens. Current usage: "
            f"{self._rate_limiter.get_current_usage()} tokens "
            f"({self._rate_limiter.get_usage_percentage():.1f}% of limit)"
        )

        return response
