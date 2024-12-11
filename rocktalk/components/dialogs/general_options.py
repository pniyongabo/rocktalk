
import streamlit as st
from config.settings import SettingsManager


@st.dialog("Settings")
def general_options():
    """Dialog for global application settings and data management"""
    storage = st.session_state.storage
    settings = SettingsManager(storage=storage)

    tab1, tab2, tab3 = st.tabs(["Model Settings", "Templates", "Import/Export"])

    with tab1:
        settings.render_settings_dialog()
    with tab2:
        settings.render_template_management()
    with tab3:
        settings._render_import_export()
