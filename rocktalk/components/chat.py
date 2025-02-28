"""Chat interface module for handling user-AI conversations with support for text and images."""

from datetime import datetime
from typing import Optional, cast

import streamlit as st
from langchain.schema import BaseMessage
from models.interfaces import ChatMessage, ChatSession, TurnState
from models.llm import LLMInterface
from models.storage_interface import StorageInterface
from streamlit_chat_prompt import PromptReturn, pin_bottom, prompt
from streamlit_shortcuts import button
from utils.js import (
    adjust_chat_message_style,
    focus_prompt,
    scroll_to_bottom,
    scroll_to_bottom_streaming,
)
from utils.log import logger
from utils.streamlit_utils import escape_dollarsign


class ChatInterface:
    """Interface for managing chat interactions between users and AI.

    This class handles the display of chat history, processing of user input,
    generation of AI responses, and management of chat sessions.

    Attributes:
        storage (StorageInterface): Interface for persistent storage of chat data.
        llm (LLMInterface): Interface for the language model providing AI responses.
    """

    storage: StorageInterface
    llm: LLMInterface

    def __init__(self) -> None:
        """Initialize the chat interface.

        Args:
            storage: Storage interface for persisting chat data.
            llm: Language model interface for generating responses.
        """
        self.storage: StorageInterface = st.session_state.storage
        self.llm: LLMInterface = st.session_state.llm

        if "turn_state" not in st.session_state:
            st.session_state.turn_state = TurnState.HUMAN_TURN
        if "messages" not in st.session_state:
            st.session_state.messages = []  # List[ChatMessage]
        if "current_session_id" not in st.session_state:
            st.session_state.current_session_id = None  # str
        if "edit_message_value" not in st.session_state:
            st.session_state.edit_message_value = None  # ChatMessage, PromptReturn
        if "skip_next_scroll" not in st.session_state:
            st.session_state.skip_next_scroll = False
        if "needs_title_generation" not in st.session_state:
            st.session_state.needs_title_generation = False

    def render(self) -> None:
        """Render the chat interface and handle the current turn state."""
        self._handle_edit_message()
        self._display_chat_history()
        self._handle_chat_input()
        self._generate_ai_response()
        self._generate_title()
        self._finish_conversation_turn()

    def _stop_chat_stream(self):
        st.toast("Stopping stream")
        st.session_state.stop_chat_stream = True

    def _display_chat_history(self) -> None:
        """Display the chat history in the Streamlit interface."""
        # print(st.session_state.theme)

        if "theme" in st.session_state and st.session_state.theme:
            adjust_chat_message_style()

        system_message = self.llm.get_state_system_message()
        if system_message:
            system_message.display()

        for message in st.session_state.messages:
            message: ChatMessage
            message.display()

        st.session_state.scroll_div_index = 0

        # Don't scroll if we just copied a message
        # TODO figure out why the page reloads 3 times?? Maybe something to do with the copy js iframe loading?
        if st.session_state.message_copied > 0:
            st.session_state.message_copied -= 1
        else:
            scroll_to_bottom()

    def _handle_edit_message(self) -> None:
        if st.session_state.edit_message_value:
            original_message: ChatMessage = st.session_state.edit_message_value[0]
            prompt_return: Optional[PromptReturn] = st.session_state.edit_message_value[
                1
            ]

            # Remove this message and all following messages
            st.session_state.messages = st.session_state.messages[
                : original_message.index
            ]

            if not st.session_state.get("temporary_session", False):
                st.session_state.storage.delete_messages_from_index(
                    session_id=st.session_state.current_session_id,
                    from_index=original_message.index,
                )

            st.session_state.turn_state = TurnState.HUMAN_TURN

            # if prompt_return provided, we use the new value and pass control back to AI
            if prompt_return:
                new_message = ChatMessage.create_from_prompt(
                    prompt_data=prompt_return,
                    session_id=original_message.session_id,
                    index=original_message.index,
                )

                # Add edited message
                st.session_state.messages.append(new_message)
                if not st.session_state.get("temporary_session", False):
                    st.session_state.storage.save_message(message=new_message)

                # Set turn state to AI_TURN to generate new response
                st.session_state.turn_state = TurnState.AI_TURN

            st.session_state.edit_message_value = None

    def _handle_chat_input(self) -> None:
        """Handle user input from the chat interface.

        Gets input from the chat prompt and processes it if provided.
        """
        prompt_container_key = "prompt_container"
        pin_bottom(prompt_container_key)
        prompt_container = st.container(key=prompt_container_key)
        # st.session_state.prompt_container =
        with prompt_container:
            self.prompt_placeholder = (
                st.empty()
            )  # Note only one thing can exist in an st.empty() so need to use a container if more than one streamlit object is supposed to be in this container
            with self.prompt_placeholder:
                chat_prompt_return: Optional[PromptReturn] = prompt(
                    name="chat_input",
                    key="main_prompt",
                    placeholder="Hello!",
                    disabled=False,
                    max_image_size=5 * 1024 * 1024,
                    default=st.session_state.user_input_default
                    or st.session_state.stored_user_input,
                    enable_clipboard_inspector=True,
                )
                if chat_prompt_return:
                    logger.info(f"Received user text input:\n{chat_prompt_return.text}")
                    st.session_state.stored_user_input = chat_prompt_return
        focus_prompt(prompt_container_key)
        st.session_state.user_input_default = None

        if chat_prompt_return and st.session_state.turn_state == TurnState.HUMAN_TURN:
            human_message: ChatMessage = ChatMessage.create_from_prompt(
                prompt_data=chat_prompt_return,
                session_id=st.session_state.current_session_id,
            )

            human_message.display()
            st.session_state.scroll_div_index += 1
            scroll_to_bottom()

            # Create new session if needed
            if (
                not st.session_state.get("temporary_session", False)
                and not st.session_state.current_session_id
            ):
                config = self.llm.get_config().model_copy(deep=True)
                new_session: ChatSession = ChatSession(
                    title=f"New Chat {datetime.now().isoformat()}",  # Temporary title until first AI response
                    config=config,
                    total_tokens_used=st.session_state.get("temp_session_tokens", 0),
                )
                st.session_state.current_session_id = new_session.session_id
                st.session_state.needs_title_generation = (
                    True  # Flag to generate title after first AI response
                )
                self.storage.store_session(new_session)
                human_message.session_id = new_session.session_id

            # Save message to storage if we have a non-temporary session
            if st.session_state.current_session_id and not st.session_state.get(
                "temporary_session", False
            ):
                self.storage.save_message(message=human_message)

            st.session_state.messages.append(human_message)

            # Set state for AI to respond
            st.session_state.turn_state = TurnState.AI_TURN

    def load_session(self, session_id: str):
        if st.session_state.current_session_id == session_id:
            return
        session = self.storage.get_session(session_id)
        st.session_state.current_session_id = session_id
        st.session_state.messages = self.storage.get_messages(session.session_id)
        st.session_state.temporary_session = False

        # Load session settings
        self.llm.update_config(session.config)
        logger.info(f"Loaded session {session.session_id} with title: {session.title}")
        logger.debug(f"Loaded session config: {session.config}")

    def _generate_ai_response(self) -> None:
        """Generate and display an AI response."""
        if st.session_state.turn_state == TurnState.AI_TURN:

            # Convert messages to LLM format
            llm_messages: list[BaseMessage] = self.llm.convert_messages_to_llm_format()

            with st.container(border=True, key="assistant_message_container_streaming"):
                # Generate and display AI response
                with st.chat_message("assistant"):
                    thinking_placeholder = st.empty()  # For displaying thinking blocks
                    message_placeholder = st.empty()

                    try:
                        with self.prompt_placeholder:
                            # add a stop stream button
                            with st.container():
                                button(
                                    label="Stop (⌘/⊞ + ⌫)",
                                    shortcut="Meta+backspace",
                                    help="Stop the current stream (⌘/⊞ + ⌫)",
                                    icon="🛑",
                                    on_click=self._stop_chat_stream,
                                    use_container_width=True,
                                )
                        full_response: str = ""
                        thinking_content = ""

                        scroll_to_bottom_streaming()

                        for chunk in self.llm.stream(input=llm_messages):
                            if st.session_state.stop_chat_stream:
                                logger.info("Interrupting stream")
                                break

                            # Check if this is the final chunk
                            if chunk.get("done", False):
                                # Final chunk with metadata
                                continue

                                # Handle different chunk types
                            if chunk.get("is_thinking_block", False):
                                # This is a thinking block
                                has_thinking = True
                                thinking_content += chunk["content"] or ""

                                # Display thinking in an expander
                                with thinking_placeholder.container():
                                    with st.expander(
                                        "View reasoning process", expanded=True
                                    ):
                                        st.markdown(f"```\n{thinking_content}\n```")
                            else:
                                # Regular text content
                                full_response += chunk["content"]
                                message_placeholder.markdown(
                                    escape_dollarsign(full_response + "▌")
                                )

                        # Display final response (without cursor)
                        message_placeholder.markdown(escape_dollarsign(full_response))

                    except Exception as e:
                        # logger.error(f"Error in LLM stream: {e}")
                        import traceback

                        logger.error(
                            f"Error in LLM stream. Full stack trace: \n{traceback.format_exc()}"
                        )

                        # Display an error message to the user without altering the chat history
                        st.error(
                            f'An error occurred while generating the AI response. You can click "Retry" to retry chat generation or "Cancel" to edit your prompt.\n\n{e}'
                        )

                        # Set the turn state back to HUMAN_TURN
                        # st.session_state.turn_state = TurnState.HUMAN_TURN

                        # Optionally, provide a retry mechanism
                        col1, col2 = st.columns(2)
                        retry_clicked = False
                        cancel_clicked = False

                        with col1:
                            retry_clicked = st.button(
                                "Retry",
                                use_container_width=True,
                            )
                            if retry_clicked:
                                # If "Retry" was clicked, we have already rerun the script, so the code below will not execute.
                                st.session_state.turn_state = TurnState.AI_TURN
                                logger.info("Retrying AI response")
                                # Optionally rerun the script to immediately process the AI response
                                st.rerun()

                        with col2:
                            cancel_clicked = st.button(
                                ":material/cancel: Cancel",
                                use_container_width=True,
                            )
                            if cancel_clicked:
                                # If "Cancel" was clicked, we need the code to continue to handle the cancellation.
                                st.session_state.stop_chat_stream = True
                                logger.info("Cancelling AI response, stopping stream")
                                # Do not return here; let the code continue to handle the cancellation.

                        st.markdown("")  # added to help with autoscroller

                        # If neither button was clicked, we return to wait for the user's action.
                        if not (retry_clicked or cancel_clicked):
                            return

                    # Handle stream interruption
                    if st.session_state.stop_chat_stream:
                        st.session_state.stop_chat_stream = False
                        message_placeholder.empty()
                        thinking_placeholder.empty()
                        st.session_state.turn_state = TurnState.HUMAN_TURN

                        # Remove the last messages
                        if len(st.session_state.messages) > 0:
                            last_human_message: ChatMessage = (
                                st.session_state.messages.pop()
                            )

                            # Remove the message from storage if needed
                            if (
                                st.session_state.current_session_id
                                and not st.session_state.get("temporary_session", False)
                            ):
                                self.storage.delete_messages_from_index(
                                    session_id=st.session_state.current_session_id,
                                    from_index=last_human_message.index,
                                )

                            st.session_state.user_input_default = (
                                last_human_message.to_prompt_return()
                            )

                        st.rerun()

    def _generate_title(self) -> None:
        # Generate title after first AI response if needed
        if st.session_state.get("needs_title_generation", False):
            title: str = self.llm.generate_session_title()
            session = self.storage.get_session(st.session_state.current_session_id)
            session.title = title
            self.storage.update_session(session)
            st.session_state.needs_title_generation = False

    def _finish_conversation_turn(self) -> None:
        if st.session_state.turn_state == TurnState.AI_TURN:
            # Update state for next human input
            st.session_state.turn_state = TurnState.HUMAN_TURN
            st.session_state.stored_user_input = None
            st.rerun()
