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

MAX_IMAGE_WIDTH = 300


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
        if "messages" not in st.session_state:
            st.session_state.messages = []  # List[ChatMessage]
        if "current_session_id" not in st.session_state:
            st.session_state.current_session_id = None  # str

    def render(self):
        """
        Render the chat interface, displaying chat history and handling user input.
        """
        self._display_chat_history()
        self._handle_chat_input()

    def _display_chat_history(self):
        """
        Display the chat history in the Streamlit interface.
        """
        for message in st.session_state.messages:
            with st.chat_message(message.additional_kwargs["role"]):
                if isinstance(message.content, str):
                    st.markdown(message.content)
                elif isinstance(message.content, list):
                    for item in message.content:
                        if isinstance(item, str):
                            st.markdown(item)
                        elif isinstance(item, dict):
                            if "type" in item:
                                if item["type"] == "text":
                                    st.markdown(item["text"])
                                elif item["type"] == "image":
                                    pil_image = self._image_from_b64_image(
                                        item["source"]["data"]
                                    )
                                    width, height = pil_image.size
                                    st.image(
                                        pil_image, width=min(width, MAX_IMAGE_WIDTH)
                                    )
                            else:
                                # just display the dict if format unknown
                                st.json(item)
                        else:
                            st.write(item)  # Fallback for unexpected types
                else:
                    st.write(message.content)  # Fallback for unexpected content type

    def _handle_chat_input(self):
        """
        Handle user input from the chat interface.
        """
        user_input = prompt("chat_input", key="user_input", placeholder="Hello!")
        # user_input = st.chat_input("chat_input", key="input")
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
            self.storage.save_message(
                ChatMessage(
                    session_id=st.session_state.current_session_id,
                    role="user",
                    content=content,
                )
            )

    def _generate_session_title(self, human_message: str, ai_response: str) -> str:
        """
        Generate a concise session title using the LLM with full conversation context.

        Args:
            human_message (str): The initial message from the human user.
            ai_response (str): The AI's response to the human message.

        Returns:
            str: A concise title for the chat session, typically 2-4 words long.

        This method uses the language model to create a brief summary of the conversation
        topic, which is then used as the title for the chat session. If the LLM fails to
        generate a valid title, it falls back to using a timestamp.
        """
        title_prompt = HumanMessage(
            content=f"""Summarize this conversation's topic in up to 5 words or about 40 characters. More details are useful, but space is limited to show this summary, so ideally 2-4 words.
            Be direct and concise, no explanations needed.
            
            Conversation:
            Human: {human_message}
            Assistant: {ai_response}"""
        )

        title = self.llm.invoke([title_prompt]).content.strip('" \n').strip()

        # Fallback to timestamp if we get an empty or invalid response
        if not title:
            title = f"Chat {datetime.now()}"

        print(f"New session title: {title}")
        return title

    def _generate_ai_response(self):
        """
        Generate and display an AI response based on the current chat session.

        This method streams the AI's response, displays it in the chat interface,
        creates a new chat session if necessary, and saves the response to storage.

        Returns:
            None
        """
        print("AI: ")

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

            # Update last_update timestamp
            st.session_state.last_update = datetime.now()

            # Now rerun after the complete conversation turn is saved
            st.rerun()
