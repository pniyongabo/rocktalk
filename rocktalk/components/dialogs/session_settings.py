import streamlit as st
from config.settings import SettingsManager
from models.interfaces import ChatSession


@st.dialog("Session Settings")
def session_settings(session: ChatSession):
    storage = st.session_state.storage
    settings = SettingsManager(session=session, storage=storage)

    tab1, tab2 = st.tabs(["Settings", "Debug Info"])

    with tab1:
        settings.render_session_actions()
        settings.render_session_settings()
    with tab2:
        settings._render_debug_tab()
