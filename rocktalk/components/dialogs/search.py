import streamlit as st
from models.storage_interface import StorageInterface
from models.interfaces import ChatMessage, ChatSession, ChatExport
from components.chat import ChatInterface
from utils.log import logger


@st.dialog("Search")
def search_dialog(storage: StorageInterface, chat_interface: ChatInterface):
    search_interface = SearchInterface(storage=storage, chat_interface=chat_interface)
    search_interface.render()


class SearchInterface:
    def __init__(self, storage: StorageInterface, chat_interface: ChatInterface):
        self.storage = storage
        self.chat_interface = chat_interface
        self.init_state()

    def init_state(self):
        """Initialize session state for search"""
        if "search_query" not in st.session_state:
            st.session_state.search_query = ""
        if "search_filters" not in st.session_state:
            st.session_state.search_filters = {
                "titles": True,
                "content": True,
                "date_range": None,
            }
        if "search_results" not in st.session_state:
            st.session_state.search_results = []

    def render(self):
        """Render search interface"""
        # Search input
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            query = st.text_input(
                "Search",
                value=st.session_state.search_query,
                placeholder="Enter search terms (use * for wildcards)",
                help="Search session titles and content",
            )
        with col2:
            st.markdown("####")  # Spacing
            if st.button(":material/search:", use_container_width=True):
                st.session_state.search_query = query
                self.perform_search()

        # Search filters
        with st.expander("Search Filters", expanded=True):
            self.render_filters()

        # Results
        if st.session_state.search_results:
            self.render_results()
        elif st.session_state.search_query:
            st.info("No results found")

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

        with col2:
            start_date = st.date_input(
                "Start date", value=None, help="Filter by start date"
            )
            end_date = st.date_input("End date", value=None, help="Filter by end date")

            logger.info(f"start: {start_date}, end: {end_date}")
            if start_date or end_date:
                # if isinstance(dates, tuple) and len(dates) == 2:
                # start_date, end_date = dates
                st.session_state.search_filters["date_range"] = (
                    start_date,
                    end_date,
                )
            else:
                st.session_state.search_filters["date_range"] = None

    def perform_search(self):
        """Execute search with current query and filters"""
        if not st.session_state.search_query:
            st.session_state.search_results = []
            return

        query = st.session_state.search_query
        filters = st.session_state.search_filters

        # Convert wildcards to SQL LIKE syntax
        query = query.replace("*", "%")

        try:
            # Get matching sessions
            matching_sessions = self.storage.search_sessions(
                query=query,
                search_titles=filters["titles"],
                search_content=filters["content"],
                date_range=filters["date_range"],
            )

            # Format results
            results = []
            for session in matching_sessions:
                messages = self.storage.get_messages(session.session_id)
                matching_messages = [
                    msg for msg in messages if query.lower() in str(msg.content).lower()
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
            session = result["session"]
            messages = result["matching_messages"]

            with st.expander(f"**{session.title}** ({len(messages)} matches)"):
                # Session metadata
                # st.text(f"Created: {session.created_at}")
                st.text(f"Last active: {session.last_active}")

                # Matching messages
                if messages:
                    for msg in messages:
                        self.render_message_preview(msg)

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
                    messages = self.storage.get_messages(session.session_id)
                    export_data = ChatExport(session=session, messages=messages)

                    st.download_button(
                        "Download Session",
                        data=export_data.model_dump_json(indent=2),
                        file_name=f"session_{session.session_id}.json",
                        mime="application/json",
                        use_container_width=True,
                    )

    def render_message_preview(self, message: ChatMessage):
        """Render preview of a matching message"""
        # Get snippet around matching text
        content = str(message.content)
        query = st.session_state.search_query.replace("*", "")
        idx = content.lower().find(query.lower())

        if idx >= 0:
            start = max(0, idx - 50)
            end = min(len(content), idx + len(query) + 50)
            snippet = "..." + content[start:end] + "..."

            with st.container():
                st.markdown(f"**{message.role}**: {snippet}")
                st.text(f"Time: {message.created_at}")
