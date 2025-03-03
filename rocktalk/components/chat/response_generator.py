# rocktalk/components/chat/response_generator.py
import traceback

import streamlit as st
from app_context import AppContext
from components.base import Component
from models.llm import TurnState
from streamlit_shortcuts import button
from utils.js import scroll_to_bottom_streaming
from utils.log import logger
from utils.streamlit_utils import escape_dollarsign


class ResponseGenerator(Component):
    """Component responsible for generating AI responses"""

    def __init__(self, ctx: AppContext, prompt_placeholder=None):
        """
        Initialize the response generator component

        Args:
            ctx: Application context
            prompt_placeholder: Optional placeholder for prompt UI elements
        """
        super().__init__(ctx)
        self.prompt_placeholder = prompt_placeholder

    def render(self) -> None:
        """Generate and render the AI response if it's the AI's turn"""
        if st.session_state.turn_state != TurnState.AI_TURN:
            return

        # Convert messages to LLM format
        llm_messages = self.ctx.llm.convert_messages_to_llm_format()

        with st.container(border=True, key="assistant_message_container_streaming"):
            # Generate and display AI response
            with st.chat_message("assistant"):
                thinking_placeholder = st.empty()  # For displaying thinking blocks
                message_placeholder = st.empty()

                try:
                    self._show_stop_button()
                    self._stream_response(
                        thinking_placeholder, message_placeholder, llm_messages
                    )

                except Exception as e:
                    self._handle_error(e, message_placeholder)

        # Generate title if needed
        if st.session_state.get("needs_title_generation", False):
            self._generate_title()

        # Update state for next human input
        st.session_state.turn_state = TurnState.HUMAN_TURN
        st.session_state.stored_user_input = None
        st.rerun()

    def _show_stop_button(self):
        """Show stop button if prompt placeholder is available"""
        if self.prompt_placeholder:
            with self.prompt_placeholder:
                with st.container():
                    button(
                        label="Stop (⌘/⊞ + ⌫)",
                        shortcut="Meta+backspace",
                        help="Stop the current stream (⌘/⊞ + ⌫)",
                        icon="🛑",
                        on_click=self._stop_chat_stream,
                        use_container_width=True,
                    )

    def _stop_chat_stream(self):
        """Stop the streaming response"""
        st.toast("Stopping stream")
        st.session_state.stop_chat_stream = True

    def _stream_response(self, thinking_placeholder, message_placeholder, llm_messages):
        """Stream the AI response"""
        full_response = ""
        thinking_content = ""

        scroll_to_bottom_streaming()

        for chunk in self.ctx.llm.stream(input=llm_messages):
            if st.session_state.stop_chat_stream:
                logger.info("Interrupting stream")
                break

            # Check if this is the final chunk
            if chunk.get("done", False):
                continue

            # Handle different chunk types
            if chunk.get("is_thinking_block", False):
                # This is a thinking block
                thinking_content += chunk["content"] or ""

                # Display thinking in an expander
                with thinking_placeholder.container():
                    with st.expander("View reasoning process", expanded=True):
                        st.markdown(f"```\n{thinking_content}\n```")
            else:
                # Regular text content
                full_response += chunk["content"]
                message_placeholder.markdown(escape_dollarsign(full_response + "▌"))

        # Display final response (without cursor)
        message_placeholder.markdown(escape_dollarsign(full_response))

        # Handle stream interruption
        if st.session_state.stop_chat_stream:
            self._handle_stream_interruption(thinking_placeholder, message_placeholder)

    def _handle_stream_interruption(self, thinking_placeholder, message_placeholder):
        """Handle interruption of streaming response"""
        st.session_state.stop_chat_stream = False
        message_placeholder.empty()
        thinking_placeholder.empty()
        st.session_state.turn_state = TurnState.HUMAN_TURN

        # Remove the last messages
        if len(st.session_state.messages) > 0:
            last_human_message = st.session_state.messages.pop()

            # Remove the message from storage if needed
            if st.session_state.current_session_id and not st.session_state.get(
                "temporary_session", False
            ):
                self.ctx.storage.delete_messages_from_index(
                    session_id=st.session_state.current_session_id,
                    from_index=last_human_message.index,
                )

            st.session_state.user_input_default = last_human_message.to_prompt_return()

        st.rerun()

    def _handle_error(self, e, message_placeholder):
        """Handle errors during response generation"""
        logger.error(
            f"Error in LLM stream. Full stack trace: \n{traceback.format_exc()}"
        )

        # Display an error message to the user without altering the chat history
        st.error(
            f'An error occurred while generating the AI response. You can click "Retry" to retry chat generation or "Cancel" to edit your prompt.\n\n{e}'
        )

        # Optionally, provide a retry mechanism
        col1, col2 = st.columns(2)
        retry_clicked = False
        cancel_clicked = False

        with col1:
            retry_clicked = st.button("Retry", use_container_width=True)
            if retry_clicked:
                st.session_state.turn_state = TurnState.AI_TURN
                logger.info("Retrying AI response")
                st.rerun()

        with col2:
            cancel_clicked = st.button(
                ":material/cancel: Cancel", use_container_width=True
            )
            if cancel_clicked:
                st.session_state.stop_chat_stream = True
                logger.info("Cancelling AI response, stopping stream")

        st.markdown("")  # added to help with autoscroller

        # If neither button was clicked, we return to wait for the user's action.
        if not (retry_clicked or cancel_clicked):
            return

    def _generate_title(self) -> None:
        """Generate title after first AI response if needed"""
        title = self.ctx.llm.generate_session_title()
        session = self.ctx.storage.get_session(st.session_state.current_session_id)
        session.title = title
        self.ctx.storage.update_session(session)
        st.session_state.needs_title_generation = False
