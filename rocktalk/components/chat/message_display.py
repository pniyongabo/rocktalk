# rocktalk/components/chat/message_display.py
import streamlit as st
from app_context import AppContext
from components.base import Component
from models.interfaces import ChatMessage
from utils.js import adjust_chat_message_style, scroll_to_bottom


class MessageDisplay(Component):
    """Component responsible for displaying chat messages"""

    def __init__(self, ctx: AppContext):
        """
        Initialize the message display component

        Args:
            ctx: Application context
        """
        super().__init__(ctx)

    def render(self) -> None:
        """Render chat messages to the UI"""
        if "theme" in st.session_state and st.session_state.theme:
            adjust_chat_message_style()

        # Display system message if available
        system_message = self.ctx.llm.get_state_system_message()
        if system_message:
            system_message.display()

        # Display all messages in the session
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
