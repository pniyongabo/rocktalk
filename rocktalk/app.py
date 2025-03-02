from pathlib import Path

import dotenv
import streamlit as st
import streamlit.components.v1 as stcomponents
import streamlit_authenticator as stauth
import yaml
from app_context import AppContext
from components.chat import ChatInterface
from components.sidebar import Sidebar
from models.llm import BedrockLLM
from models.storage.sqlite import SQLiteChatStorage
from streamlit_float import float_init
from streamlit_theme import st_theme
from utils.js import get_user_timezone, load_js_init
from utils.log import ROCKTALK_DIR, logger
from yaml.loader import SafeLoader

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

    # Update theme (needs to happen on every run)
    st.session_state.theme = st_theme()

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
    # Only proceed if either:
    # 1. No authentication is configured
    # 2. Authentication is configured and user is authenticated
    # if not authenticator or st.session_state.get("authentication_status"):
    # Run the app
    render_header()
    if "next_run_callable" in st.session_state:
        st.session_state.next_run_callable()
        del st.session_state["next_run_callable"]
    render_app(ctx)


# Float feature initialization
float_init()

load_js_init()

if __name__ == "__main__":
    main()
