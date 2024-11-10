from datetime import datetime
from typing import List, cast

import streamlit as st
from langchain.schema import AIMessage, HumanMessage
from langchain_core.messages.ai import AIMessageChunk
from streamlit_chat_prompt import prompt, PromptReturn
from models.interfaces import ChatMessage, ChatSession, LLMInterface, StorageInterface
import base64
from io import BytesIO
from PIL import ImageFile, Image

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


class ChatInterface:
    """
    A class to handle the chat interface, including displaying chat history and processing user input.

    Args:
        storage (StorageInterface): An interface for storing chat data.
        llm (LLMInterface): An interface for the language model.

    Attributes:
        storage (StorageInterface): The storage interface instance.
        llm (LLMInterface): The language model interface instance.
    """

    def __init__(self, storage: StorageInterface, llm: LLMInterface):
        self.storage = storage
        self.llm = llm
        if "turn_state" not in st.session_state:
            st.session_state.turn_state = TurnState.HUMAN_TURN
        if "messages" not in st.session_state:
            st.session_state.messages = []  # List[ChatMessage]
        if "current_session_id" not in st.session_state:
            st.session_state.current_session_id = None  # str

    def render(self):
        """
        Render the chat interface, displaying chat history and handling user input.
        """
        self._display_chat_history()

        if st.session_state.turn_state == TurnState.HUMAN_TURN:
            self._handle_chat_input()
        elif st.session_state.turn_state == TurnState.AI_TURN:
            self._generate_ai_response()

        if user_input:
            self._process_user_input(user_input)
            self._generate_ai_response()

    def _image_from_b64_image(self, b64_image: str) -> ImageFile.ImageFile:
        """
        Convert a base64-encoded image string to a PIL Image object.

        Args:
            b64_image (str): Base64-encoded image string.
        Returns:
            ImageFile.ImageFile: PIL Image object.
        """
        image_data = base64.b64decode(b64_image)
        image = Image.open(BytesIO(image_data))
        return image

    def _prepare_content_from_user_input(self, user_input: PromptReturn) -> List[dict]:
        """
        Prepare content from user input for processing.

        Args:
            user_input (PromptReturn): User input object containing message and images.

        Returns:
            List[dict]: Prepared content as a list of dictionaries.
        """
        content = []
        if user_input.message:
            content.append({"type": "text", "text": user_input.message})
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
        return content

    def _process_user_input(self, user_input: PromptReturn):
        """
        Process user input, display it in the chat interface, and save it to storage.

        Args:
            user_input (PromptReturn): User input object containing message and images.
        """
        print(f"\nHuman: {user_input}")

        # Display user message and images in the Streamlit chat interface
        with st.chat_message("user"):
            # Display the text message
            st.markdown(user_input.message)

            # Display any images uploaded by the user
            for image in user_input.images:
                pil_image = self._image_from_b64_image(image.data)
                width, _height = pil_image.size
                # Limit the display width of the image
                st.image(
                    pil_image,
                    width=min(MAX_IMAGE_WIDTH, width),
                )

        # Prepare the content for the LLM, including both text and images
        content = self._prepare_content_from_user_input(user_input)

        # Create a HumanMessage object with the prepared content
        human_input = HumanMessage(content=content, additional_kwargs={"role": "user"})

        # Add the user's message to the session state
        st.session_state.messages.append(human_input)

        # If there's an active chat session, save the user's message to storage
        if st.session_state.current_session_id:

        # Set state for AI to respond
        st.session_state.turn_state = TurnState.AI_TURN

        # Generate and display AI response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            for chunk in st.session_state.llm.stream(st.session_state.messages):
                chunk = cast(AIMessageChunk, chunk)
                for item in chunk.content:
                    if isinstance(item, dict) and "text" in item:
                        text = item["text"]
                        full_response += text
                        print(text, end="", flush=True)

                    message_placeholder.markdown(full_response + "▌")

                if chunk.response_metadata:
                    print(chunk.response_metadata)
                if chunk.usage_metadata:
                    print(type(chunk))
                    print(chunk.usage_metadata)

            # Save AI response
            ai_response = AIMessage(
                content=full_response, additional_kwargs={"role": "assistant"}
            )

            # Create new session if none exists
            if not st.session_state.current_session_id:
                # Get the human message that started this conversation
                human_message = st.session_state.messages[-1].content
                title = self._generate_session_title(human_message, full_response)
                new_session = ChatSession.create(
                    title=title,
                    subject=title,
                    metadata={"model": "anthropic.claude-3-sonnet-20240229-v1:0"},
                )
                self.storage.store_session(new_session)

                st.session_state.current_session_id = new_session.session_id
                # Save the initial human message now that we have a session
                self.storage.save_message(
                    ChatMessage(
                        session_id=st.session_state.current_session_id,
                        role="user",
                        content=human_message,
                    )
                )

            st.session_state.messages.append(ai_response)

            # Save to storage
            self.storage.save_message(
                ChatMessage(
                    session_id=st.session_state.current_session_id,
                    role="assistant",
                    content=full_response,
                )
            )

            message_placeholder.markdown(full_response)

            # Update state for next human input
            st.session_state.turn_state = TurnState.HUMAN_TURN
            st.session_state.last_update = datetime.now()

            # Now rerun after the complete conversation turn is saved
            st.rerun()
