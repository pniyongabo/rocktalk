from datetime import datetime

import streamlit as st
from devtools import debug
from langchain.schema import AIMessage, HumanMessage
from pydantic import BaseModel

from models.interfaces import ChatExport, ChatMessage, ChatSession, StorageInterface
from utils.date_utils import create_date_masks

from .dialogs import session_settings, session_upload


class Sidebar:
    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def render(self):
        with st.sidebar:
            st.title("Chat Sessions")
            with st.container():
                col1, col2 = st.columns([0.5, 0.5], gap="small")
                with col1:
                    if st.button("New Chat", type="primary"):
                        st.session_state.messages = []
                        st.session_state.current_session_id = None
                        st.rerun()
                with col2:
                    if st.button("Settings"):
                        session_upload()

            self._render_session_list()

    def _render_session_list(self):
        # Get recent sessions
        recent_sessions = self.storage.get_recent_sessions(limit=100)

        if recent_sessions:
            groups, df_sessions = create_date_masks(recent_sessions=recent_sessions)

            # Display sessions by group
            for group_name, mask in groups:
                group_sessions = df_sessions[mask]

                if not group_sessions.empty:
                    st.subheader(group_name)

                    # Display sessions within each group
                    for _, df_session in group_sessions.iterrows():
                        # Container for each session row
                        with st.container():
                            col1, col2 = st.columns([0.9, 0.1], gap="small")

                            with col1:
                                # Main session button
                                if st.button(
                                    f"{df_session['title']}",
                                    key=f"session_{df_session['session_id']}",
                                    use_container_width=True,
                                ):
                                    st.session_state.current_session_id = df_session[
                                        "session_id"
                                    ]
                                    messages = self.storage.get_session_messages(
                                        df_session["session_id"]
                                    )
                                    st.session_state.messages = [
                                        (
                                            HumanMessage(
                                                content=msg.content,
                                                additional_kwargs={"role": "user"},
                                            )
                                            if msg.role == "user"
                                            else AIMessage(
                                                content=msg.content,
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
                                    key=f"menu_trigger_{df_session['session_id']}",
                                    help="Session options",
                                ):
                                    session_settings(df_session)
