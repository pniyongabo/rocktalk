import streamlit as st
from config.settings import SettingsManager
from utils.update import check_for_updates


@st.dialog("Settings")
def general_options():
    """Dialog for global application settings and data management"""
    storage = st.session_state.storage
    settings = SettingsManager(storage=storage)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Model Settings", "Import/Export", "Credentials", "Check for Updates"]
    )

    with tab1:
        settings.render_settings_dialog()
    with tab2:
        settings._render_import_export()
    with tab3:
        settings.render_refresh_credentials()
    with tab4:
        check_for_updates()
