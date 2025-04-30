import streamlit as st
from app_context import AppContext
from components import ChatInterface, Sidebar
from streamlit_theme import st_theme
from utils.js import load_js_init
from utils.log import logger

st.set_page_config(
    page_title="RockTalk",
    page_icon="🪨",
    layout="wide",
)


def initialize_app() -> AppContext:
    """Initialize app and return the application context"""
    # Create or retrieve the application context
    if "app_context" not in st.session_state:
        logger.debug("Creating new AppContext")
        st.session_state.app_context = AppContext()
        headers = {s: k for s, k in st.context.headers.items()}
        logger.debug(f"User connection info: {headers}")

    # Update theme (needs to happen on every run)
    st.session_state.theme = st_theme()

    load_js_init()

    return st.session_state.app_context


def render_header():
    """Render app header when no session is active"""
    if not st.session_state.get("current_session_id") and not st.session_state.get(
        "temporary_session"
    ):
        st.subheader(
            "Rocktalk: Powered by AWS Bedrock 🪨 + LangChain 🦜️🔗 + Streamlit 👑"
        )


def render_app(ctx: AppContext):
    chat = ChatInterface(ctx=ctx)
    sidebar = Sidebar(ctx=ctx, chat_interface=chat)

    chat.render()
    sidebar.render()


def main():
    """Main application entry point"""
    logger.debug("RockTalk app rerun")

    ctx = initialize_app()

    if not ctx.handle_authentication():
        return

    if (
        "next_run_callable" in st.session_state
        and st.session_state.next_run_callable is not None
    ):
        st.session_state.next_run_callable()
        del st.session_state["next_run_callable"]

    # Only proceed if either:
    # 1. No authentication is configured
    # 2. Authentication is configured and user is authenticated
    # if not authenticator or st.session_state.get("authentication_status"):
    # Run the app
    render_header()
    render_app(ctx)


if __name__ == "__main__":
    main()
