import json
import time
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import List

import streamlit as st
from components.chat import ChatInterface
from components.dialogs.session_settings import session_settings
from config.settings import PAUSE_BEFORE_RELOADING, SettingsManager
from models.interfaces import ChatExport, ChatMessage, ChatSession
from models.storage_interface import SearchOperator, StorageInterface
from streamlit_keywords import keywords_input
from utils.log import logger


@st.dialog("Search")
def search_dialog(storage: StorageInterface, chat_interface: ChatInterface):
    search_interface = SearchInterface(storage=storage, chat_interface=chat_interface)
    search_interface.render()


class SearchInterface:
    def __init__(self, storage: StorageInterface, chat_interface: ChatInterface):
        self.storage = storage
        self.chat_interface = chat_interface
        SearchInterface.init_state()

    @staticmethod
    def clear_cached_settings_vars():
        vars_to_clear = [
            "search_filters",
            "search_results",
            "search_terms",
            "search_dialog_reloads",
            "search_keyword_input_key",
        ]
        for var in vars_to_clear:
            try:
                del st.session_state[var]
            except Exception as e:
                pass
        SearchInterface.init_state()

    @staticmethod
    def init_state():
        """Initialize session state for search"""
        if "search_terms" not in st.session_state:
            st.session_state.search_terms = []
        if "search_filters" not in st.session_state:
            st.session_state.search_filters = {
                "titles": True,
                "content": True,
                "date_range": None,
                "operator": SearchOperator.AND,
            }
        if "search_results" not in st.session_state:
            st.session_state.search_results = []
        if "refresh_app" not in st.session_state:
            st.session_state.refresh_app = False
        if "search_keyword_input_key" not in st.session_state:
            st.session_state.search_keyword_input_key = uuid.uuid4().hex

    def render(self):
        """Render search interface"""

        if st.session_state.refresh_app:
            with st.container(border=True):
                st.warning(
                    "A page refresh is required to see changes applied in the sidebar session history, \nWhen you're done with your search/edits, you can reload by clicking the button below."
                )
                if st.button(":material/refresh: Reload", use_container_width=True):
                    st.session_state.refresh_app = False
                    st.rerun(scope="app")

        # Search input
        st.session_state.search_terms = keywords_input(
            label="Search Terms",
            text="Enter search terms (press enter after each)",
            key=st.session_state.search_keyword_input_key,
        )
        logger.debug(f"search terms: {st.session_state.search_terms}")

        # Search filters
        with st.expander("Search Filters", expanded=True):
            self.render_filters()

        if st.session_state.search_terms:
            self.perform_search()
        else:
            st.session_state.search_results = []
            st.warning("Please enter at least one search term")

        # Results
        if st.session_state.search_terms and st.session_state.search_results:
            self.render_results()
        elif st.session_state.search_terms:
            st.info("No results found")

    def render_filters(self):
        """Render search filter options"""
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.search_filters["titles"] = st.checkbox(
                "Search titles",
                value=st.session_state.search_filters["titles"],
            )
            st.session_state.search_filters["content"] = st.checkbox(
                "Search content",
                value=st.session_state.search_filters["content"],
            )

            # Add operator selection
            st.session_state.search_filters["operator"] = (
                SearchOperator.AND
                if st.radio(
                    "Search Logic",
                    options=["Match ALL terms", "Match ANY term"],
                    index=(
                        0
                        if st.session_state.search_filters["operator"]
                        == SearchOperator.AND
                        else 1
                    ),
                    horizontal=True,
                    help="Choose how to combine search terms",
                )
                == "Match ALL terms"
                else SearchOperator.OR
            )

        with col2:
            start_date = st.date_input(
                "Start date", value=None, help="Filter by start date"
            )
            end_date = st.date_input("End date", value=None, help="Filter by end date")

            if start_date or end_date:
                st.session_state.search_filters["date_range"] = (
                    start_date,
                    end_date,
                )
            else:
                st.session_state.search_filters["date_range"] = None

    def perform_search(self):
        """Execute search with current query and filters"""
        if not st.session_state.search_terms:
            st.session_state.search_results = []
            return

        terms = st.session_state.search_terms
        filters = st.session_state.search_filters

        # Convert wildcards to SQL LIKE syntax
        terms = [term.replace("*", "%") for term in terms]

        try:
            # Get matching sessions
            matching_sessions = self.storage.search_sessions(
                query=terms,
                operator=filters["operator"],
                search_titles=filters["titles"],
                search_content=filters["content"],
                date_range=filters["date_range"],
            )

            # Format results
            results = []
            for session in matching_sessions:
                messages = self.storage.get_messages(session.session_id)
                matching_messages = [
                    msg
                    for msg in messages
                    if any(term.lower() in str(msg.content).lower() for term in terms)
                ]

                results.append(
                    {
                        "session": session,
                        "matching_messages": matching_messages,
                    }
                )

            st.session_state.search_results = results

        except Exception as e:
            st.error(f"Search failed: {str(e)}")

    def show_delete_form(self):
        with st.form("confirm_delete_sessions"):
            message_container = st.empty()
            with message_container:
                st.warning(
                    f"Are you sure you want to delete {len(st.session_state.selected_sessions)} "
                    f"selected session{'s' if len(st.session_state.selected_sessions) > 1 else ''}?"
                )

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button(
                    ":material/delete: Delete",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        for session_id in st.session_state.selected_sessions:
                            self.storage.delete_session(session_id)
                            if st.session_state.current_session_id == session_id:
                                SettingsManager(storage=self.storage).clear_session()

                        message_container.success(
                            f"Deleted {len(st.session_state.selected_sessions)} "
                            f"session{'s' if len(st.session_state.selected_sessions) > 1 else ''}"
                        )
                        st.session_state.selected_sessions = set()
                        st.session_state.show_delete_form = False
                        st.session_state.refresh_app = True
                        time.sleep(PAUSE_BEFORE_RELOADING)
                        st.rerun(scope="fragment")
                    except Exception as e:
                        st.error(f"Failed to delete sessions: {str(e)}")

            with col2:
                if st.form_submit_button(
                    ":material/cancel: Cancel", use_container_width=True
                ):
                    st.session_state.show_delete_form = False
                    st.rerun(scope="fragment")

    def toggle_session_selected(self, session_id: str, checkbox_key: str):
        if st.session_state[checkbox_key]:
            st.session_state.selected_sessions.add(session_id)
        elif session_id in st.session_state.selected_sessions:
            st.session_state.selected_sessions.remove(session_id)

    # Helper function to check if all sessions are selected
    def are_all_selected(self):
        return len(st.session_state.selected_sessions) == len(
            st.session_state.search_results
        )

    # Function to handle select all toggle
    def handle_select_all_change(self):
        if st.session_state.select_all_checkbox:
            # Select all
            st.session_state.selected_sessions.update(
                result["session"].session_id
                for result in st.session_state.search_results
            )
        else:
            # Deselect all
            st.session_state.selected_sessions.clear()
        # st.rerun(scope="fragment")

    def export_sessions(self):
        # Show processing message
        with st.spinner("Preparing export data..."):
            export_data = []
            for session_id in st.session_state.selected_sessions:
                session = self.storage.get_session(session_id)
                messages = self.storage.get_messages(session_id)
                export_data.append(
                    ChatExport(session=session, messages=messages).model_dump_json()
                )
        st.download_button(
            ":material/download: Download Exported Sessions",
            data=json.dumps(export_data, indent=2),
            file_name=f"chat_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
            on_click=lambda: setattr(st.session_state, "export_data", None),
        )

    def toggle_sessions_hidden_state(self):
        if st.session_state.selected_sessions:
            # Count current private status
            private_count = 0
            for session_id in st.session_state.selected_sessions:
                session = self.storage.get_session(session_id)
                if session.is_private:
                    private_count += 1

            # Determine new state based on majority
            make_private = private_count < len(st.session_state.selected_sessions) / 2

            for session_id in st.session_state.selected_sessions:
                session = self.storage.get_session(session_id)
                session.is_private = make_private
                self.storage.update_session(session)
                st.session_state.refresh_app = True
            return f"Made {len(st.session_state.selected_sessions)} sessions {'hidden' if make_private else 'visible'}"

    def render_results_actions(self):
        col1, col2, col3 = st.columns(3)
        success = ""
        with col1:
            if st.button(
                "Toggle Hidden",
                use_container_width=True,
                disabled=not st.session_state.selected_sessions,
                help=(
                    "For all selected sessions, will toggle 'is_private' on the session, either setting to False or True depending on initial state. If `is_private==True`, will prevent session from showing in the session history. Session will still be searchable."
                    if st.session_state.selected_sessions
                    else ""
                ),
            ):
                success = self.toggle_sessions_hidden_state()
        with col2:
            if st.button(
                "Export Selected",
                use_container_width=True,
                disabled=not st.session_state.selected_sessions,
                help=(
                    "For all selected sessions, will export the session and all associated messages to a JSON file. You will be prompted to download the file."
                    if st.session_state.selected_sessions
                    else ""
                ),
            ):
                if not st.session_state.get("export_data"):
                    st.session_state.export_data = True
                else:
                    st.session_state.export_data = not st.session_state.export_data
        with col3:
            if st.button(
                "Delete Selected",
                type="secondary",
                use_container_width=True,
                disabled=not st.session_state.selected_sessions,
                help=(
                    "For all selected sessions, will delete the session and all associated messages. You will be prompted for confirmation."
                    if st.session_state.selected_sessions
                    else ""
                ),
            ):
                st.session_state.show_delete_form = True

        # Show download button if export data is ready
        if st.session_state.get("export_data"):
            self.export_sessions()

        if success:
            st.success(success)
            time.sleep(1)
            st.rerun(scope="fragment")

        # Show delete confirmation form if active
        if st.session_state.get("show_delete_form", False):
            self.show_delete_form()

    def render_results(self):
        """Render search results"""
        if "selected_sessions" not in st.session_state:
            st.session_state.selected_sessions = set()

        self.render_results_actions()

        # show number of results, number selected, etc.
        st.markdown(
            f"**{len(st.session_state.search_results)}** results found"
            + (
                f", **{len(st.session_state.selected_sessions)}** selected"
                if st.session_state.selected_sessions
                else ""
            )
        )

        st.checkbox(
            "Clear Selections" if self.are_all_selected() else "Select All",
            # ":material/select_all:",
            key="select_all_checkbox",
            value=self.are_all_selected(),
            on_change=self.handle_select_all_change,
        )

        for result in st.session_state.search_results:
            self.render_result(result)

    def render_result(self, result):
        session: ChatSession = result["session"]
        messages: List[ChatMessage] = result["matching_messages"]

        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            checkbox_key = f"select_{session.session_id}"
            st.checkbox(
                f"Checkbox for {session.session_id}",
                key=checkbox_key,
                value=session.session_id in st.session_state.selected_sessions,
                on_change=self.toggle_session_selected,
                kwargs={
                    "session_id": session.session_id,
                    "checkbox_key": checkbox_key,
                },
                label_visibility="collapsed",
            )

        with col2:
            with st.expander(
                ("🔒 " if session.is_private else "")
                + f"**{session.title}** ({len(messages)} matches)"
            ):
                # Session metadata
                # st.text(f"Created: {session.created_at}")
                st.text(f"Last active: {session.last_active}")

                st.text(
                    f"Session history visibility: {'Private 🔒' if session.is_private else 'Visible'}"
                )

                # Actions
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(
                        ":material/open_in_full: Load",
                        key=f"open_{session.session_id}",
                        help="Load session into chat interface",
                        use_container_width=True,
                    ):
                        self.chat_interface.load_session(session_id=session.session_id)
                        st.rerun()

                with col2:
                    if st.button(
                        ":material/settings: Settings",
                        key=f"settings_{session.session_id}",
                        help="Open session settings dialog",
                        use_container_width=True,
                    ):
                        SettingsManager(
                            storage=self.storage
                        ).clear_cached_settings_vars()
                        # TODO can't open dialog from another dialog!
                        st.session_state.next_run_callable = partial(
                            session_settings, session=session
                        )
                        st.rerun()

                with col3:
                    if st.button(
                        ":material/download: Export",
                        key=f"export_{session.session_id}",
                        help="Export session to JSON file",
                        use_container_width=True,
                    ):
                        if not st.session_state.get("download_session"):
                            st.session_state.download_session = True
                        else:
                            st.session_state.download_session = (
                                not st.session_state.download_session
                            )

                if st.session_state.get("download_session"):
                    # messages = self.storage.get_messages(session.session_id)
                    export_data = ChatExport(session=session, messages=messages)

                    st.download_button(
                        ":material/download: Download Session",
                        data=export_data.model_dump_json(indent=2),
                        file_name=f"session_{session.session_id}.json",
                        mime="application/json",
                        on_click=lambda: setattr(
                            st.session_state, "download_session", False
                        ),
                        use_container_width=True,
                    )

                # Matching messages
                if messages:
                    for msg in messages:
                        self.render_message_preview(msg)

    def render_message_preview(self, message: ChatMessage):
        """Render preview of a matching message"""
        content = str(message.content)
        terms = st.session_state.search_terms

        # Find first matching term and its position
        matches = []
        for term in terms:
            idx = content.lower().find(term.lower())
            if idx >= 0:
                matches.append((idx, term))

        if matches:
            # Use the first match for the preview
            idx, matching_term = min(matches, key=lambda x: x[0])
            start = max(0, idx - 50)
            end = min(len(content), idx + len(matching_term) + 50)
            snippet = "..." + content[start:end] + "..."

            with st.container():
                st.markdown(f"**{message.role}**: {snippet}")
                st.text(f"Time: {message.created_at}")
