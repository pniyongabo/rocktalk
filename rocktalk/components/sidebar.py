from typing import List
import streamlit as st
from datetime import datetime
from models.interfaces import StorageInterface
from utils.date_utils import create_date_masks
from langchain.schema import AIMessage, HumanMessage
from .session_modal import session_settings


class Sidebar:
    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def render(self):
        with st.sidebar:
            st.sidebar.title("Chat Sessions")
            self._render_new_chat_button()
            self._render_session_list()

    def _render_new_chat_button(self):
        if st.sidebar.button("New Chat", type="primary"):
            st.session_state.messages = []
            st.session_state.current_session_id = None
            st.rerun()

    def _render_session_list(self):
        # Get recent sessions
        recent_sessions = st.session_state.storage.get_recent_sessions(limit=100)

        if recent_sessions:
            groups, df_sessions = create_date_masks(recent_sessions=recent_sessions)

            # Display sessions by group
            for group_name, mask in groups:
                group_sessions = df_sessions[mask]

                if not group_sessions.empty:
                    st.subheader(group_name)

                    # Display sessions within each group
                    for _, session in group_sessions.iterrows():
                        # Container for each session row
                        with st.container():
                            col1, col2 = st.columns([0.9, 0.1], gap="small")

                            with col1:
                                # Main session button
                                if st.button(
                                    f"{session['title']}",
                                    key=f"session_{session['session_id']}",
                                    use_container_width=True,
                                ):
                                    st.session_state.current_session_id = session[
                                        "session_id"
                                    ]
                                    messages = (
                                        st.session_state.storage.get_session_messages(
                                            session["session_id"]
                                        )
                                    )
                                    st.session_state.messages = [
                                        (
                                            HumanMessage(
                                                content=msg["content"],
                                                additional_kwargs={"role": "user"},
                                            )
                                            if msg["role"] == "user"
                                            else AIMessage(
                                                content=msg["content"],
                                                additional_kwargs={"role": "assistant"},
                                            )
                                        )
                                        for msg in messages
                                    ]
                                    st.rerun()

                            with col2:
                                # Menu trigger button
                                if st.button(
                                    "⋮",
                                    key=f"menu_trigger_{session['session_id']}",
                                    help="Session options",
                                ):
                                    session_settings(session)
