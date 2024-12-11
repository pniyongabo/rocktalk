
import streamlit as st
from config.settings import SettingsManager


@st.dialog("Template Settings")
def template_settings():
    """Dialog for managing chat templates"""
    storage = st.session_state.storage
    settings = SettingsManager(storage=storage)

    tab1, tab2, tab3 = st.tabs(["Browse Templates", "Create New", "Import/Export"])

    with tab1:
        settings.render_template_browser()
    with tab2:
        settings.render_template_creator()
    with tab3:
        settings.render_template_import_export()
