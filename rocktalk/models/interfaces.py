import json
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, List, Optional, TypeAlias

import streamlit as st
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from PIL.ImageFile import ImageFile
from pydantic import BaseModel, Field, model_validator
from streamlit_chat_prompt import FileData, PromptReturn, prompt
from utils.image_utils import MAX_IMAGE_WIDTH, image_from_b64_image
from utils.js import copy_value_to_clipboard, focus_prompt
from utils.log import logger
from utils.streamlit_utils import (
    OnPillsChange,
    PillOptions,
    close_dialog,
    escape_dollarsign,
    on_pills_change,
)


class ThinkingParameters(BaseModel):
    """Parameters for Claude's extended thinking capability.

    Attributes:
        enabled: Whether extended thinking is enabled
        budget_tokens: Maximum tokens Claude can use for internal reasoning (min: 1,024)
    """

    enabled: bool = False
    budget_tokens: int = Field(
        default=16000,
        ge=1024,  # Minimum 1,024 tokens as per API requirements
        lt=128000,  # Maximum 128,000 tokens
    )


class LLMParameters(BaseModel):
    """Parameters for the LLM model."""

    temperature: float = Field(
        default=0.5, description="Sampling temperature between 0 and 1", ge=0, le=1
    )
    top_p: Optional[float] = Field(
        default=None, description="Nucleus sampling parameter", ge=0, le=1
    )
    top_k: Optional[int] = Field(
        default=None,
        description="Top-k sampling parameter (additional parameter for Anthropic models)",
        ge=0,
    )
    max_output_tokens: Optional[int] = Field(
        default=None, description="Maximum number of tokens to generate"
    )
    thinking: ThinkingParameters = Field(
        default_factory=ThinkingParameters,
        description="Extended thinking parameters for Claude 3.7 models",
    )


_DEFAULT_LLM_CONFIG: Optional["LLMConfig"] = None


class LLMConfig(BaseModel):
    """Configuration for the LLM model."""

    bedrock_model_id: str = Field(
        description="Bedrock model ID",
    )
    parameters: LLMParameters = Field(
        default_factory=LLMParameters, description="Model parameters"
    )
    stop_sequences: List[str] = Field(
        default_factory=list,
        description="Sequences that will cause the model to stop generating",
    )
    system: Optional[str] = Field(
        default=None,
        description="System prompt",
    )

    rate_limit: int = Field(
        # TODO look up based on model? https://us-west-2.console.aws.amazon.com/servicequotas/home/services/bedrock/quotas
        # aws service-quotas  list-service-quotas --service-code "bedrock"
        default=1_000_000,  # https://docs.aws.amazon.com/general/latest/gr/bedrock.html
        description="Maximum tokens per minute to process",
        ge=100,  # Minimum reasonable limit
        le=10_000_000,  # Maximum reasonable limit
    )


class ChatTemplate(BaseModel):
    name: str
    description: str
    config: LLMConfig
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ChatContentItem(BaseModel):
    """Content of a chat message, which can be text or other media types."""

    text: Optional[str] = None
    thinking: Optional[str] = None
    thinking_signature: Optional[str] = None
    redacted_thinking: Optional[str] = None
    image_data: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_content(self) -> "ChatContentItem":
        """Validate that at least one content type is provided and only one is set"""
        values = self.model_dump()
        content_fields = [
            values.get("text"),
            values.get("thinking"),
            values.get("redacted_thinking"),
            values.get("image_data"),
        ]

        # Check if at least one content field is provided
        if not any(content_fields):
            raise ValueError("At least one content type must be provided")

        # Check if only one content type is provided
        if sum(1 for field in content_fields if field is not None) > 1:
            raise ValueError("Only one content type should be provided")

        return self


ChatContent: TypeAlias = List[ChatContentItem]


