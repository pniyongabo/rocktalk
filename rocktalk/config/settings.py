from enum import StrEnum
from functools import partial
import time
from datetime import datetime
from typing import Any, Callable, List, Optional, Tuple
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
from .button_group import ButtonGroupManager
from .parameter_controls import ParameterControls

# Check for deployment environment
PAUSE_BEFORE_RELOADING = 2  # seconds
CUSTOM_TEMPLATE_NAME = "Custom"


class SettingsActions(StrEnum):
    render_new_template_form = "create_template_action"
    render_edit_template_form = "edit_template_action"
    set_default = "set_default_action"
    delete_template = "delete_template_action"
    regenerate_title = "refresh_title_action"
    duplicate_session = "copy_session_action"
    export_session = "export_session_action"
    delete_session = "delete_session_action"


class SettingsManager:
    vars_to_init = {
        SettingsActions.render_new_template_form: None,
        SettingsActions.render_edit_template_form: None,
        SettingsActions.set_default: None,
        SettingsActions.delete_template: None,
        SettingsActions.regenerate_title: None,
        SettingsActions.duplicate_session: None,
        SettingsActions.export_session: None,
        SettingsActions.delete_session: None,
        "new_title": None,
        "confirm_reset": None,
        "confirm_delete_session": None,
        "confirm_delete_template": None,
        "temp_template_name": None,
        "temp_template_description": None,
    }

    template_actions = ButtonGroupManager(
        "template_actions",
        [
            SettingsActions.render_new_template_form,
            SettingsActions.render_edit_template_form,
            SettingsActions.delete_template,
            SettingsActions.set_default,
        ],
    )

    session_actions = ButtonGroupManager(
        "session_actions",
        [
            SettingsActions.duplicate_session,
            SettingsActions.export_session,
            SettingsActions.set_default,
            SettingsActions.delete_session,
        ],
    )

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

    def rerun_app(self):
        """Rerun the app"""
        self.clear_cached_settings_vars()
        st.rerun()

    def rerun_dialog(self):
        logger.info(f"Rerunning {self}")
        st.rerun(scope="fragment")

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

        if st.button(apply_settings_text, type="primary", use_container_width=True):
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

                    if self.session and self.storage:
                        self.session.title = st.session_state["session_title_input"]
                        self.session.config = st.session_state.temp_llm_config
                        self.session.last_active = datetime.now()
                        self.storage.update_session(self.session)

                st.success(body="Settings applied successfully!")
                time.sleep(PAUSE_BEFORE_RELOADING)
                self.rerun_app()
            except Exception as e:
                st.error(f"Error applying settings: {str(e)}")

    def clear_session(self, config: Optional[LLMConfig] = None):
        st.session_state.current_session_id = None
        st.session_state.messages = []
        self.llm.update_config(config=config)

    def render_settings_dialog(self):
        """Render the settings dialog"""

        self.render_template_management()

        # Save settings
        self.render_apply_settings()

        controls = ParameterControls(
            read_only=False,
            show_help=True,
        )
        controls.render_parameters(st.session_state.temp_llm_config)

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

        # Save settings
        current_template = self._get_matching_template(st.session_state.temp_llm_config)
        # if current_template:
        #     # only allow setting as default if a current template is found/in use i.e. not Custom
        #     set_as_default = st.checkbox(
        #         "Set as default configuration",
        #         help="These settings will be used for new sessions",
        #     )
        # else:
        #     set_as_default = False

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Duplicate Session", use_container_width=True):
                self.session_actions.toggle_action(SettingsActions.duplicate_session)

        with col2:
            if st.button("Export Session", use_container_width=True):
                self.session_actions.toggle_action(SettingsActions.export_session)

        with col3:
            if st.button("Set as Default", disabled=not current_template):
                self.session_actions.toggle_action(SettingsActions.set_default)

        with col4:
            if st.button("Delete Session", use_container_width=True, type="secondary"):
                self.session_actions.toggle_action(SettingsActions.delete_session)

        if self.session_actions.is_active(SettingsActions.duplicate_session):
            self._show_copy_session_form()

        if self.session_actions.is_active(SettingsActions.export_session):
            self._export_session()

        if current_template and self.session_actions.is_active(
            SettingsActions.set_default
        ):
            self._set_default_template(current_template)
            self.session_actions.rerun()

        if self.session_actions.is_active(SettingsActions.delete_session):
            self.render_session_delete_form()
            # self.session_actions.rerun()

        self.render_apply_settings()

    def _show_copy_session_form(self):
        """Show dialog for copying session"""
        assert self.session, "Session not initialized"
        with st.form("copy_session_form"):
            st.subheader("Copy Session")
            new_title = st.text_input(
                "New Session Title", value=f"Copy of {self.session.title}"
            )

            copy_messages = st.checkbox("Copy all messages", value=True)
            copy_settings = st.checkbox("Copy settings", value=True)

            success = False
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button(
                    "Create", type="primary", use_container_width=True
                ):
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
                    success = True

            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    self.session_actions.rerun()

            if success:
                st.success("Session copied successfully!")
                time.sleep(PAUSE_BEFORE_RELOADING)
                self.rerun_app()

    def _reset_settings(self):
        """Reset session settings to default template"""
        if st.button("Reset", use_container_width=True):
            st.session_state.temp_llm_config = st.session_state.original_config

    def _render_debug_tab(self):
        """Render debug information tab"""
        assert self.session, "Session not initialized"

        st.text(f"Session ID: {self.session.session_id}")
        st.text(f"Created: {self.session.created_at}")

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
            self.session.title = st.text_input(
                "Session Title", self.session.title, key="session_title_input"
            )
        with col2:
            st.markdown("####")
            if st.button(":material/refresh:"):
                st.session_state.refresh_title_action = True
                st.session_state.new_title = self.llm.generate_session_title(
                    self.session
                )

        # Show confirmation for new title
        if st.session_state.refresh_title_action:
            self.render_session_title_update_form()

        self.render_template_selector()

        self._show_config_diff()

        # Model settings
        controls = ParameterControls(
            read_only=False, show_help=True, session=self.session
        )
        controls.render_parameters(st.session_state.temp_llm_config)

    def render_session_title_update_form(self):
        if not self.session:
            st.error(
                "Session has not been defined, cannot regenerate title outside of session settings"
            )
            return
        with st.form("confirm_title_change"):
            st.info(f"New suggested title: {st.session_state.new_title}")
            col1, col2 = st.columns(2)
            success = None
            with col1:
                if st.form_submit_button(
                    "Accept", type="primary", use_container_width=True
                ):
                    self.storage.rename_session(
                        self.session.session_id, st.session_state.new_title
                    )
                    st.session_state.refresh_title_action = False
                    del st.session_state["new_title"]
                    success = True

            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.refresh_title_action = False
                    del st.session_state["new_title"]
                    self.rerun_dialog()

            if success:
                st.success("Title updated")
                time.sleep(PAUSE_BEFORE_RELOADING)
                self.rerun_dialog()

    def _export_session(self):
        """Export session data"""
        assert self.session, "Session not initialized"
        messages: List[ChatMessage] = self.storage.get_messages(self.session.session_id)
        export_data = {
            "session": self.session.model_dump(),
            "messages": [msg.model_dump() for msg in messages],
        }
        if st.download_button(
            "Download Session Export",
            data=str(export_data),
            file_name=f"session_{self.session.session_id}.json",
            mime="application/json",
            use_container_width=True,
        ):
            st.success("Session exported successfully")
            time.sleep(PAUSE_BEFORE_RELOADING)
            self.session_actions.rerun()

    def render_session_delete_form(self):
        """Render delete session form"""
        assert self.session, "Session not initialized"

        with st.form("confirm_delete_session"):
            message_container = st.empty()
            with message_container:
                st.warning(
                    f"Are you sure you want to delete the session '{self.session.title}'?"
                )

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button(
                    "Delete", type="primary", use_container_width=True
                ):
                    try:
                        self.storage.delete_session(self.session.session_id)
                        if (
                            self.session.session_id
                            == st.session_state.current_session_id
                        ):
                            st.session_state.current_session_id = None
                            st.session_state.messages = []
                            self.llm.update_config()
                        message_container.success(
                            f"Session '{self.session.title}' deleted"
                        )
                        time.sleep(PAUSE_BEFORE_RELOADING)
                        self.rerun_app()
                    except Exception as e:
                        st.error(
                            f"Failed to delete session '{self.session.title}'\n{e}"
                        )

            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    self.session_actions.rerun()

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

        if current_selection not in template_names:
            current_selection = self.storage.get_default_template().name

        selected_idx = (
            template_names.index(current_selection)
            if current_selection in template_names
            else None
        )

        with st.expander(
            f"Original Template: {st.session_state.original_template}", expanded=False
        ):
            st.json(st.session_state.original_config.model_dump_json())

        selected = st.selectbox(
            "Template to Apply",
            template_names,
            index=selected_idx,
            key=template_selectbox_key,
            on_change=self._on_template_selected,
            kwargs=dict(selector_key=template_selectbox_key, templates=templates),
        )
        if selected is not None and selected != CUSTOM_TEMPLATE_NAME:
            return self.storage.get_chat_template_by_name(selected)
        else:
            return None

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
            st.success(f"'{template.name}' set as default template")
            time.sleep(PAUSE_BEFORE_RELOADING)
        except Exception as e:
            st.error(f"Failed to set default template:\n{str(e)}")
            time.sleep(PAUSE_BEFORE_RELOADING)

    def render_template_management(self):
        """Template management UI"""
        template = self.render_template_selector()

        # Template actions
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Save New Template"):
                self.template_actions.toggle_action(
                    SettingsActions.render_new_template_form
                )

        with col2:
            # Only enable edit button if a template is selected
            if st.button("Edit Template", disabled=not template):
                self.template_actions.toggle_action(
                    SettingsActions.render_edit_template_form
                )

        with col3:
            if st.button("Set as Default", disabled=not template):
                self.template_actions.toggle_action(SettingsActions.set_default)

        with col4:
            if st.button("Delete Template", disabled=not template):
                self.template_actions.toggle_action(SettingsActions.delete_template)

        # Handle active actions
        if self.template_actions.is_active(
            SettingsActions.render_new_template_form
        ) or self.template_actions.is_active(SettingsActions.render_edit_template_form):
            self.render_save_template_form(
                template=(
                    template
                    if self.template_actions.is_active(
                        SettingsActions.render_edit_template_form
                    )
                    else None
                )
            )

        if self.template_actions.is_active(SettingsActions.set_default) and template:
            self._set_default_template(template)
            self.template_actions.rerun()

        if (
            self.template_actions.is_active(SettingsActions.delete_template)
            and template
        ):
            self.render_delete_template_form(template)

    def render_save_template_form(self, template: Optional[ChatTemplate] = None):
        with st.form("template_form"):
            name = st.text_input(
                "Name", help="Template name", value=template.name if template else ""
            )

            description = st.text_area(
                "Description",
                help="Template description",
                value=template.description if template else "",
            )

            success, message = False, None
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button(
                    "Update Template" if template else "Create Template",
                    type="primary",
                    use_container_width=True,
                ):
                    success, message = self.validate_and_save_template(
                        name=name, description=description, template=template
                    )

            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    self.template_actions.rerun()

            if success:
                if message:
                    message()
                    time.sleep(PAUSE_BEFORE_RELOADING)
                self.template_actions.rerun()

    def validate_and_save_template(
        self, name: str, description: str, template: Optional[ChatTemplate]
    ) -> Tuple[bool, Optional[Callable[[], Any]]]:
        """Validate and save new template"""
        if not name or not description:
            return False, partial(
                st.warning, body="Please provide both name and description"
            )

        if template:
            template.name = name
            template.description = description
            template.config = st.session_state.temp_llm_config
            self.storage.update_chat_template(template)
        else:
            new_template = ChatTemplate(
                name=name,
                description=description,
                config=st.session_state.temp_llm_config,
            )
            self.storage.store_chat_template(new_template)
        return True, partial(
            st.success,
            body=f"Template '{name}' {'updated' if template else 'created'} successfully",
        )

    def render_delete_template_form(self, template: ChatTemplate):
        """Render delete template form"""
        with st.form("confirm_delete_template"):
            message_container = st.empty()
            with message_container:
                st.warning(
                    f"Are you sure you want to delete the '{template.name}' template?"
                )

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button(
                    "Delete", type="primary", use_container_width=True
                ):
                    try:
                        self.storage.delete_chat_template(template.template_id)
                        message_container.success(f"'{template.name}' template deleted")
                        time.sleep(PAUSE_BEFORE_RELOADING)
                        self.template_actions.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete '{template.name}' template\n{e}")

            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    self.template_actions.rerun()

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
                    self.rerun_app()
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
                    self.rerun_app()
                else:
                    st.session_state.confirm_reset = True
                    st.warning("Click again to confirm reset")
