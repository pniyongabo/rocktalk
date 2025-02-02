import streamlit as st
from config.settings import SettingsManager


@st.dialog("Template Selector")
def template_selector_dialog():
    """Dialog for quickly selecting a template for new chat"""
    st.subheader("Select Template for New Chat")
    settings = SettingsManager(storage=st.session_state.storage)
    template = settings.render_template_selector(include_original=False)

    with st.form("template_selector", border=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button(
                ":material/add: New Chat",
                type="primary",
                use_container_width=True,
            ):
                if template:
                    settings.clear_session(config=template.config)
                else:
                    settings.clear_session()
                st.rerun()
        with col2:
            if st.form_submit_button(
                ":material/history_toggle_off: Temporary Chat",
                use_container_width=True,
            ):
                if template:
                    settings.clear_session(config=template.config)
                else:
                    settings.clear_session()
                st.session_state.temporary_session = True
                st.rerun()
