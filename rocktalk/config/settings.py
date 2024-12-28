import hmac
import os
from tempfile import template
import time
from datetime import datetime
from tkinter import W
from typing import List, Optional

import dotenv
import streamlit as st
from models.interfaces import (
    ChatExport,
    ChatSession,
    ChatTemplate,
    LLMConfig,
)


from models.storage_interface import StorageInterface
from models.llm import LLMInterface
from utils.log import logger
from services.creds import get_cached_aws_credentials

from models.interfaces import ChatMessage

from .parameter_controls import ParameterControls

# Load environment variables
dotenv.load_dotenv()

# Check for deployment environment
DEPLOYED = os.getenv("DEPLOYED", "true").lower() == "true"

PAUSE_BEFORE_RELOADING = 2  # seconds


def get_password() -> Optional[str]:
    """
    Get password from environment variables or Streamlit secrets
    Returns None if no password is configured, with appropriate warnings
    """
    password = None
    if DEPLOYED:
        password = st.secrets.get("password")
        if not password:
            st.warning("⚠️ No password configured in Streamlit secrets")
    else:
        password = os.getenv("APP_PASSWORD")
        if not password:
            st.warning("⚠️ No APP_PASSWORD set in environment variables")
    return password


def check_password() -> bool:
    """Returns `True` if the user had the correct password."""
    password = get_password()
    if not password:
        st.error("Password not configured")
        st.stop()

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], password):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    # TODO fix this. weird logic?
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


CUSTOM_TEMPLATE_NAME = "Custom"


