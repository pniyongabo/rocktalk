import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from PIL.ImageFile import ImageFile
from langchain.schema import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field
from streamlit_chat_prompt import PromptReturn
import streamlit as st
from utils.image_utils import image_from_b64_image, MAX_IMAGE_WIDTH


class ChatMessage(BaseModel):
    session_id: str
    role: str
    content: str | list[str | dict]
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    def display(self) -> None:
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
                            st.image(image=pil_image, width=min(width, MAX_IMAGE_WIDTH))
                    else:
                        st.markdown(str(item))

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
        user_input: PromptReturn, session_id: Optional[str] = None
    ) -> "ChatMessage":
        """Create ChatMessage from user input.

        Args:
            user_input: User input containing message and optional images.
            session_id: Optional session ID for the message.

        Returns:
            ChatMessage object containing the user input.
        """
        content = []
        if user_input.message:
            content.append({"type": "text", "text": user_input.message})
        if user_input.images:
            for image in user_input.images:
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

        return ChatMessage(session_id=session_id or "", role="user", content=content)


class ChatSession(BaseModel):
    session_id: str
    title: str
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    message_count: Optional[int] = None
    first_message: Optional[datetime] = None
    last_message: Optional[datetime] = None

    @staticmethod
    def create(
        title: str,
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
        last_active: Optional[datetime] = None,
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
        )


class ChatExport(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]
    exported_at: datetime = Field(default_factory=datetime.now)
