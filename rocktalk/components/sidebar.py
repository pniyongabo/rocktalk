from typing import List
import streamlit as st
from datetime import datetime
from models.interfaces import StorageInterface
from utils.date_utils import create_date_masks
from langchain.schema import AIMessage, HumanMessage


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
                            col1, col2 = st.columns([0.9, 0.1])

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
                                    st.session_state.open_menu_id = session[
                                        "session_id"
                                    ]
                                    st.rerun()

                            # Show menu modal if this session's menu is open
                            if st.session_state.open_menu_id == session["session_id"]:
                                with st.sidebar:
                                    # Create a modal-like container
                                    menu_container = st.empty()
                                    with menu_container.container():
                                        st.markdown("### Session Options")

                                        # Rename input
                                        new_name = st.text_input(
                                            "Rename session",
                                            value=session["title"],
                                            key=f"rename_{session['session_id']}",
                                        )

                                        col1, col2 = st.columns(2)
                                        with col1:
                                            if st.button(
                                                "Save",
                                                key=f"save_{session['session_id']}",
                                                type="primary",
                                            ):
                                                if new_name != session["title"]:
                                                    st.session_state.storage.rename_session(
                                                        session_id=session[
                                                            "session_id"
                                                        ],
                                                        new_title=new_name,
                                                    )
                                                st.session_state.open_menu_id = None
                                                st.rerun()

                                        with col2:
                                            if st.button(
                                                "Cancel",
                                                key=f"cancel_{session['session_id']}",
                                            ):
                                                st.session_state.open_menu_id = None
                                                st.rerun()

                                        st.divider()

                                        # Delete option
                                        if st.button(
                                            "🗑️ Delete Session",
                                            key=f"delete_{session['session_id']}",
                                            type="secondary",
                                            use_container_width=True,
                                        ):
                                            if st.session_state.get(
                                                f"confirm_delete_{session['session_id']}",
                                                False,
                                            ):
                                                st.session_state.storage.delete_session(
                                                    session["session_id"]
                                                )
                                                if (
                                                    st.session_state.current_session_id
                                                    == session["session_id"]
                                                ):
                                                    st.session_state.current_session_id = (
                                                        None
                                                    )
                                                    st.session_state.messages = []
                                                st.session_state.open_menu_id = None
                                                st.rerun()
                                            else:
                                                st.session_state[
                                                    f"confirm_delete_{session['session_id']}"
                                                ] = True
                                                st.warning(
                                                    "Click again to confirm deletion"
                                                )

                                        with st.expander("🔍 Debug Information"):
                                            st.markdown("### Session Details")

                                            # Display all session information in a formatted way
                                            st.markdown("#### Basic Info")
                                            st.code(
                                                f"""Session ID: {session['session_id']}
                                        Title: {session['title'][:57] + '...' if len(session['title']) > 57 and not session['title'][57].isspace() else session['title'][:60]}
                                        Created: {session['created_at']}
                                        Last Active: {session['last_active']}
                                        Message Count: {session['message_count']}"""
                                            )

                                            # Display metadata if it exists
                                            if (
                                                "metadata" in session
                                                and session["metadata"]
                                            ):
                                                st.markdown("#### Metadata")
                                                st.json(session["metadata"])

                                            # Display all raw session data
                                            st.markdown("#### Raw Session Data")
                                            st.json(session.to_dict())

                                            # Add message preview
                                            st.markdown("#### Recent Messages")
                                            messages = st.session_state.storage.get_session_messages(
                                                session["session_id"]
                                            )
                                            if messages:
                                                for msg in messages[
                                                    -3:
                                                ]:  # Show last 3 messages
                                                    st.code(
                                                        f"""Role: {msg['role']}
                                        Timestamp: {msg['timestamp']}
                                        Content: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}"""
                                                    )
