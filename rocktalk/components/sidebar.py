from functools import partial

import streamlit as st
from config.settings import SettingsManager
from models.storage_interface import StorageInterface
from utils.date_utils import create_date_masks
from utils.streamlit_utils import OnPillsChange, PillOptions, on_pills_change

from .chat import ChatInterface
from .dialogs.general_options import general_options
from .dialogs.session_settings import session_settings


class Sidebar:
    """Manages the sidebar UI and session list"""

    def __init__(self, chat_interface: ChatInterface):
        self.storage: StorageInterface = st.session_state.storage
        self.chat_interface = chat_interface

    def render(self):
        """Render the complete sidebar"""
        with st.sidebar:
            st.title("Chat Sessions")
            self._render_header()
            st.divider()
            self._render_session_list()

    def _render_header(self):
        """Render the header section with New Chat and Settings buttons"""
        with st.container(key="chat_sessions"):
            self._apply_header_styles()
            self._render_header_buttons()

    def _render_header_buttons(self):
        """Render New Chat and Settings buttons"""
        options_map: PillOptions = {
            0: {
                "label": "\+ New Chat",  #:material/add:
                "callback": self._create_new_chat,
            },
            1: {
                "label": ":material/settings:",
                "callback": self._open_global_settings,
            },
            # 2: {  # Add templates option
            #     "label": ":material/file_document: Templates",
            #     "callback": template_settings,
            # },
        }

        st.segmented_control(
            "Chat Sessions",
            options=options_map.keys(),
            format_func=lambda option: options_map[option]["label"],
            selection_mode="single",
            key="chat_sessions_header_buttons",
            on_change=on_pills_change,
            kwargs=dict(
                OnPillsChange(
                    key="chat_sessions_header_buttons",
                    options_map=options_map,
                )
            ),
            label_visibility="hidden",
        )

    def _render_session_list(self):
        """Render the list of chat sessions grouped by date"""
        with st.container(key="session_list"):
            self._apply_session_list_styles()

            recent_sessions = self.storage.get_recent_sessions(limit=100)
            if not recent_sessions:
                st.info("No chat sessions yet")
                return

            groups, df_sessions = create_date_masks(recent_sessions=recent_sessions)
            self._render_session_groups(groups, df_sessions)

    def _render_session_groups(self, groups, df_sessions):
        """Render session groups with their sessions"""
        for group_name, mask in groups:
            group_sessions = df_sessions[mask]
            if group_sessions.empty:
                continue

            st.write(f"{group_name}")
            for _, session in group_sessions.iterrows():
                self._render_session_item(session)
            st.divider()

    def _render_session_item(self, df_session):
        """Render individual session item with actions"""
        options_map: PillOptions = {
            0: {
                "label": f"{df_session['title']}",
                "callback": partial(self._load_session, df_session["session_id"]),
            },
            1: {
                "label": ":material/settings:",
                "callback": partial(self._open_session_settings, df_session),
            },
        }

        session_key = f"session_{df_session['session_id']}"
        st.segmented_control(
            df_session["title"],
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

    def _apply_header_styles(self):
        """Apply CSS styles to the header section"""
        container_key = "chat_sessions"
        # st.markdown(
        #     f"""
        #     <style>
        #     .st-key-{container_key} p {{
        #         font-size: min(15px, 1rem) !important;
        #     }}
        #     </style>
        #     """,
        #     unsafe_allow_html=True,
        # )
        self._apply_session_list_styles(container_key=container_key)

    def _apply_session_list_styles(self, container_key="session_list"):
        """Apply CSS styles to the session list"""
        st.markdown(
            f"""
            <style>
            .st-key-{container_key} [data-testid="stMarkdownContainer"] :not(hr) {{
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

    # Action handlers
    def _create_new_chat(self):
        """Handle new chat creation"""
        SettingsManager(storage=self.storage).clear_session()
        # st.rerun() # is a no-op within callback

    def _load_session(self, session_id: str):
        """Handle session loading"""
        self.chat_interface.load_session(session_id)
        # st.rerun()  # is a no-op within callback

    def _open_global_settings(self):
        """Open global settings dialog"""
        SettingsManager(storage=self.storage).clear_cached_settings_vars()
        general_options()

    def _open_session_settings(self, df_session):
        """Open session settings dialog"""
        SettingsManager(storage=self.storage).clear_cached_settings_vars()
        session_settings(df_session=df_session)
