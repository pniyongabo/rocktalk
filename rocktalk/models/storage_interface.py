import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum
from typing import List, Optional, Tuple

from models.interfaces import (
    ChatMessage,
    ChatSession,
    ChatTemplate,
    LLMConfig,
    LLMParameters,
)

ROCKTALK_DEFAULT_MODEL = os.getenv(
    "ROCKTALK_DEFAULT_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0"
)


class SearchOperator(StrEnum):
    AND = "AND"
    OR = "OR"


class StorageInterface(ABC):
    """Protocol defining the interface for chat storage implementations"""

    @abstractmethod
    def save_message(self, message: ChatMessage) -> None:
        """Save a message to a chat session"""
        ...

    @abstractmethod
    def get_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session"""
        ...

    @abstractmethod
    def search_sessions(
        self,
        query: List[str],  # Changed from str to List[str]
        operator: SearchOperator = SearchOperator.AND,  # Added operator
        search_titles: bool = True,
        search_content: bool = True,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> List[ChatSession]:
        """Search sessions with advanced filtering

        Args:
            query: List of search terms
            operator: SearchOperator.AND or SearchOperator.OR to combine terms
            search_titles: Whether to search session titles
            search_content: Whether to search message content
            date_range: Optional tuple of (start_date, end_date) to filter by
        """
        ...

    @abstractmethod
    def get_active_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[ChatSession]:
        """Get sessions that have messages within the date range"""
        ...

    @abstractmethod
    def update_session(self, session: ChatSession) -> None:
        """Update an existing chat session"""
        ...

    @abstractmethod
    def store_session(self, session: ChatSession) -> None:
        """Store a new chat session"""
        ...

    @abstractmethod
    def get_session(self, session_id: str) -> ChatSession:
        """Get a specific chat session"""
        ...

    @abstractmethod
    def delete_message(self, session_id: str, index: int) -> None:
        """Delete a specific message by its index.

        Args:
            session_id: ID of the session containing the message
            index: Index of the message to delete
        """
        ...

    @abstractmethod
    def delete_messages_from_index(self, session_id: str, from_index: int) -> None:
        """Delete all messages with index >= from_index for the given session."""
        ...

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete a session and its messages"""
        ...

    @abstractmethod
    def delete_all_sessions(self) -> None:
        """Delete all chat sessions and their messages"""
        ...

    @abstractmethod
    def get_recent_sessions(
        self, limit: int = 10, include_private=False
    ) -> List[ChatSession]:
        """Get most recently active sessions"""
        ...

    @abstractmethod
    def rename_session(self, session_id: str, new_title: str) -> None:
        """Rename a chat session"""
        ...

    @abstractmethod
    def set_default_template(self, template_id: str) -> None:
        """Set a template as the default

        Args:
            template_id: ID of the template to set as default

        Raises:
            ValueError: If template_id doesn't exist
        """
        ...

    @abstractmethod
    def get_default_template(self) -> ChatTemplate:
        """Get the current default template

        Returns:
            The default template if one is set, None otherwise
        """
        ...

    @staticmethod
    def get_preset_templates() -> List[ChatTemplate]:
        """Get the preset chat templates

        Note: These are preset templates, different from user-set default template.
        Used for initial setup and reset to defaults.
        """
        return [
            ChatTemplate(
                name="Balanced",
                description="Balanced between creativity and consistency",
                config=LLMConfig(
                    bedrock_model_id=ROCKTALK_DEFAULT_MODEL,
                    parameters=LLMParameters(temperature=0.5),
                ),
            ),
            ChatTemplate(
                name="Deterministic",
                description="Precise and consistent responses",
                config=LLMConfig(
                    bedrock_model_id=ROCKTALK_DEFAULT_MODEL,
                    parameters=LLMParameters(temperature=0.0),
                ),
            ),
            ChatTemplate(
                name="Creative",
                description="More varied and creative responses",
                config=LLMConfig(
                    bedrock_model_id=ROCKTALK_DEFAULT_MODEL,
                    parameters=LLMParameters(temperature=0.9),
                ),
            ),
        ]

    @abstractmethod
    def initialize_preset_templates(self) -> None:
        """Initialize the default preset templates if they don't exist"""
        ...

    @abstractmethod
    def store_chat_template(self, template: ChatTemplate) -> None:
        """Store a new chat template"""
        ...

    @abstractmethod
    def get_chat_template_by_id(self, template_id: str) -> ChatTemplate:
        """Get a specific chat template by id"""
        ...

    @abstractmethod
    def get_chat_template_by_name(self, template_name: str) -> ChatTemplate:
        """Get a specific chat template by name"""
        ...

    @abstractmethod
    def update_chat_template(self, template: ChatTemplate) -> None:
        """Update an existing chat template"""
        ...

    @abstractmethod
    def delete_chat_template(self, template_id: str) -> None:
        """Delete a chat template"""
        ...

    @abstractmethod
    def get_chat_templates(self) -> List[ChatTemplate]:
        """Get all chat templates"""
        ...
