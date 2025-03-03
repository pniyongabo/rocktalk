# rocktalk/components/chat/interface.py
import streamlit as st
from app_context import AppContext
from components.base import Component
from models.interfaces import ChatMessage
from models.llm import TurnState
from utils.log import logger

from .message_display import MessageDisplay
from .response_generator import ResponseGenerator
from .user_input import UserInput


class ChatInterface(Component):
    """Main interface for chat functionality, coordinating all chat components"""

    def __init__(self, ctx: AppContext):
        """
        Initialize the chat interface

        Args:
            ctx: Application context
        """
        super().__init__(ctx)

        # Initialize state if needed
        self._init_state()

        # Initialize sub-components
        self.message_display = MessageDisplay(ctx)
        self.user_input = UserInput(ctx)
        # We'll initialize the response generator after user_input is rendered
        self.response_generator = None

    def _init_state(self):
        """Initialize session state variables needed for chat"""
        if "turn_state" not in st.session_state:
            st.session_state.turn_state = TurnState.HUMAN_TURN
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "current_session_id" not in st.session_state:
            st.session_state.current_session_id = None
        if "edit_message_value" not in st.session_state:
            st.session_state.edit_message_value = None
        if "skip_next_scroll" not in st.session_state:
            st.session_state.skip_next_scroll = False
        if "needs_title_generation" not in st.session_state:
            st.session_state.needs_title_generation = False

    def render(self):
        """Render the complete chat interface"""
        # Handle message editing
        self._handle_edit_message()

        # Display messages
        self.message_display.render()

        # Get user input
        self.user_input.render()

        # Initialize response generator with prompt placeholder from user input
        if not self.response_generator:
            self.response_generator = ResponseGenerator(
                ctx=self.ctx, prompt_placeholder=self.user_input.prompt_placeholder
            )

        # Generate response if needed
        self.response_generator.render()

    def _handle_edit_message(self) -> None:
        """Handle editing of previous messages"""
        if st.session_state.edit_message_value:
            original_message: ChatMessage = st.session_state.edit_message_value[0]
            prompt_return = st.session_state.edit_message_value[1]

            # Remove this message and all following messages
            st.session_state.messages = st.session_state.messages[
                : original_message.index
            ]

            if not st.session_state.get("temporary_session", False):
                self.ctx.storage.delete_messages_from_index(
                    session_id=st.session_state.current_session_id,
                    from_index=original_message.index,
                )

            st.session_state.turn_state = TurnState.HUMAN_TURN

            # If prompt_return provided, we use the new value and pass control back to AI
            if prompt_return:
                new_message = ChatMessage.create_from_prompt(
                    prompt_data=prompt_return,
                    session_id=original_message.session_id,
                    index=original_message.index,
                )

                # Add edited message
                st.session_state.messages.append(new_message)
                if not st.session_state.get("temporary_session", False):
                    self.ctx.storage.save_message(message=new_message)

                # Set turn state to AI_TURN to generate new response
                st.session_state.turn_state = TurnState.AI_TURN

            st.session_state.edit_message_value = None

    def load_session(self, session_id: str):
        """
        Load a chat session

        Args:
            session_id: ID of the session to load
        """
        if st.session_state.current_session_id == session_id:
            return

        session = self.ctx.storage.get_session(session_id)
        st.session_state.current_session_id = session_id
        st.session_state.messages = self.ctx.storage.get_messages(session.session_id)
        st.session_state.temporary_session = False

        # Load session settings
        self.ctx.llm.update_config(session.config)
        logger.info(f"Loaded session {session.session_id} with title: {session.title}")
        logger.debug(f"Loaded session config: {session.config}")
