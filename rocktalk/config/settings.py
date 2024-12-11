import hmac
import os
import time
from datetime import datetime
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
from services.bedrock import BedrockService, FoundationModelSummary
from utils.log import logger

from rocktalk.models.interfaces import ChatMessage

from .parameter_controls import ParameterControls

# Load environment variables
dotenv.load_dotenv()

# Check for deployment environment
DEPLOYED = os.getenv("DEPLOYED", "true").lower() == "true"


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
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


class SettingsManager:

    def __init__(
        self,
        storage: StorageInterface,
        session: Optional[ChatSession] = None,
    ):
        self.session = session
        self.storage = storage

        # Initialize temp config if needed
        self.initialize_temp_config()

    def initialize_temp_config(self):
        """Initialize temporary configuration state"""
        if (
            "temp_llm_config" not in st.session_state
            or st.session_state.temp_llm_config is None
        ):
            if self.session:
                st.session_state.temp_llm_config = self.session.config.model_copy(
                    deep=True
                )
            else:
                st.session_state.temp_llm_config = (
                    st.session_state.llm.get_config().model_copy(deep=True)
                )

    def render_apply_settings(self):
        """
        Apply current temporary settings
        Returns True if successful
        """
        set_as_default = st.checkbox(
            "Set as default configuration",
            help="These settings will be used for new sessions",
        )

        if st.button("Apply Settings", type="primary"):
            try:
                st.session_state.llm.update_config(st.session_state.temp_llm_config)
                if self.session:
                    assert self.storage
                    self.session.config = st.session_state.temp_llm_config
                    self.session.last_active = datetime.now()
                    self.storage.update_session(self.session)

                if set_as_default:
                    LLMConfig.set_default(st.session_state.temp_llm_config)

                SettingsManager.clear_cached_settings_vars()
                st.success(body="Settings applied successfully!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error applying settings: {str(e)}")

    def render_settings_dialog(self):
        """Render the settings dialog"""

        # if st.session_state.current_session_id is None:
        # Render controls
        self.render_model_selector()

        # self.render_parameter_controls()
        controls = ParameterControls(
            read_only=False,
            show_help=True,
        )
        controls.render_parameters(st.session_state.temp_llm_config)

        # Save settings
        self.render_apply_settings()

    @staticmethod
    def clear_cached_settings_vars():
        """Clear cached settings variables"""
        vars_to_clear = [
            "temp_llm_config",
            "temp_llm_preset",
            "llm_preset",
            "providers_reorder",
            "current_provider",
            "model_providers",
            "ordered_providers",
        ]
        for var in vars_to_clear:
            if var in st.session_state:
                del st.session_state[var]

    @staticmethod
    def update_config(config: LLMConfig):
        """Update the current temp LLM configuration"""
        st.session_state.temp_llm_config = config.model_copy(deep=True)

    @staticmethod
    def render_model_summary(current_model: FoundationModelSummary) -> None:
        """Display read-only summary of a config"""
        config: LLMConfig = st.session_state.temp_llm_config
        st.markdown(
            f"""
                    **Model:** {current_model.model_name}\n
                    **Model ID:** {current_model.bedrock_model_id}"""
        )

    @staticmethod
    def get_current_model() -> FoundationModelSummary | None:
        return next(
            (
                m
                for m in st.session_state.available_models
                if m.bedrock_model_id
                == st.session_state.temp_llm_config.bedrock_model_id
            ),
            None,
        )

    @staticmethod
    def render_model_selector() -> None:
        """Render model selection UI"""
        if "available_models" not in st.session_state:
            try:
                st.session_state.available_models = (
                    BedrockService.get_compatible_models()
                )
            except Exception as e:
                st.error(f"Error getting compatible models: {e}")
                st.session_state.available_models = []

        if not st.session_state.available_models:
            return

        current_model: FoundationModelSummary | None = (
            SettingsManager.get_current_model()
        )

        if current_model:
            SettingsManager.render_model_summary(current_model=current_model)

        with st.expander("Change Model", expanded=False):
            if (
                "model_providers" not in st.session_state
                or st.session_state.model_providers is None
            ):
                providers = {}
                for model in st.session_state.available_models:
                    provider = model.provider_name or "Other"
                    if provider not in providers:
                        providers[provider] = []
                    providers[provider].append(model)
                st.session_state.model_providers = providers

            if (
                "current_provider" not in st.session_state
                or st.session_state.current_provider is None
            ):
                st.session_state.current_provider = (
                    current_model.provider_name if current_model else None
                )

            if (
                "ordered_providers" not in st.session_state
                or st.session_state.ordered_providers is None
            ):
                st.session_state.ordered_providers = sorted(
                    st.session_state.model_providers.keys(),
                    key=lambda x: x != st.session_state.current_provider,
                )

            provider_tabs = st.tabs(st.session_state.ordered_providers)
            for tab, provider in zip(provider_tabs, st.session_state.ordered_providers):
                with tab:
                    for model in st.session_state.model_providers[provider]:
                        st.divider()
                        col1, col2 = st.columns([0.7, 0.3])
                        with col1:
                            st.markdown(f"**{model.bedrock_model_id}**")
                            if model.model_name:
                                st.markdown(f"*{model.model_name}*")
                        with col2:
                            st.button(
                                "Select",
                                key=f"select_{model.bedrock_model_id}",
                                type=(
                                    "primary"
                                    if (
                                        model.bedrock_model_id
                                        == st.session_state.temp_llm_config.bedrock_model_id
                                    )
                                    else "secondary"
                                ),
                                on_click=lambda p=provider, m=model.bedrock_model_id: SettingsManager._set_model(
                                    provider=p, model_id=m
                                ),
                            )

    @staticmethod
    def _set_model(provider: str, model_id: str):
        """Internal method to set the model configuration"""
        st.session_state.temp_llm_config.bedrock_model_id = model_id
        if st.session_state.temp_llm_config.parameters.max_output_tokens:
            st.session_state.temp_llm_config.parameters.max_output_tokens = min(
                st.session_state.temp_llm_config.parameters.max_output_tokens,
                BedrockService.get_max_output_tokens(model_id),
            )
        st.session_state.current_provider = provider

    def render_session_actions(self):
        """Render session action buttons and dialogs"""

        st.divider()

        # Save settings
        self.render_apply_settings()

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Copy to New Session", use_container_width=True):
                self._show_copy_session_dialog()

            if st.button("Reset to Original Settings", use_container_width=True):
                self._reset_session_settings()

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
                        else LLMConfig.get_default()
                    ),
                )
                self.storage.store_session(new_session)

                if copy_messages:
                    messages = self.storage.get_messages(self.session.session_id)
                    for msg in messages:
                        msg.session_id = new_session.session_id
                        self.storage.save_message(msg)

                st.success("Session copied successfully!")
                st.rerun()

    def _reset_session_settings(self):
        """Reset session settings to default template"""
        assert self.session, "Session not initialized"
        if st.session_state.get("confirm_reset", False):
            default_config = LLMConfig.get_default()
            # Preserve system prompt
            default_config.system = self.session.config.system
            self.session.config = default_config
            self.storage.update_session(self.session)
            st.success("Settings reset to default")
            st.session_state.confirm_reset = False
            st.rerun()
        else:
            st.session_state.confirm_reset = True
            st.warning("Click again to confirm reset")

    def _render_debug_tab(self):
        """Render debug information tab"""
        assert self.session, "Session not initialized"

        session = self.session
        session_id = self.session.session_id
        messages = self.storage.get_messages(session_id)

        st.markdown("# 🔍 Debug Information")

        st.json(session.model_dump())

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
        self.session.title = st.text_input("Session Title", self.session.title)
        st.text(f"Session ID: {self.session.session_id}")
        st.text(f"Created: {self.session.created_at}")

        # Template selector
        self.render_template_selector(current_config=self.session.config)

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
        if st.session_state.get("confirm_delete", False):
            self.storage.delete_session(self.session.session_id)
            st.success("Session deleted")
            st.rerun()
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
        logger.info(
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

    def _show_template_preview(self, template: ChatTemplate):
        """Show preview dialog when applying template to session"""
        assert self.storage, "Storage not initialized"
        assert self.session, "Session not initialized"

        # st.dialog("Preview Changes")
        st.markdown("### Changes that will be applied:")

        temp_template_config: LLMConfig = template.config.model_copy(deep=True)
        temp_session_config: LLMConfig = self.session.config.model_copy(deep=True)
        temp_template_config.system = None
        temp_session_config.system = None

        # Compare and show differences by iterating through model fields directly
        all_diffs = []
        for field_name in template.config.model_fields.keys():
            param_diffs = self._format_parameter_diff(
                field_name,
                getattr(temp_session_config, field_name),
                getattr(temp_template_config, field_name),
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

    def render_template_selector(
        self,
        current_config: LLMConfig,
    ):
        """Shared template selection UI"""
        templates: List[ChatTemplate] = self.storage.get_chat_templates()

        # Add "Custom" option if config doesn't match any template
        matching_template = self._get_matching_template(current_config)
        template_names = ["Custom"] + [t.name for t in templates]

        selected_idx = (
            0 if not matching_template else template_names.index(matching_template.name)
        )

        selected = st.selectbox("Template", template_names, index=selected_idx)

        if selected != "Custom":
            selected_template = next(t for t in templates if t.name == selected)
            # if st.button("Apply Template"):
            if self.session:
                self._show_template_preview(selected_template)

            self._on_template_selected(selected_template)

    def _render_existing_templates(self):
        """Render the list of existing templates with actions"""
        templates: List[ChatTemplate] = self.storage.get_chat_templates()

        for template in templates:
            with st.expander(template.name):
                st.markdown(f"**Description:** {template.description}")
                # For read-only view
                controls = ParameterControls(
                    read_only=True,
                    show_json=True,
                    truncate_system_prompt=True,
                    show_help=False,
                )
                controls.render_parameters(config=template.config)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Use", key=f"use_{template.template_id}"):
                        SettingsManager.update_config(template.config)
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"delete_{template.template_id}"):
                        self.storage.delete_chat_template(template.template_id)
                        st.rerun()

    def _render_new_template_form(self):
        """Render the form for creating a new template"""
        with st.form("new_template"):
            name = st.text_input("Name", help="Template name")
            description = st.text_area("Description", help="Template description")

            # Initialize temp config if needed
            if (
                "temp_llm_config" not in st.session_state
                or st.session_state.temp_llm_config is None
            ):
                st.session_state.temp_llm_config = LLMConfig.get_default()

            # Model selection
            st.subheader("Model Configuration")
            SettingsManager.render_model_selector()

            # Parameter controls
            st.subheader("Parameters")
            # For editable controls
            controls = ParameterControls(
                read_only=False,
                show_help=True,
            )
            controls.render_parameters(st.session_state.temp_llm_config)

            if st.form_submit_button("Create Template"):
                if not name or not description:
                    st.error("Please provide both name and description")
                    return

                template = ChatTemplate(
                    name=name,
                    description=description,
                    config=st.session_state.temp_llm_config,
                )
                self.storage.store_chat_template(template)

                # Clear temporary config
                SettingsManager.clear_cached_settings_vars()
                st.rerun()

    def _on_template_selected(self, template: ChatTemplate):
        """Handle template selection"""
        # Create new config from template
        new_config = template.config.model_copy(deep=True)

        if self.session:
            # preserve system prompt
            new_config.system = self.session.config.system
            st.session_state.temp_llm_config = new_config.model_copy(deep=True)
        else:
            st.session_state.temp_llm_config = template.config.model_copy(deep=True)

    def _set_default_template(self):
        """Set current configuration as default template"""
        current_config = st.session_state.temp_llm_config
        template = ChatTemplate(
            name="Default",
            description="Default configuration template",
            config=current_config,
        )
        self.storage.store_chat_template(template)
        st.success("Settings saved as default template")

    def _show_save_template_dialog(self):
        """Show dialog to save current settings as a new template"""
        with st.form("save_template_form"):
            name = st.text_input("Template Name")
            description = st.text_area("Description")

            if st.form_submit_button("Save Template"):
                if not name:
                    st.error("Template name is required")
                    return

                template = ChatTemplate(
                    name=name,
                    description=description,
                    config=st.session_state.temp_llm_config,
                )
                self.storage.store_chat_template(template)
                st.success(f"Template '{name}' saved successfully")

    def render_template_management(self):
        """Template management UI"""
        current_config = st.session_state.temp_llm_config
        matching_template = self._get_matching_template(current_config)

        st.markdown(
            f"**Current Settings:** {matching_template.name if matching_template else 'Custom'}"
        )

        self.render_template_selector(current_config)

        # Template actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Set as Default"):
                self._set_default_template()

        with col2:
            if st.button("Save as Template"):
                self._show_save_template_dialog()

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
                    st.rerun()
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
                if self._confirm_reset():
                    self._perform_reset()
                    st.rerun()
                else:
                    st.session_state["confirm_reset"] = True
                    st.warning("Click again to confirm reset")

    def _confirm_reset(self) -> bool:
        """Check if reset has been confirmed"""
        return st.session_state.get("confirm_reset", False)

    def _perform_reset(self):
        """Perform the actual reset operation"""
        st.session_state.storage.delete_all_sessions()
        st.session_state.current_session_id = None
        st.session_state.messages = []
        SettingsManager.clear_cached_settings_vars()

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
                st.rerun()
        with col2:
            if not is_default and st.button(
                "Set as Default", key=f"default_{template.template_id}"
            ):
                self._set_as_default_template(template)
        with col3:
            if not is_default and st.button(
                "Delete", key=f"delete_{template.template_id}"
            ):
                self._delete_template(template.template_id)

    def render_template_creator(self):
        """Render template creation form"""
        with st.form("new_template"):
            name = st.text_input("Name", help="Template name")
            description = st.text_area("Description", help="Template description")

            st.subheader("Model Configuration")
            self.render_model_selector()

            st.subheader("Parameters")
            controls = ParameterControls(read_only=False, show_help=True)
            controls.render_parameters(st.session_state.temp_llm_config)

            if st.form_submit_button("Create Template"):
                if self._validate_and_save_template(name, description):
                    st.success(f"Template '{name}' created successfully")
                    st.rerun()

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

    # Helper methods
    def _validate_and_save_template(self, name: str, description: str) -> bool:
        """Validate and save new template"""
        if not name or not description:
            st.error("Please provide both name and description")
            return False

        existing = self.storage.get_chat_templates()
        if any(t.name == name for t in existing):
            st.error(f"Template with name '{name}' already exists")
            return False

        template = ChatTemplate(
            name=name, description=description, config=st.session_state.temp_llm_config
        )
        self.storage.store_chat_template(template)
        return True

    def _set_as_default_template(self, template: ChatTemplate):
        """Set template as default"""
        # Create copy with name "Default"
        default_template = ChatTemplate(
            name="Default",
            description=f"Default template (copied from {template.name})",
            config=template.config.model_copy(deep=True),
        )
        self.storage.store_chat_template(default_template)
        st.success(f"Set '{template.name}' as default template")

    def _delete_template(self, template_id: str):
        """Delete template with confirmation"""
        if st.session_state.get(f"confirm_delete_template_{template_id}", False):
            self.storage.delete_chat_template(template_id)
            st.success("Template deleted")
            st.rerun()
        else:
            st.session_state[f"confirm_delete_template_{template_id}"] = True
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
