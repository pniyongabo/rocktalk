
import streamlit as st
from config.settings import SettingsManager
from models.storage_interface import StorageInterface
from utils.date_utils import create_date_masks

from .chat import ChatInterface
from .dialogs import interface_options, session_settings


class Sidebar:
    storage: StorageInterface

    def __init__(self, chat_interface: ChatInterface):
        self.storage: StorageInterface = st.session_state.storage
        self.chat_interface = chat_interface

    def render(self):
        with st.sidebar:
            st.title("Chat Sessions")

            with st.container():
                col1, col2 = st.columns([0.5, 0.5], gap="small")
                with col1:
                    if st.button("New Chat", type="primary"):
                        self.chat_interface.clear_session()  # Use this instead
                        st.rerun()
                with col2:
                    if st.button("Settings"):
                        SettingsManager.clear_cached_settings_vars()
                        interface_options()

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
                                    self.chat_interface.load_session(
                                        df_session["session_id"]
                                    )
                                    st.rerun()

                            with col2:
                                # Menu trigger button
                                if st.button(
                                    "⋮",
                                    key=f"menu_trigger_{df_session['session_id']}",
                                    help="Session options",
                                ):
                                    SettingsManager.clear_cached_settings_vars()
                                    session_settings(df_session)
