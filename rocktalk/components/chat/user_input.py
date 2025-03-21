# rocktalk/components/chat/user_input.py
from datetime import datetime

import streamlit as st
from app_context import AppContext
from components.base import Component
from models.interfaces import ChatMessage, ChatSession
from models.llm import TurnState
from streamlit_chat_prompt import PromptReturn, pin_bottom, prompt
from streamlit_shortcuts import button
from utils.js import focus_prompt, scroll_to_bottom
from utils.log import logger


class UserInput(Component):
    """Component responsible for handling user input"""

    def __init__(self, ctx: AppContext):
        """
        Initialize the user input component

        Args:
            ctx: Application context
        """
        super().__init__(ctx)
        self.prompt_placeholder = None

    def render(self) -> None:
        """Render the user input prompt and handle input"""
        prompt_container_key = "prompt_container"
        pin_bottom(prompt_container_key)
        prompt_container = st.container(key=prompt_container_key)

        with prompt_container:
            self.prompt_placeholder = st.empty()
            with self.prompt_placeholder:
                chat_prompt_return: PromptReturn | None = prompt(
                    name="chat_input",
                    key="main_prompt",
                    placeholder="Hello!",
                    disabled=False,
                    max_image_file_size=5 * 1024 * 1024,
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
            self._process_user_input(chat_prompt_return)

    def _process_user_input(self, chat_prompt_return: PromptReturn) -> None:
        """
        Process user input and prepare for AI response

        Args:
            chat_prompt_return: The prompt return data
        """
        # Create message from input
        human_message: ChatMessage = ChatMessage.create_from_prompt(
            prompt_data=chat_prompt_return,
            session_id=st.session_state.current_session_id,
        )

        # Display the message
        human_message.display()
        st.session_state.scroll_div_index += 1
        scroll_to_bottom()

        # Create new session if needed
        if (
            not st.session_state.get("temporary_session", False)
            and not st.session_state.current_session_id
        ):
            self._create_new_session(human_message)

        # Save message to storage if we have a non-temporary session
        if st.session_state.current_session_id and not st.session_state.get(
            "temporary_session", False
        ):
            self.ctx.storage.save_message(message=human_message)

        # Add message to session state
        st.session_state.messages.append(human_message)

        # Set state for AI to respond
        st.session_state.turn_state = TurnState.AI_TURN

    def _create_new_session(self, human_message: ChatMessage) -> None:
        """
        Create a new chat session

        Args:
            human_message: The first user message for this session
        """
        config = self.ctx.llm.get_config().model_copy(deep=True)
        new_session: ChatSession = ChatSession(
            title=f"New Chat {datetime.now().isoformat()}",  # Temporary title until first AI response
            config=config,
            input_tokens_used=st.session_state.get("temp_session_input_tokens", 0),
            output_tokens_used=st.session_state.get("temp_session_output_tokens", 0),
        )
        st.session_state.current_session_id = new_session.session_id
        st.session_state.needs_title_generation = (
            True  # Flag to generate title after first AI response
        )
        self.ctx.storage.store_session(new_session)
        human_message.session_id = new_session.session_id

    def get_prompt_placeholder(self):
        """Get the prompt placeholder for other components to use"""
        return self.prompt_placeholder
