from typing import List
import streamlit as st
from models.storage_interface import SearchOperator, StorageInterface
from models.interfaces import ChatMessage, ChatSession, ChatExport
from components.chat import ChatInterface
from utils.log import logger
from streamlit_tags import st_tags
from config.settings import SettingsManager
from components.dialogs.session_settings import session_settings
from functools import partial


@st.dialog("Search")
def search_dialog(storage: StorageInterface, chat_interface: ChatInterface):
    search_interface = SearchInterface(storage=storage, chat_interface=chat_interface)
    search_interface.render()


class SearchInterface:
    def __init__(self, storage: StorageInterface, chat_interface: ChatInterface):
        self.storage = storage
        self.chat_interface = chat_interface
        self.init_state()

    @staticmethod
    def clear_cached_settings_vars():
        vars_to_clear = [
            "search_filters",
            "search_results",
            "search_terms",
            "search_dialog_reloads",
        ]
        for var in vars_to_clear:
            try:
                del st.session_state[var]
            except:
                pass

    def init_state(self):
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

    def render(self):
        """Render search interface"""
        # Search input
        st.session_state.search_terms = st_tags(
            label="Search Terms",
            text="Enter search terms (press enter after each)",
        )
        logger.info(f"search terms: {st.session_state.search_terms}")

        # Search filters
        with st.expander("Search Filters", expanded=True):
            self.render_filters()

        # st.divider()

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
        logger.info(str(st.session_state.search_results)[:100])

    def render_filters(self):
        """Render search filter options"""
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.search_filters["titles"] = st.checkbox(
                "Search titles", value=st.session_state.search_filters["titles"]
            )
            st.session_state.search_filters["content"] = st.checkbox(
                "Search content", value=st.session_state.search_filters["content"]
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
                    {"session": session, "matching_messages": matching_messages}
                )

            st.session_state.search_results = results

        except Exception as e:
            st.error(f"Search failed: {str(e)}")

    def render_results(self):
        """Render search results"""
        st.markdown("### Search Results")

        for result in st.session_state.search_results:
            session: ChatSession = result["session"]
            messages: List[ChatMessage] = result["matching_messages"]

            with st.expander(f"**{session.title}** ({len(messages)} matches)"):
                # Session metadata
                # st.text(f"Created: {session.created_at}")
                st.text(f"Last active: {session.last_active}")

                # Actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "Open Session",
                        key=f"open_{session.session_id}",
                        use_container_width=True,
                    ):
                        self.chat_interface.load_session(session_id=session.session_id)
                        st.rerun()
                with col2:
                    if st.button(
                        "Sessions",
                        key=f"settings_{session.session_id}",
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

                    # messages = self.storage.get_messages(session.session_id)
                    # export_data = ChatExport(session=session, messages=messages)

                    # st.download_button(
                    #     "Download Session",
                    #     data=export_data.model_dump_json(indent=2),
                    #     file_name=f"session_{session.session_id}.json",
                    #     mime="application/json",
                    #     use_container_width=True,
                    # )

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
