import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Protocol, Sequence

import streamlit as st
from langchain.schema import AIMessage, BaseMessage, HumanMessage
from PIL.ImageFile import ImageFile
from pydantic import BaseModel, Field, PrivateAttr
from streamlit_chat_prompt import ImageData, PromptReturn, prompt
from utils.image_utils import MAX_IMAGE_WIDTH, image_from_b64_image
from utils.streamlit_utils import close_dialog


class LLMParameters(BaseModel):
    temperature: float
    max_output_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None  # Additional parameter for Anthropic models


class LLMPresetName(Enum):
    BALANCED = "Balanced"
    DETERMINISTIC = "Deterministic"
    CREATIVE = "Creative"
    CUSTOM = "Custom"


PRESET_CONFIGS: Dict[LLMPresetName, LLMParameters] = {
    LLMPresetName.DETERMINISTIC: LLMParameters(temperature=0.0),
    LLMPresetName.CREATIVE: LLMParameters(temperature=0.9),
    LLMPresetName.BALANCED: LLMParameters(temperature=0.5),
}


_DEFAULT_LLM_CONFIG: Optional["LLMConfig"] = None


class LLMConfig(BaseModel):
    model_id: str
    region_name: str
    parameters: LLMParameters
    stop_sequences: List[str] = Field(default_factory=list)
    system: Optional[str] = None
    # guardrail_config: Optional[Dict[str, Any]] = None
    # additional_model_request_fields: Optional[Dict[str, Any]] = None
    # additional_model_response_field_paths: Optional[List[str]] = None
    # disable_streaming: bool = False
    # supports_tool_choice_values: Optional[Sequence[Literal["auto", "any", "tool"]]] = (
    #     None
    # )

    def get_parameters(self) -> LLMParameters:
        return self.parameters

    @staticmethod
    def get_default() -> "LLMConfig":
        global _DEFAULT_LLM_CONFIG
        if _DEFAULT_LLM_CONFIG is None:
            preset_parm = PRESET_CONFIGS[LLMPresetName.BALANCED]
            _DEFAULT_LLM_CONFIG = LLMConfig(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                region_name="us-west-2",
                parameters=preset_parm,
            )

        return _DEFAULT_LLM_CONFIG

    @staticmethod
    def set_default(llm_config: "LLMConfig") -> None:
        global _DEFAULT_LLM_CONFIG
        _DEFAULT_LLM_CONFIG = llm_config.model_copy()


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


class ChatMessage(BaseModel):
    session_id: str
    role: str
    content: str | list[str | dict]
    index: int
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    @st.dialog("Edit Message")
    def edit_message(self):
        previous_prompt = self.to_prompt_return()
        st.warning(
            "Editing message will re-run conversation from this point and will replace any existing conversation past this point!",
            icon="⚠️",
        )
        prompt_return = prompt(
            "edit prompt",
            key=f"edit_prompt_{id(self)}",
            placeholder=previous_prompt.text or "",
            main_bottom=False,
            default=previous_prompt,
        )

        if prompt_return:
            st.session_state.edit_message_value = self, prompt_return
            close_dialog()
            st.rerun()

    def display(self) -> None:
        # Only show edit button for user messages
        col1, col2 = st.columns([0.9, 0.1])
        with col1:

            with st.chat_message(self.role):
                if isinstance(self.content, str):
                    st.markdown(self.content)
                elif isinstance(self.content, list):
                    for item in self.content:
                        if isinstance(item, dict):
                            if item["type"] == "text":
                                st.markdown(item["text"])
                            elif item["type"] == "image":
                                pil_image: ImageFile = image_from_b64_image(
                                    item["source"]["data"]
                                )
                                width: int = pil_image.size[0]
                                st.image(
                                    image=pil_image, width=min(width, MAX_IMAGE_WIDTH)
                                )
                        else:
                            st.markdown(str(item))
            with col2:
                if self.role == "user":
                    if st.button("✎", key=f"edit_{id(self)}"):
                        self.edit_message()

    def convert_to_llm_message(self) -> BaseMessage:
        """Convert ChatMessage to LangChain message format.

        Args:
            message: ChatMessage to convert.

        Returns:
            LangChain message object (either HumanMessage or AIMessage).
        """
        if self.role == "user":
            return HumanMessage(
                content=self.content, additional_kwargs={"role": "user"}
            )
        elif self.role == "assistant":
            return AIMessage(
                content=self.content, additional_kwargs={"role": "assistant"}
            )
        raise ValueError(f"Unsupported message role: {self.role}")

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

        return ChatMessage(
            session_id=session_id or "",
            role="user",
            content=content,
            index=index if index is not None else len(st.session_state.messages),
        )

    def to_prompt_return(self) -> PromptReturn:
        """Convert ChatMessage back to PromptReturn format.

        Returns:
            PromptReturn object containing the message text and any images.
        """
        text = None
        images = []

        if isinstance(self.content, list):
            for item in self.content:
                if isinstance(item, dict):
                    if item["type"] == "text":
                        message = item["text"]
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
    session_id: str
    title: str
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    message_count: Optional[int] = None
    first_message: Optional[datetime] = None
    last_message: Optional[datetime] = None
    config: LLMConfig = Field(default_factory=LLMConfig.get_default)

    @staticmethod
    def create(
        title: str,
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
        last_active: Optional[datetime] = None,
        config: Optional[LLMConfig] = None,
    ) -> "ChatSession":
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        current_time = datetime.now()
        created_at = created_at or current_time
        last_active = last_active or created_at

        return ChatSession(
            session_id=session_id,
            title=title,
            metadata=metadata or {},
            created_at=created_at,
            last_active=last_active,
            config=config or st.session_state.llm.get_config(),
        )


class ChatExport(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]
    exported_at: datetime = Field(default_factory=datetime.now)
