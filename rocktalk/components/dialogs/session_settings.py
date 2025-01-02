import pandas as pd
import streamlit as st
from config.settings import SettingsManager
from models.interfaces import ChatSession


@st.dialog("Session Settings")
def session_settings(session: ChatSession):
    # session_id = df_session["session_id"]
    storage = st.session_state.storage
    # session = storage.get_session(session.session_id)

    settings = SettingsManager(session=session, storage=storage)

    tab1, tab2, tab3 = st.tabs(["Settings", "Export", "Debug Info"])

    with tab1:
        settings.render_session_actions()
        settings.render_session_settings()
    with tab2:
        settings._render_import_export()
    with tab3:
        settings._render_debug_tab()
