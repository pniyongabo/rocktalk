from functools import partial

import streamlit as st
from config.settings import SettingsManager
from models.storage_interface import StorageInterface
from utils.date_utils import create_date_masks
from utils.streamlit_utils import OnPillsChange, PillOptions, on_pills_change
from utils.update import UpdateManager

from .chat import ChatInterface
from .dialogs.general_options import general_options
from .dialogs.save_temporary_session import save_temporary_session
from .dialogs.search import SearchInterface, search_dialog
from .dialogs.session_settings import session_settings
from .dialogs.template_selector import template_selector_dialog


class Sidebar:
    """Manages the sidebar UI and session list"""

    def __init__(self, chat_interface: ChatInterface):
        self.storage: StorageInterface = st.session_state.storage
        self.chat_interface = chat_interface

    def render(self):
        """Render the complete sidebar"""
        with st.sidebar:
            if st.session_state.get("authentication_status"):
                # User is authenticated
                name = st.session_state.get("name")
                username = st.session_state.get("username")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"Welcome *{name}*")
                with col2:
                    if st.button(":material/password:", use_container_width=True):
                        st.write("Change Password")
                        # st.dialog("Change Password", "Please enter your new password")
                        # authenticator.reset_password(username, "main")
                with col3:
                    if st.button(":material/logout:", use_container_width=True):
                        st.session_state.authenticator.logout("logout", "unrendered")

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
                "label": ":material/add: New",
                "callback": self.create_new_chat,
            },
            1: {
                "label": ":material/history_toggle_off:",
                "callback": partial(self.create_new_chat, temporary=True),
            },
            2: {
                "label": ":material/playlist_add:",
                "callback": self.open_template_selector,
            },
            3: {
                "label": ":material/search:",
                "callback": self.open_search_dialog,
            },
            4: {
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
            help="Create a new Chat, create a new chat from a template, search for sessions, or general session settings",
            kwargs=dict(
                OnPillsChange(
                    key="chat_sessions_header_buttons",
                    options_map=options_map,
                )
            ),
            label_visibility="collapsed",
        )

    def render_session_list(self):
        """Render the list of chat sessions grouped by date"""
        with st.container(key="session_list"):
            self.apply_session_list_styles()

            recent_sessions = self.storage.get_recent_sessions(limit=100)
            if not recent_sessions:
                st.info("No chat sessions yet")
                return

            if st.session_state.current_session_id or st.session_state.get(
                "temporary_session", False
            ):
                st.markdown("#### Active session")

                if st.session_state.get("temporary_session", False):
                    if st.button("Save Temporary Session", use_container_width=True):
                        save_temporary_session()
                else:
                    session = self.storage.get_session(
                        session_id=st.session_state.current_session_id
                    )
                    self.render_session_item(
                        session_id=session.session_id,
                        session_title=session.title,
                        active=True,
                    )
                st.divider()

            groups, df_sessions = create_date_masks(recent_sessions=recent_sessions)
            self.render_session_groups(groups, df_sessions)

    def render_session_groups(self, groups, df_sessions):
        """Render session groups with their sessions"""
        for group_name, mask in groups:
            group_sessions = df_sessions[mask]
            if group_sessions.empty:
                continue

            # Track if we actually displayed any sessions in this group
            sessions_displayed = False

            # Buffer the sessions that will be displayed
            session_elements = []
            for _, session in group_sessions.iterrows():
                # Skip if this is the current active session
                if session["session_id"] == st.session_state.current_session_id:
                    continue
                session_elements.append(session)
                sessions_displayed = True

            # Only display group name and sessions if we have sessions to show
            if sessions_displayed:
                st.write(f"{group_name}")
                for session in session_elements:
                    session_id = session["session_id"]
                    session_title = session["title"]
                    self.render_session_item(session_id, session_title)
                st.divider()

    def render_session_item(self, session_id: str, session_title: str, active=False):
        """Render individual session item with actions"""
        options_map: PillOptions = {
            0: {
                "label": session_title,
                "callback": partial(self.load_session, session_id),
            },
            1: {
                "label": ":material/settings:",
                "callback": partial(self.open_session_settings, session_id),
            },
        }

        session_key = f"session_{session_id}{'_active' if active else ''}"
        st.segmented_control(
            session_title,
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
            label_visibility="collapsed",
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
        self.apply_session_list_styles(
            container_key=header_key, width=37
        )  # approx 50 pix per new icon

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
    def create_new_chat(self, temporary: bool = False):
        """Handle new chat creation"""
        SettingsManager(storage=self.storage).clear_session()
        st.session_state.temporary_session = temporary

        # st.rerun() # is a no-op within callback

    def load_session(self, session_id: str):
        """Handle session loading"""
        self.chat_interface.load_session(session_id)
        # st.rerun()  # is a no-op within callback

    def open_global_settings(self):
        """Open global settings dialog"""
        SettingsManager(storage=self.storage).clear_cached_settings_vars()
        UpdateManager().reset_state()
        general_options()

    def open_session_settings(self, session_id: str):
        """Open session settings dialog"""
        SettingsManager(storage=self.storage).clear_cached_settings_vars()
        session_settings(session=self.storage.get_session(session_id=session_id))

    def open_search_dialog(self):
        """Open session settings dialog"""
        SearchInterface.clear_cached_settings_vars()
        search_dialog(
            storage=self.storage,
            chat_interface=self.chat_interface,
        )

    def open_template_selector(self):
        """Open quick template selector dialog"""
        SettingsManager(storage=self.storage).clear_cached_settings_vars()
        template_selector_dialog()