class ChatMessage(BaseModel):
    message_id: int
    session_id: str
    content: ChatContent = Field(default_factory=list)
    role: str
    index: int
    created_at: datetime = Field(default_factory=partial(datetime.now, timezone.utc))

    @st.dialog("Edit Message")
    def edit_message(self):
        previous_prompt = self.to_prompt_return()
        logger.debug(f"Editing message: {previous_prompt}")
        st.warning(
            "Editing message will re-run conversation from this point and will replace any existing conversation past this point!",
            icon="⚠️",
        )
        edit_prompt_key = f"edit_prompt_{self.message_id}"
        prompt_return = prompt(
            "edit prompt",
            key=edit_prompt_key,
            placeholder=previous_prompt.text or "",
            main_bottom=False,
            default=previous_prompt,
            enable_clipboard_inspector=True,
        )
        focus_prompt(container_key=edit_prompt_key)

        if prompt_return:
            st.session_state.edit_message_value = self, prompt_return
            close_dialog()
            st.rerun()

        # Delete option
        if st.button(
            ":material/delete_history: Delete Message and All Subsequent Messages",
            key=f"delete_message_edit_dialog",
            type="secondary",
            use_container_width=True,
            help="Delete all messages starting here until the end of the chat history. You will be asked for confirmation.",
        ):
            if st.session_state.get(
                f"confirm_delete_message_edit_dialog",
                False,
            ):
                st.session_state.edit_message_value = self, None
                del st.session_state["confirm_delete_message_edit_dialog"]
                close_dialog()
                st.rerun()
            else:
                st.session_state[f"confirm_delete_message_edit_dialog"] = True
                st.warning("Click again to confirm deletion")

    @staticmethod
    def create(
        role: str,
        content: List[ChatContentItem],
        index: int,
        session_id: Optional[str] = None,
        message_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ) -> "ChatMessage":
        """Create a new ChatMessage object.

        Args:
            role: The role of the message sender (e.g., 'user', 'assistant', 'system').
            content: The content of the message, can be string or structured content.
            index: The position of the message in the conversation sequence.
            session_id: Optional identifier for the chat session. Defaults to empty string.
            message_id: Optional unique identifier for the message. Defaults to -1.

        Returns:
            ChatMessage: A new ChatMessage instance with the specified properties.
        """
        return ChatMessage(
            message_id=message_id or len(st.session_state.messages),
            session_id=session_id or "",
            role=role,
            content=content,
            index=index,
            created_at=created_at or datetime.now(timezone.utc),
        )

    def display(self) -> None:
        # Only show edit button for user messages
        # create uui for this particular message display
        unique_id = str(uuid.uuid4())
        text: str = ""
        with st.container(
            border=True,
            key=f"{self.role}_message_container_{self.message_id}_{unique_id}",
        ):
            with st.chat_message(self.role):
                # if isinstance(self.content, str):
                #     text = self.content
                #     st.markdown(escape_dollarsign(text))
                if isinstance(self.content, list):
                    text_list: List[str] = []
                    thinking_blocks: List[str] = []

                    # First pass: collect thinking blocks and text content
                    for item in self.content:
                        if item.text:
                            text_list.append(item.text)
                        elif item.image_data:
                            pil_image: ImageFile = image_from_b64_image(item.image_data)
                            width: int = pil_image.size[0]
                            st.image(
                                image=pil_image,
                                width=min(width, MAX_IMAGE_WIDTH),
                            )
                        elif item.thinking:
                            thinking_blocks.append(item.thinking)
                        elif item.redacted_thinking:
                            thinking_blocks.append("[Content redacted for safety]")

                    # Display thinking blocks first
                    if thinking_blocks:
                        with st.expander("View reasoning process", expanded=False):
                            for block in thinking_blocks:
                                st.markdown(escape_dollarsign(block))

                    # Then display text content
                    text = "".join(text_list)
                    if text:
                        st.markdown(escape_dollarsign(text))

            message_button_container_key = (
                f"message_button_container_{self.message_id}_{unique_id}"
            )
            message_button_container = st.container(
                border=False, key=message_button_container_key
            )
            with message_button_container:

                message_buttons_key = f"message_buttons_{self.message_id}_{unique_id}"

                options_map: PillOptions = [
                    {
                        "label": ":material/content_copy: Copy",
                        "callback": partial(copy_value_to_clipboard, text),
                    },
                ]
                if self.role == "user":
                    options_map.insert(
                        0,
                        {
                            "label": ":material/edit: Edit",
                            "callback": self.edit_message,
                        },
                    )
                st.segmented_control(
                    "Chat Sessions",
                    options=range(len(options_map)),
                    format_func=lambda option: options_map[option]["label"],
                    selection_mode="single",
                    key=message_buttons_key,
                    on_change=on_pills_change,
                    kwargs=dict(
                        OnPillsChange(
                            key=message_buttons_key,
                            options_map=options_map,
                        )
                    ),
                    label_visibility="collapsed",
                )

    def convert_to_llm_message(self) -> BaseMessage:
        """Convert ChatMessage to LangChain message format.

        Args:
            message: ChatMessage to convert.

        Returns:
            LangChain message object (either HumanMessage or AIMessage).
        """
        if isinstance(self.content, str):
            if self.role == "system":
                return SystemMessage(content=self.content)
            elif self.role == "user":
                return HumanMessage(content=self.content)
            elif self.role == "assistant":
                return AIMessage(content=self.content)
            else:
                raise ValueError(f"Invalid role: {self.role}")
        else:
            # Handle structured content for Anthropic Claude 3.7 thinking blocks
            content_list: List[Any] = []
            for item in self.content:
                if item.text:
                    content_list.append({"type": "text", "text": item.text})
                elif item.thinking:
                    if (
                        st.session_state.app_context.llm.is_thinking_supported()
                    ):
                        content_list.append(
                            {
                                "type": "thinking",
                                "thinking": item.thinking,
                                "signature": item.thinking_signature,
                            }
                        )
                elif item.redacted_thinking:
                    if (
                        st.session_state.app_context.llm.is_thinking_supported()
                    ):
                        content_list.append(
                            {
                                "type": "redacted_thinking",
                                "redacted_thinking": item.redacted_thinking,
                            }
                        )
                elif item.image_data:
                    content_list.append(
                        {
                            "type": "image",
                            "source": {
                                "type": item.metadata.get("format", "base64"),
                                "media_type": item.metadata.get(
                                    "media_type", "image/png"
                                ),
                                "data": item.image_data,
                            },
                        }
                    )

            if self.role == "assistant":
                return AIMessage(content=content_list)
            elif self.role == "user":
                return HumanMessage(content=content_list)
            else:
                return SystemMessage(content=content_list)

    @staticmethod
    def from_system_message(
        system_message: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional["ChatMessage"]:
        """Convert ChatMessage to LangChain SystemMessage.

        Returns:
            LangChain SystemMessage object.
        """
        return (
            ChatMessage.create(
                session_id=session_id,
                role="system",
                content=[ChatContentItem(text=system_message)],
                index=-1,
            )
            if system_message
            else None
        )

    @staticmethod
    def create_from_prompt(
        prompt_data: PromptReturn,
        session_id: Optional[str] = None,
        index: Optional[int] = None,
    ) -> "ChatMessage":
        """Create ChatMessage from user input.

        Args:
            prompt_data: User input containing message and optional images.
            session_id: Optional session ID for the message.
            index: Optional index for the message.

        Returns:
            ChatMessage object containing the user input.
        """
        content_items: ChatContent = []
        if prompt_data.text:
            content_items.append(ChatContentItem(text=prompt_data.text))
        if prompt_data.images:
            for image in prompt_data.images:
                content_items.append(
                    ChatContentItem(
                        image_data=image.data,  # Store the image data in image_url field
                        metadata={
                            "format": image.format,
                            "media_type": image.type,
                        },
                    )
                )

        return ChatMessage.create(
            session_id=session_id,
            role="user",
            content=content_items,
            index=(index if index is not None else len(st.session_state.messages)),
        )

    def to_prompt_return(self) -> PromptReturn:
        """Convert ChatMessage back to PromptReturn format.

        Returns:
            PromptReturn object containing the message text and any images.
        """
        text = None
        images: List[FileData] = []

        logger.debug(
            f"Prompt return raw data from streamlit-chat-prompt: {self.content}"
        )

        if isinstance(self.content, list):
            for item in self.content:
                if isinstance(item, ChatContentItem):
                    if item.text:
                        text = item.text
                    elif item.image_data:
                        images.append(
                            FileData(
                                format=item.metadata.get("format", "base64"),
                                type=item.metadata.get("media_type", "image/jpeg"),
                                data=item.image_data,
                            )
                        )
                else:
                    raise ValueError(f"Invalid content type: {type(item)}")
                # elif isinstance(item, dict):  # For backward compatibility
                #     if item.get("type") == "text":
                #         text = item.get("text")
                #     elif item.get("type") == "image" and "source" in item:
                #         images.append(
                #             ImageData(
                #                 format=item["source"].get("type", "base64"),
                #                 type=item["source"].get("media_type", "image/jpeg"),
                #                 data=item["source"].get("data"),
                #             )
                #         )
        else:
            raise ValueError(f"Invalid content type: {type(self.content)}")

        return PromptReturn(text=text, files=images if images else None)

    def serialize_message_content(self) -> str:
        """Convert a list of ChatContentItem objects to a JSON string for storage."""
        # Convert each ChatContentItem to a dict
        serialized_items = [item.model_dump() for item in self.content]
        return json.dumps(serialized_items)

    @staticmethod
    def deserialize_message_content(content_json: str) -> ChatContent:
        """Convert a JSON string back to a list of ChatContentItem objects."""
        # Parse the JSON string into a list of dicts
        content_data = json.loads(content_json)

        # Convert each dict back to a ChatContentItem
        return [ChatContentItem.model_validate(item) for item in content_data]


class ChatSession(BaseModel):
    title: str
    config: LLMConfig
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=partial(datetime.now, timezone.utc))
    last_active: datetime = Field(default_factory=partial(datetime.now, timezone.utc))
    is_private: bool = False
    input_tokens_used: int = 0
    output_tokens_used: int = 0


class ChatExport(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]
    exported_at: datetime = Field(default_factory=partial(datetime.now, timezone.utc))
