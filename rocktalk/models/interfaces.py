import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from functools import partial
from typing import Any, List, Optional

import streamlit as st
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from PIL.ImageFile import ImageFile
from pydantic import BaseModel, Field
from streamlit_chat_prompt import ImageData, PromptReturn, prompt
from streamlit_js_eval import streamlit_js_eval
from utils.image_utils import MAX_IMAGE_WIDTH, image_from_b64_image
from utils.js import focus_prompt
from utils.log import logger
from utils.streamlit_utils import (
    OnPillsChange,
    PillOptions,
    close_dialog,
    escape_dollarsign,
    on_pills_change,
)


def find_iframe_js():
    return """
    function findIFrameFunction(funcName) {
        console.log('findIFrameFunction: ', funcName);
        const iframes = window.parent.document.getElementsByClassName("stIFrame");
        for (let iframe of iframes) {
            try {
                console.log('iframe: ', iframe);
                if (iframe.contentWindow && iframe.contentWindow[funcName]) {
                    return iframe.contentWindow[funcName];
                }
            } catch (err) {
                console.error('Error accessing iframe:', err);
            }
        }
        return null;
    }
    """


def expand_button_height(target_key: str):
    return
    target_key = json.dumps(f".st-key-{target_key} button")
    streamlit_js_eval(
        js_expressions=f"""
    {find_iframe_js()}

    findIFrameFunction('expandButton')({target_key});
    """
    )


def copy_value_to_clipboard(value: str):
    value = json.dumps(value)
    # with stylized_container("copy_to_clipboard_boo"):
    streamlit_js_eval(
        js_expressions=f"""
    {find_iframe_js()}

    findIFrameFunction('initAndCopy')({value});
    """
    )
    st.toast(body="Copied to clipboard", icon="📋")
    # See note in chat.py
    st.session_state.message_copied = 3


class LLMParameters(BaseModel):
    temperature: float = 0.5
    max_output_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None  # Additional parameter for Anthropic models


_DEFAULT_LLM_CONFIG: Optional["LLMConfig"] = None


class LLMConfig(BaseModel):
    bedrock_model_id: str
    parameters: LLMParameters
    stop_sequences: List[str] = Field(default_factory=list)
    system: Optional[str] = None


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


class ChatTemplate(BaseModel):
    name: str
    description: str
    config: LLMConfig
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ChatMessage(BaseModel):
    message_id: int
    session_id: str
    role: str
    content: str | list[str | dict]
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
        )
        focus_prompt(container_key=edit_prompt_key)

        if prompt_return:
            st.session_state.edit_message_value = self, prompt_return
            close_dialog()
            st.rerun()

        # Delete option
        if st.button(
            ":material/delete_history: Trim History from Here",
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
        content: Any,
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
                if isinstance(self.content, str):
                    text = self.content
                elif isinstance(self.content, list):
                    text_list: List[str] = []
                    for item in self.content:
                        if isinstance(item, dict):
                            if item["type"] == "text":
                                text_list.append(item["text"])
                            elif item["type"] == "image":
                                pil_image: ImageFile = image_from_b64_image(
                                    item["source"]["data"]
                                )
                                width: int = pil_image.size[0]
                                st.image(
                                    image=pil_image,
                                    width=min(width, MAX_IMAGE_WIDTH),
                                )
                        else:
                            text_list.append(str(item))
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
        if self.role == "system":
            return SystemMessage(
                content=self.content, additional_kwargs={"role": "system"}
            )
        elif self.role == "user":
            return HumanMessage(
                content=self.content, additional_kwargs={"role": "user"}
            )
        elif self.role == "assistant":
            return AIMessage(
                content=self.content, additional_kwargs={"role": "assistant"}
            )
        raise ValueError(f"Unsupported message role: {self.role}")

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
                content=str(system_message),
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
        content = []
        if prompt_data.text:
            content.append({"type": "text", "text": prompt_data.text})
        if prompt_data.images:
            for image in prompt_data.images:
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": image.format,
                            "media_type": image.type,
                            "data": image.data,
                        },
                    }
                )

        return ChatMessage.create(
            session_id=session_id,
            role="user",
            content=content,
            index=(index if index is not None else len(st.session_state.messages)),
        )

    def to_prompt_return(self) -> PromptReturn:
        """Convert ChatMessage back to PromptReturn format.

        Returns:
            PromptReturn object containing the message text and any images.
        """
        text = None
        images = []
        logger.debug(
            f"Prompt return raw data from streamlit-chat-prompt: {self.content}"
        )
        if isinstance(self.content, list):
            for item in self.content:
                if isinstance(item, dict):
                    if item["type"] == "text":
                        text = item["text"]
                    elif item["type"] == "image":
                        images.append(
                            ImageData(
                                format=item["source"]["type"],
                                type=item["source"]["media_type"],
                                data=item["source"]["data"],
                            )
                        )
        elif isinstance(self.content, str):
            text = self.content

        return PromptReturn(text=text, images=images if images else None)


class ChatSession(BaseModel):
    title: str
    config: LLMConfig
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=partial(datetime.now, timezone.utc))
    last_active: datetime = Field(default_factory=partial(datetime.now, timezone.utc))
    is_private: bool = False


class ChatExport(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]
    exported_at: datetime = Field(default_factory=partial(datetime.now, timezone.utc))
