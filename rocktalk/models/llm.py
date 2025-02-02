import os
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

    def stream(self, input) -> Iterator[BaseMessageChunk]:
        return self._llm.stream(input=input)

    def invoke(self, input) -> BaseMessage:
        return self._llm.invoke(input=input)
