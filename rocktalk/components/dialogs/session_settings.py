import streamlit as st
from app_context import AppContext
from config.settings import SettingsManager
from models.interfaces import ChatSession


@st.dialog("Session Settings")
def session_settings(app_context: AppContext, session: ChatSession):
    settings = SettingsManager(app_context=app_context, session=session)

    tab1, tab2 = st.tabs(["Settings", "Debug Info"])

    with tab1:
        settings.render_session_actions()
        settings.render_session_settings()
    with tab2:
        settings._render_debug_tab()
