from functools import partial

import streamlit as st
from config.settings import SettingsManager
from models.storage_interface import StorageInterface
from utils.date_utils import create_date_masks
from utils.streamlit_utils import OnPillsChange, PillOptions, on_pills_change

from .chat import ChatInterface
from .dialogs import interface_options, session_settings


class Sidebar:
    storage: StorageInterface

    def __init__(self, chat_interface: ChatInterface):
        self.storage: StorageInterface = st.session_state.storage
        self.chat_interface = chat_interface

    def _load_session(self, session_id: str):
        self.chat_interface.load_session(session_id)

    def _open_global_session_settings(self):
        SettingsManager.clear_cached_settings_vars()
        interface_options()

    def _open_session_settings(self, df_session):
        SettingsManager.clear_cached_settings_vars()
        session_settings(df_session)

    def _create_new_chat(self):
        self.chat_interface.clear_session()

    def render(self):
        with st.sidebar:
            st.title("Chat Sessions")
            chat_session_key = "chat_sessions"
            with st.container(key=chat_session_key):
                st.markdown(
                    """
                        <style>
                        .st-key-chat_sessions p {
                            font-size: min(15px, 1rem) !important;
                        }
                        </style>
                    """,
                    unsafe_allow_html=True,
                )
                chat_sessions_header_buttons_key = "chat_sessions_header_buttons"

                options_map: PillOptions = {
                    0: {
                        "label": ":material/add: New Chat",
                        "callback": self._create_new_chat,
                    },
                    1: {
                        "label": ":material/settings: Settings",
                        "callback": self._open_global_session_settings,
                    },
                }
                st.pills(
                    "Chat Sessions",
                    options=options_map.keys(),
                    format_func=lambda option: options_map[option]["label"],
                    selection_mode="single",
                    key=chat_sessions_header_buttons_key,
                    on_change=on_pills_change,
                    kwargs=dict(
                        OnPillsChange(
                            key=chat_sessions_header_buttons_key,
                            options_map=options_map,
                        )
                    ),
                    label_visibility="hidden",
                )

                st.divider()
                self._render_session_list()

    def _render_session_list(self):
        session_list_key = "session_list"
        st.markdown(
            f"""<style>
                .st-key-{session_list_key} [data-testid="stMarkdownContainer"] :not(hr) {{
                    min-width: 200px !important;
                    max-width: 200px !important;
                    overflow: hidden !important;
                    text-overflow: ellipsis !important;
                    white-space: nowrap !important;
                }}
                </style>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key=session_list_key):
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
                            options_map: PillOptions = {
                                0: {
                                    "label": f"{df_session['title']}",
                                    "callback": partial(
                                        self._load_session,
                                        df_session["session_id"],
                                    ),
                                },
                                1: {
                                    "label": ":material/more_vert:",
                                    "callback": partial(
                                        self._open_session_settings, df_session
                                    ),
                                },
                            }
                            session_key = f"session_{df_session['session_id']}"
                            st.segmented_control(
                                f"{df_session['title']}",
                                options=options_map.keys(),
                                format_func=lambda option: options_map[option]["label"],
                                selection_mode="single",
                                key=session_key,
                                on_change=on_pills_change,
                                kwargs=dict(
                                    OnPillsChange(
                                        key=session_key,
                                        options_map=options_map,
                                    )
                                ),
                                label_visibility="hidden",
                            )

                        st.divider()
