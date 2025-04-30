# rocktalk/components/sidebar.py
from functools import partial
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st
from app_context import AppContext
from config.settings import SettingsManager
from models.interfaces import ChatSession
from utils.date_utils import create_date_masks
from utils.log import logger
from utils.streamlit_utils import OnPillsChange, PillOptions, on_pills_change

from .base import Component
from .chat import ChatInterface
from .dialogs.general_options import general_options
from .dialogs.save_temporary_session import save_temporary_session
from .dialogs.search import SearchInterface, search_dialog
from .dialogs.session_settings import session_settings
from .dialogs.template_selector import template_selector_dialog


class Sidebar(Component):
    """Manages the sidebar UI and session list"""

    def __init__(self, ctx: AppContext, chat_interface: ChatInterface):
        """
        Initialize the sidebar component.

        Args:
            ctx: Application context providing access to services
            chat_interface: Reference to the chat interface for interactions
        """
        super().__init__(ctx)
        self.chat_interface: ChatInterface = chat_interface
        self._settings_manager = SettingsManager(app_context=ctx)

    def render(self) -> None:
        """Render the complete sidebar"""
        with st.sidebar:
            self.render_header()
            st.divider()
            self.render_session_list()

    def _handle_authentication_ui(self) -> None:
        """Handle authentication-related UI elements if auth is enabled"""
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
                    if self.ctx.auth:
                        self.ctx.auth.logout("logout", "unrendered")
                    else:
                        logger.error("Auth service not available but logout requested")

    def render_header(self) -> None:
        """Render the header section with action buttons"""
        self._handle_authentication_ui()
        col1, col2 = st.columns((2, 1))
        with col1:
            st.title("Chat Sessions")
        with col2:
            self.render_current_template()

        header_key = "chat_sessions"
        with st.container(key=header_key):
            self.apply_header_styles(header_key)
            self.render_header_buttons()

    def render_header_buttons(self) -> None:
        """Render action buttons in the header"""
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

    def render_current_template(self) -> None:
        """Render the current template"""
        template = SettingsManager.get_matching_template(
            self.ctx.llm.get_config(), storage=self.ctx.storage
        )
        if template:
            st.markdown(f":small[Current: **{template.name}**]")

    def render_session_list(self) -> None:
        """Render the list of chat sessions"""
        with st.container(key="session_list"):
            self.apply_session_list_styles()

            # Get recent sessions
            recent_sessions = self.ctx.storage.get_recent_sessions(limit=100)
            if not recent_sessions:
                st.info("No chat sessions yet")
                return

            # Render active session if any
            self._render_active_session()

            # Render grouped sessions
            self._render_session_groups(recent_sessions)

    def _render_active_session(self) -> None:
        """Render the currently active session section"""
        if st.session_state.current_session_id or st.session_state.get(
            "temporary_session", False
        ):
            st.markdown("#### Active session")

            if st.session_state.get("temporary_session", False):
                if st.button("Save Temporary Session", use_container_width=True):
                    save_temporary_session(app_context=self.ctx)
            else:
                session = self.ctx.storage.get_session(
                    session_id=st.session_state.current_session_id
                )
                self.render_session_item(
                    session_id=session.session_id,
                    session_title=session.title,
                    active=True,
                )
            st.divider()

    def _render_session_groups(self, recent_sessions: List[ChatSession]) -> None:
        """
        Render sessions grouped by date

        Args:
            recent_sessions: List of recent chat sessions
        """
        groups, df_sessions = create_date_masks(recent_sessions=recent_sessions)

        for group_name, mask in groups:
            group_sessions = df_sessions[mask]
            if group_sessions.empty:
                continue

            # Filter and display sessions
            self._render_session_group(group_name, group_sessions)

    def _render_session_group(
        self, group_name: str, group_sessions: pd.DataFrame
    ) -> None:
        """
        Render a single session group

        Args:
            group_name: Name of the group (e.g., "Today", "Yesterday")
            group_sessions: DataFrame containing sessions in this group
        """
        # Track if we actually displayed any sessions in this group
        sessions_displayed = False
        session_elements = []

        # Collect sessions to display
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

    def render_session_item(
        self, session_id: str, session_title: str, active=False
    ) -> None:
        """
        Render an individual session item with actions

        Args:
            session_id: ID of the session
            session_title: Title of the session
            active: Whether this is the currently active session
        """
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

    def apply_header_styles(self, header_key: str) -> None:
        """
        Apply CSS styles to the header section

        Args:
            header_key: CSS key for the header container
        """
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
            container_key=header_key, width=29
        )  # approx 50 pix per new icon

    def apply_session_list_styles(
        self, container_key="session_list", width: int = 190
    ) -> None:
        """
        Apply CSS styles to the session list

        Args:
            container_key: CSS key for the container
            width: Width in pixels for the container
        """
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
    def create_new_chat(self, temporary: bool = False) -> None:
        """
        Handle new chat creation

        Args:
            temporary: Whether to create a temporary session
        """
        self._settings_manager.clear_session()
        st.session_state.temporary_session = temporary
        logger.info(f"Creating new {'temporary ' if temporary else ''}chat")

    def load_session(self, session_id: str) -> None:
        """
        Handle session loading

        Args:
            session_id: ID of the session to load
        """
        self.chat_interface.load_session(session_id)
        logger.info(f"Loaded session: {session_id}")

    def open_global_settings(self) -> None:
        """Open global settings dialog"""
        self._settings_manager.clear_cached_settings_vars()
        general_options(app_context=self.ctx)
        logger.debug("Opened global settings")

    def open_session_settings(self, session_id: str) -> None:
        """
        Open session settings dialog

        Args:
            session_id: ID of the session to configure
        """
        self._settings_manager.clear_cached_settings_vars()
        session = self.ctx.storage.get_session(session_id=session_id)
        session_settings(app_context=self.ctx, session=session)
        logger.debug(f"Opened settings for session: {session_id}")

    def open_search_dialog(self) -> None:
        """Open search dialog"""
        SearchInterface.clear_cached_settings_vars()
        search_dialog(
            app_context=self.ctx,
            chat_interface=self.chat_interface,
        )
        logger.debug("Opened search dialog")

    def open_template_selector(self) -> None:
        """Open quick template selector dialog"""
        self._settings_manager.clear_cached_settings_vars()
        template_selector_dialog(app_context=self.ctx)
        logger.debug("Opened template selector")
