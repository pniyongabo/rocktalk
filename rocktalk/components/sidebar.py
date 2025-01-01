from functools import partial

import streamlit as st
from config.settings import SettingsManager
from models.storage_interface import StorageInterface
from utils.date_utils import create_date_masks
from utils.streamlit_utils import OnPillsChange, PillOptions, on_pills_change
from functools import partial
from .chat import ChatInterface
from .dialogs.general_options import general_options
from .dialogs.session_settings import session_settings
from .dialogs.search import search_dialog


class Sidebar:
    """Manages the sidebar UI and session list"""

    def __init__(self, chat_interface: ChatInterface):
        self.storage: StorageInterface = st.session_state.storage
        self.chat_interface = chat_interface

    def render(self):
        """Render the complete sidebar"""
        with st.sidebar:
            st.title("Chat Sessions")
            self.render_header()
            st.divider()
            self.render_session_list()

    def render_header(self):
        """Render the header section with New Chat and Settings buttons"""
        header_key = "chat_sessions"
        with st.container(key=header_key):
            self.apply_header_styles(header_key)
            self.render_header_buttons()

    def render_header_buttons(self):
        """Render New Chat and Settings buttons"""
        options_map: PillOptions = {
            0: {
                "label": "\+ New Chat",  #:material/add:
                "callback": self.create_new_chat,
            },
            1: {
                "label": ":material/search:",
                "callback": partial(
                    search_dialog,
                    storage=self.storage,
                    chat_interface=self.chat_interface,
                ),
            },
            2: {
                "label": ":material/settings:",
                "callback": self.open_global_settings,
            },
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

    def render_session_list(self):
        """Render the list of chat sessions grouped by date"""
        with st.container(key="session_list"):
            self.apply_session_list_styles()

            recent_sessions = self.storage.get_recent_sessions(limit=100)
            if not recent_sessions:
                st.info("No chat sessions yet")
                return

            groups, df_sessions = create_date_masks(recent_sessions=recent_sessions)
            self.render_session_groups(groups, df_sessions)

    def render_session_groups(self, groups, df_sessions):
        """Render session groups with their sessions"""
        for group_name, mask in groups:
            group_sessions = df_sessions[mask]
            if group_sessions.empty:
                continue

            st.write(f"{group_name}")
            for _, session in group_sessions.iterrows():
                self.render_session_item(session)
            st.divider()

    def render_session_item(self, df_session):
        """Render individual session item with actions"""
        options_map: PillOptions = {
            0: {
                "label": f"{df_session['title']}",
                "callback": partial(self.load_session, df_session["session_id"]),
            },
            1: {
                "label": ":material/settings:",
                "callback": partial(self.open_session_settings, df_session),
            },
        }

        session_key = f"session_{df_session['session_id']}"
        st.segmented_control(
            "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
            options=options_map.keys(),
            format_func=lambda option: options_map[option]["label"],
            selection_mode="single",
            key=session_key,
            on_change=on_pills_change,
            # help=f'{df_session["last_active"].strftime("%m/%d/%Y %I:%M %p")}',
            kwargs=dict(
                OnPillsChange(
                    key=session_key,
                    options_map=options_map,
                )
            ),
            label_visibility="hidden",
        )

    def apply_header_styles(self, header_key: str):
        """Apply CSS styles to the header section"""

        st.markdown(
            f"""
            <style>
            .st-key-{header_key} p {{
                font-size: min(15px, 1rem) !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        self.apply_session_list_styles(container_key=header_key, width=151)

    def apply_session_list_styles(self, container_key="session_list", width: int = 200):
        """Apply CSS styles to the session list"""
        st.markdown(
            f"""
            <style>
            .st-key-{container_key} [data-testid="stMarkdownContainer"] :not(hr) {{
                min-width: {width}px !important;
                max-width: {width}px !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    # Action handlers
    def create_new_chat(self):
        """Handle new chat creation"""
        SettingsManager(storage=self.storage).clear_session()
        # st.rerun() # is a no-op within callback

    def load_session(self, session_id: str):
        """Handle session loading"""
        self.chat_interface.load_session(session_id)
        # st.rerun()  # is a no-op within callback

    def open_global_settings(self):
        """Open global settings dialog"""
        SettingsManager(storage=self.storage).clear_cached_settings_vars()
        general_options()

    def open_session_settings(self, df_session):
        """Open session settings dialog"""
        SettingsManager(storage=self.storage).clear_cached_settings_vars()
        session_settings(df_session=df_session)