class SettingsManager:
    vars_to_init = {
        "create_template_action": None,
        "edit_template_action": None,
        "set_default_action": None,
        "delete_template_action": None,
        "refresh_title_action": None,
        "new_title": None,
        "confirm_reset": None,
        "confirm_delete": None,
        "confirm_delete_template": None,
        "temp_template_name": None,
        "temp_template_description": None,
    }

    def __init__(
        self,
        storage: StorageInterface,
        session: Optional[ChatSession] = None,
    ):
        self.session = session
        self.storage = storage
        self.llm: LLMInterface = st.session_state.llm

        # Initialize temp config if needed
        self.initialize_temp_config()

    def clear_cached_settings_vars(self):
        """Clear cached settings variables"""
        vars_to_clear = [
            "temp_llm_config",
            "providers_reorder",
            "current_provider",
            "model_providers",
            "ordered_providers",
            *self.vars_to_init.keys(),
        ]
        for var in vars_to_clear:
            if var in st.session_state:
                del st.session_state[var]

    def rerun(self):
        """Rerun the app"""
        self.clear_cached_settings_vars()
        st.rerun()

    def initialize_temp_config(self):
        """Initialize temporary configuration state"""
        if (
            "temp_llm_config" not in st.session_state
            or st.session_state.temp_llm_config is None
        ):
            if self.session:
                # we're editing settings for a particular session
                st.session_state.temp_llm_config = self.session.config.model_copy(
                    deep=True
                )
            elif st.session_state.current_session_id:
                # we've opened general settings while a session is active/displayed, use default template
                st.session_state.temp_llm_config = (
                    self.storage.get_default_template().config
                )
            else:
                # general settings, no session active (new chat/session)
                st.session_state.temp_llm_config = self.llm.get_config().model_copy(
                    deep=True
                )

            st.session_state.original_config = (
                st.session_state.temp_llm_config.model_copy(deep=True)
            )
            matching_template = self._get_matching_template(
                st.session_state.original_config
            )
            st.session_state.original_template = (
                matching_template.name if matching_template else CUSTOM_TEMPLATE_NAME
            )

        for var, default_value in self.vars_to_init.items():
            if var not in st.session_state:
                st.session_state[var] = default_value

    def render_apply_settings(self, set_as_default: bool = False):
        """
        Apply current temporary settings
        Returns True if successful
        """

        apply_settings_text = "Apply Settings"
        if st.session_state.current_session_id and not self.session:
            apply_settings_text = "Apply Settings to New Session"

        if st.button(apply_settings_text, type="primary"):
            try:
                current_template = self._get_matching_template(
                    st.session_state.temp_llm_config
                )
                if current_template:
                    if set_as_default:
                        self._set_default_template(current_template)

                if st.session_state.current_session_id and not self.session:
                    # we're editing general settings while another session is active, Apply will create a new session
                    self.clear_session(config=st.session_state.temp_llm_config)
                else:
                    self.llm.update_config(st.session_state.temp_llm_config)

                    if self.session:
                        assert self.storage
                        self.session.config = st.session_state.temp_llm_config
                        self.session.last_active = datetime.now()
                        self.storage.update_session(self.session)

                st.success(body="Settings applied successfully!")
                time.sleep(PAUSE_BEFORE_RELOADING)
                self.rerun()
            except Exception as e:
                st.error(f"Error applying settings: {str(e)}")

    def clear_session(self, config: Optional[LLMConfig] = None):
        st.session_state.current_session_id = None
        st.session_state.messages = []
        self.llm.update_config(config=config)

    def render_settings_dialog(self):
        """Render the settings dialog"""

        self.render_template_management()

        controls = ParameterControls(
            read_only=False,
            show_help=True,
        )
        controls.render_parameters(st.session_state.temp_llm_config)

        # Save settings
        self.render_apply_settings()

    def render_refresh_credentials(self):
        if st.button("Refresh AWS Credentials"):
            get_cached_aws_credentials.clear()
            self.llm.update_config(st.session_state.original_config)
            st.success("Credentials refreshed successfully!")

    @staticmethod
    def update_config(config: LLMConfig):
        """Update the current temp LLM configuration"""
        st.session_state.temp_llm_config = config.model_copy(deep=True)

    def render_session_actions(self):
        """Render session action buttons and dialogs"""

        st.divider()

        # Save settings
        current_template = self._get_matching_template(st.session_state.temp_llm_config)
        if current_template:
            # only allow setting as default if a current template is found/in use i.e. not Custom
            set_as_default = st.checkbox(
                "Set as default configuration",
                help="These settings will be used for new sessions",
            )
        else:
            set_as_default = False

        self.render_apply_settings(set_as_default=set_as_default)

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Copy to New Session", use_container_width=True):
                self._show_copy_session_dialog()

        with col2:
            if st.button("Export Session", use_container_width=True):
                self._export_session()

            if st.button("Delete Session", use_container_width=True, type="secondary"):
                self._confirm_delete_session()

    def _show_copy_session_dialog(self):
        """Show dialog for copying session"""
        assert self.session, "Session not initialized"
        with st.form("copy_session_form"):
            st.subheader("Copy Session")
            new_title = st.text_input(
                "New Session Title", value=f"Copy of {self.session.title}"
            )

            copy_messages = st.checkbox("Copy all messages", value=True)
            copy_settings = st.checkbox("Copy settings", value=True)

            if st.form_submit_button("Create"):
                new_session = ChatSession(
                    title=new_title,
                    config=(
                        self.session.config.model_copy(deep=True)
                        if copy_settings
                        else (self.storage.get_default_template().config)
                    ),
                )
                self.storage.store_session(new_session)

                if copy_messages:
                    messages = self.storage.get_messages(self.session.session_id)
                    for msg in messages:
                        msg.session_id = new_session.session_id
                        self.storage.save_message(msg)

                st.success("Session copied successfully!")
                time.sleep(PAUSE_BEFORE_RELOADING)
                self.rerun()

    def _reset_settings(self):
        """Reset session settings to default template"""
        if st.button("Reset", use_container_width=True):
            st.session_state.temp_llm_config = st.session_state.original_config

    def _render_debug_tab(self):
        """Render debug information tab"""
        assert self.session, "Session not initialized"

        session = self.session
        session_id = self.session.session_id
        messages = self.storage.get_messages(session_id)

        st.markdown("# 🔍 Debug Information")

        st.json(session.model_dump(), expanded=0)

        # Recent messages
        st.markdown("#### Recent Messages")
        self._render_recent_messages(messages)

    def _render_recent_messages(self, messages: List[ChatMessage]):
        """Render recent messages with truncated image data"""
        for msg in messages[:4]:  # Show up to 4 recent messages
            msg_dict = msg.model_dump()

            # Truncate image data
            if isinstance(msg_dict.get("content"), list):
                for item in msg_dict["content"]:
                    if isinstance(item, dict) and item.get("type") == "image":
                        if "data" in item.get("source", {}):
                            item["source"]["data"] = (
                                item["source"]["data"][:10] + "...[truncated]"
                            )

            st.json(msg_dict)

    def render_session_settings(self):
        """Session configuration UI"""
        assert self.session, "Session not initialized"
        # Session info
        col1, col2 = st.columns((0.9, 0.1))
        with col1:
            self.session.title = st.text_input("Session Title", self.session.title)

        with col2:
            st.markdown("<BR>", unsafe_allow_html=True)
            if st.button(":material/refresh:"):
                st.session_state.refresh_title_action = True
                st.session_state.new_title = self.llm.generate_session_title(
                    self.session
                )

        # Show confirmation for new title
        if st.session_state.refresh_title_action:
            st.info(f"New suggested title: {st.session_state.new_title}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Accept"):
                    # self.session.title = st.session_state.new_title
                    self.storage.rename_session(
                        self.session.session_id, st.session_state.new_title
                    )
                    st.session_state.refresh_title_action = False
                    del st.session_state.new_title
                    st.success("Title updated")
                    time.sleep(PAUSE_BEFORE_RELOADING)
                    self.rerun()
            with col2:
                if st.button("Cancel"):
                    st.session_state.refresh_title_action = False
                    del st.session_state.new_title
                    self.rerun()

        st.text(f"Session ID: {self.session.session_id}")
        st.text(f"Created: {self.session.created_at}")

        self.render_template_selector()

        self._show_config_diff()

        # Model settings
        controls = ParameterControls(
            read_only=False, show_help=True, session=self.session
        )
        controls.render_parameters(st.session_state.temp_llm_config)

    def _export_session(self):
        """Export session data"""
        assert self.session, "Session not initialized"
        messages: List[ChatMessage] = self.storage.get_messages(self.session.session_id)
        export_data = {
            "session": self.session.model_dump(),
            "messages": [msg.model_dump() for msg in messages],
        }
        st.download_button(
            "Download Session Export",
            data=str(export_data),
            file_name=f"session_{self.session.session_id}.json",
            mime="application/json",
        )

    def _confirm_delete_session(self):
        """Show delete confirmation dialog"""
        assert self.session, "Session not initialized"
        if st.session_state.confirm_delete:
            self.storage.delete_session(self.session.session_id)
            if self.session.session_id == st.session_state.current_session_id:
                st.session_state.current_session_id = None
                st.session_state.messages = []
                self.llm.update_config()
            st.success("Session deleted")
            self.rerun()
        else:
            st.session_state.confirm_delete = True
            st.warning("Click again to confirm deletion")

    def _format_parameter_diff(
        self, param_name: str, old_val, new_val, indent: int = 0
    ) -> List[str]:
        """
        Recursively format parameter differences between configurations.
        Returns a list of markdown formatted diff strings.
        """
        if old_val != new_val and (old_val or new_val):
            logger.debug(
                f"_format_parameter_diff: {param_name} old: {old_val}, new: {new_val}"
            )
        diffs = []
        indent_str = "  " * indent

        # Handle nested models (Pydantic BaseModel)
        if hasattr(old_val, "model_fields") and hasattr(new_val, "model_fields"):
            # Iterate through fields directly from the model
            for nested_param in old_val.model_fields.keys():
                nested_diffs = self._format_parameter_diff(
                    nested_param,
                    getattr(old_val, nested_param),
                    getattr(new_val, nested_param),
                    indent + 1,
                )
                if nested_diffs:
                    # diffs.append(f"{param_name}:")
                    diffs.extend(nested_diffs)
        # Handle basic value differences
        elif old_val != new_val:
            diffs.append(f"{indent_str}- {param_name}: *{old_val}* → **{new_val}**")

        return diffs

    def _show_config_diff(self):
        """Show preview dialog when applying template to session"""
        assert self.storage, "Storage not initialized"
        assert self.session, "Session not initialized"

        st.markdown("### Changes that will be applied:")
        temp_config: LLMConfig = st.session_state.temp_llm_config
        # temp_template_config: LLMConfig = template.config.model_copy(deep=True)
        temp_session_config: LLMConfig = self.session.config.model_copy(deep=True)

        # Compare and show differences by iterating through model fields directly
        all_diffs = []
        for field_name in temp_config.model_fields.keys():
            param_diffs = self._format_parameter_diff(
                field_name,
                getattr(temp_session_config, field_name),
                getattr(temp_config, field_name),
            )
            all_diffs.extend(param_diffs)

        if all_diffs:
            for diff in all_diffs:
                st.markdown(diff)
        else:
            st.markdown("*No changes to apply*")

    def _get_matching_template(self, config: LLMConfig) -> Optional[ChatTemplate]:
        """Find template matching the given config, if any"""
        assert self.storage, "Storage not initialized"
        templates = self.storage.get_chat_templates()
        for template in templates:
            if template.config == config:
                return template
        return None

    def render_template_selector(self) -> Optional[ChatTemplate]:
        """Shared template selection UI"""
        current_config = st.session_state.temp_llm_config
        templates: List[ChatTemplate] = self.storage.get_chat_templates()

        # Get currently selected template name from selectbox key in session state, or None on first render
        template_selectbox_key = "template_selectbox_key"
        current_selection = st.session_state.get(template_selectbox_key, None)

        # Get currently selected template name from session state
        if current_selection is None:
            matching_template = self._get_matching_template(current_config)
            if matching_template:
                current_selection = matching_template.name
            else:
                current_selection = CUSTOM_TEMPLATE_NAME

        template_names = [CUSTOM_TEMPLATE_NAME] + [t.name for t in templates]
        selected_idx = template_names.index(current_selection)

        st.markdown(f"### Original Template: {st.session_state.original_template}")
        with st.expander("Configuration", expanded=False):
            st.json(st.session_state.original_config.model_dump_json())

        selected = st.selectbox(
            "Template to Apply",
            template_names,
            index=selected_idx,
            key=template_selectbox_key,
            on_change=self._on_template_selected,
            kwargs=dict(selector_key=template_selectbox_key, templates=templates),
        )
        if selected != CUSTOM_TEMPLATE_NAME:
            return self.storage.get_chat_template_by_name(selected)
        else:
            return None

    # def _render_existing_templates(self):
    #     """Render the list of existing templates with actions"""
    #     templates: List[ChatTemplate] = self.storage.get_chat_templates()

    #     for template in templates:
    #         with st.expander(template.name):
    #             st.markdown(f"**Description:** {template.description}")
    #             # For read-only view
    #             controls = ParameterControls(
    #                 read_only=True,
    #                 show_json=True,
    #                 truncate_system_prompt=True,
    #                 show_help=False,
    #             )
    #             controls.render_parameters(config=template.config)

    #             col1, col2 = st.columns(2)
    #             with col1:
    #                 if st.button("Use", key=f"use_{template.template_id}"):
    #                     SettingsManager.update_config(template.config)
    #                     self.rerun()
    #             with col2:
    #                 if st.button("Delete", key=f"delete_{template.template_id}"):
    #                     self.storage.delete_chat_template(template.template_id)
    #                     self.rerun()

    def _on_template_selected(self, selector_key: str, templates: List[ChatTemplate]):
        """Handle template selection"""
        # Create new config from template
        template_name: str = st.session_state[selector_key]

        if template_name == CUSTOM_TEMPLATE_NAME:
            if st.session_state.original_template == CUSTOM_TEMPLATE_NAME:
                # reset to original settings
                new_config = st.session_state.original_config.model_copy(deep=True)
            else:
                # switching from a named template to Custom, so just copy current temp settings (i.e. no changes to custom)
                new_config = st.session_state.temp_llm_config.model_copy(deep=True)
        else:
            # we picked a named template, so apply the settings
            template = next(t for t in templates if t.name == template_name)
            new_config = template.config.model_copy(deep=True)

        # preserve system prompt
        if self.session:
            new_config.system = self.session.config.system

        st.session_state.temp_llm_config = new_config

    def _set_default_template(self, template: ChatTemplate):
        """Set an existing template as default"""
        try:
            self.storage.set_default_template(template.template_id)
            st.success(f"Set '{template.name}' as default template")
        except Exception as e:
            st.error(f"Failed to set default template: {str(e)}")

    def render_template_management(self):
        """Template management UI"""
        # print("template management rendered")
        # matching_template = self._get_matching_template(current_config)

        # st.markdown(
        #     f"**Current Settings:** {matching_template.name if matching_template else 'Custom'}"
        # )

        template = self.render_template_selector()

        # Template actions
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Save as Template"):
                # if st.session_state.create_template_action:
                #     # press the button once the template action is shown to cancel the form render
                #     st.session_state.create_template_action = False
                #     st.session_state.edit_template_action = False
                # else:
                #     st.session_state.create_template_action = True
                st.session_state.create_template_action = (
                    not st.session_state.create_template_action
                )
                st.session_state.edit_template_action = False
        with col2:
            # Only enable edit button if a template is selected
            if st.button("Edit Template", disabled=not template):
                # Toggle edit action and clear create action
                st.session_state.edit_template_action = (
                    not st.session_state.edit_template_action
                )
                st.session_state.create_template_action = False

        with col3:
            if st.button("Delete Template", disabled=not template):
                st.session_state.delete_template_action = True

        with col4:
            if st.button("Set as Default", disabled=not template):
                st.session_state.set_default_action = True

        if (
            st.session_state.create_template_action
            or st.session_state.edit_template_action
        ):
            self.render_save_template_form(
                template=template if st.session_state.edit_template_action else None
            )

        if st.session_state.set_default_action and template:
            self._set_default_template(template)
            st.session_state.set_default_action = False

        if st.session_state.delete_template_action and template:
            try:
                self.storage.delete_chat_template(template.template_id)
                st.success(f"Template '{template.name}' deleted")
            except:
                st.error(f"Failed to delete template '{template.name}'")

    def _render_import_export(self):
        """Render import/export functionality"""
        st.markdown("## Import/Export")

        # Import section
        self._render_import_section()

        st.divider()

        # Reset section
        self._render_reset_section()

    def _render_import_section(self):
        """Handle conversation import functionality"""
        with st.form("session_upload", clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "Import Conversation",
                type=["json"],
                key="conversation_import",
                help="Upload a previously exported conversation",
            )

            if st.form_submit_button(":material/upload: Import"):
                if uploaded_file is None:
                    st.error("Please select a file to import")
                    return

                try:
                    self._process_import_file(uploaded_file)
                    st.success("Conversation imported successfully!")
                    self.rerun()
                except Exception as e:
                    st.error(f"Error importing conversation: {str(e)}")
                    raise e

    def _process_import_file(self, uploaded_file):
        """Process the imported conversation file"""
        import_data = ChatExport.model_validate_json(uploaded_file.getvalue())

        # Store the imported session
        st.session_state.storage.store_session(import_data.session)

        # Store all messages
        for msg in import_data.messages:
            st.session_state.storage.save_message(msg)

        # Update current session
        st.session_state.current_session_id = import_data.session.session_id
        uploaded_file.close()

    def render_import_export(self):
        """Render import/export options"""
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Import")
            uploaded_file = st.file_uploader("Import Settings", type=["json"])
            if uploaded_file:
                try:
                    import json

                    settings = json.loads(uploaded_file.getvalue())
                    # Validate and import settings
                    config: LLMConfig = LLMConfig.model_validate(settings)
                    st.session_state.temp_llm_config = config
                    st.success("Settings imported successfully")
                except Exception as e:
                    st.error(f"Error importing settings: {str(e)}")

        with col2:
            st.subheader("Export")
            if st.button("Export Settings"):
                try:
                    import json

                    settings = st.session_state.temp_llm_config.model_dump()
                    st.download_button(
                        "Download Settings",
                        data=json.dumps(settings, indent=2),
                        file_name="settings.json",
                        mime="application/json",
                    )
                except Exception as e:
                    st.error(f"Error exporting settings: {str(e)}")

    def _render_reset_section(self):
        """Handle application reset functionality"""
        with st.form("reset_data", clear_on_submit=False):
            st.warning("⚠️ This will delete ALL sessions and messages!")

            if st.form_submit_button(":material/delete_forever: Reset All Data"):
                if st.session_state.confirm_reset:
                    st.session_state.storage.delete_all_sessions()
                    st.session_state.current_session_id = None
                    st.session_state.messages = []
                    self.rerun()
                else:
                    st.session_state.confirm_reset = True
                    st.warning("Click again to confirm reset")

    def render_template_browser(self):
        """Render template list with actions"""
        templates = self.storage.get_chat_templates()

        # Show default template first
        default_template = next((t for t in templates if t.name == "Default"), None)
        if default_template:
            with st.expander("Default Template", expanded=True):
                self._render_template_details(default_template, is_default=True)

        # Show other templates
        for template in templates:
            if template.name != "Default":
                with st.expander(template.name):
                    self._render_template_details(template)

    def _render_template_details(
        self, template: ChatTemplate, is_default: bool = False
    ):
        """Render individual template with actions"""
        st.markdown(f"**Description:** {template.description}")

        # Parameter display
        controls = ParameterControls(
            read_only=True,
            show_json=True,
            truncate_system_prompt=True,
            show_help=False,
        )
        controls.render_parameters(config=template.config)

        # Template actions
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Use", key=f"use_{template.template_id}"):
                self.update_config(template.config)
                self.rerun()
        with col2:
            if not is_default and st.button(
                "Set as Default", key=f"default_{template.template_id}"
            ):
                self._set_default_template(template)
        with col3:
            if not is_default and st.button(
                "Delete", key=f"delete_{template.template_id}"
            ):
                self._delete_template(template.template_id)

    def render_template_creator(self):
        """Render template creation form"""

        st.subheader("Model Configuration")
        controls = ParameterControls(read_only=False, show_help=True)
        controls.render_parameters(st.session_state.temp_llm_config)

        self.render_save_template_form()

    def render_save_template_form(self, template: Optional[ChatTemplate] = None):
        logger.info(f"Got template: {template}")
        with st.form("template_form"):
            name = st.text_input(
                "Name", help="Template name", value=template.name if template else ""
            )

            description = st.text_area(
                "Description",
                help="Template description",
                value=template.description if template else "",
            )
            # logger.info(f"inputs template name={name} description={description}")

            if st.form_submit_button(
                "Update Template" if template else "Create Template",
            ):
                # if name != st.session_state.temp_template_name:
                #     st.session_state.temp_template_name = name
                # if description != st.session_state.temp_template_description:
                #     st.session_state.temp_template_description = description

                # logger.info(
                #     f"session state template name={st.session_state.temp_template_name} description={st.session_state.temp_template_description}"
                # )
                if self._validate_and_save_template(
                    name=name, description=description, template=template
                ):
                    # st.session_state.create_template_action = None
                    # st.session_state.edit_template_action = None
                    self.rerun()

    def _validate_and_save_template(
        self, name: str, description: str, template: Optional[ChatTemplate]
    ) -> bool:
        """Validate and save new template"""
        # name = st.session_state.temp_template_name
        # description = st.session_state.temp_template_description

        if not name or not description:
            st.error("Please provide both name and description")
            time.sleep(PAUSE_BEFORE_RELOADING)
            return False

        templates = self.storage.get_chat_templates()
        if any(t.name == name for t in templates):
            st.error(f"Template with name '{name}' already exists")
            time.sleep(PAUSE_BEFORE_RELOADING)
            return False

        if template:
            template.name = name
            template.description = description
            self.storage.update_chat_template(template)
        else:
            new_template = ChatTemplate(
                name=name,
                description=description,
                config=st.session_state.temp_llm_config,
            )
            self.storage.store_chat_template(new_template)

        st.success(
            f"Template '{name}' {'updated' if template else 'created'} successfully"
        )
        time.sleep(PAUSE_BEFORE_RELOADING)
        return True

    def render_template_import_export(self):
        """Handle template import/export"""
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Import Template")
            uploaded_file = st.file_uploader("Import Template", type=["json"])
            if uploaded_file:
                self._handle_template_import(uploaded_file)

        with col2:
            st.subheader("Export Templates")
            templates = self.storage.get_chat_templates()
            for template in templates:
                st.download_button(
                    f"Export {template.name}",
                    data=template.model_dump_json(indent=2),
                    file_name=f"template_{template.template_id}.json",
                    mime="application/json",
                    key=f"export_{template.template_id}",
                )

    # def _set_as_default_template(self, template: ChatTemplate):
    #     """Set template as default"""
    #     # Create copy with name "Default"
    #     default_template = ChatTemplate(
    #         name="Default",
    #         description=f"Default template (copied from {template.name})",
    #         config=template.config.model_copy(deep=True),
    #     )
    #     self.storage.store_chat_template(default_template)
    #     st.success(f"Set '{template.name}' as default template")

    def _delete_template(self, template_id: str):
        """Delete template with confirmation"""
        if st.session_state.confirm_delete_template:
            self.storage.delete_chat_template(template_id)
            st.success("Template deleted")
        else:
            st.session_state.confirm_delete_template = True
            st.warning("Click again to confirm deletion")

    def _handle_template_import(self, uploaded_file):
        """Handle template import"""
        try:
            template_data = uploaded_file.getvalue()
            template = ChatTemplate.model_validate_json(template_data)
            self.storage.store_chat_template(template)
            st.success(f"Template '{template.name}' imported successfully")
        except Exception as e:
            st.error(f"Error importing template: {str(e)}")
