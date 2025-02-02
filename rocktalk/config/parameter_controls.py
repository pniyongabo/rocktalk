# settings_widgets.py
import functools
from typing import Any, Literal, Optional

import streamlit as st
from models.interfaces import ChatSession, LLMConfig
from services.bedrock import BedrockService, FoundationModelSummary
from utils.log import logger
from utils.streamlit_utils import OnPillsChange, PillOptions, on_pills_change


class ParameterControls:
    """Widget for displaying and editing LLM settings"""

    def __init__(
        self,
        read_only: bool = False,
        show_json: bool = False,
        truncate_system_prompt: bool = True,
        max_system_prompt_lines: int = 10,
        show_help: bool = True,
        session: ChatSession | None = None,
    ):
        self.read_only = read_only

        self.show_json = show_json
        self.truncate_system_prompt = truncate_system_prompt
        self.max_system_prompt_lines = max_system_prompt_lines
        self.show_help = show_help
        self.session = session

    @staticmethod
    def control_on_change(
        key: str | None,
        parameter: str,
        action: Literal["set"] | Literal["clear"] = "set",
        value: Optional[Any] = None,
    ):
        """Set a configuration value from a control"""
        if key is None and action == "set":
            logger.warning("No key provided for set_control_config_value")
            return

        if parameter == "temperature":
            if action == "clear":
                logger.debug(
                    f"Updating temperature to 0.5 from {st.session_state.temp_llm_config.parameters.temperature}"
                )
                st.session_state.temp_llm_config.parameters.temperature = 0.5
                return
            else:
                assert key is not None, "Key must be provided for temperature control"
                new_val = float(value or st.session_state[key])
                logger.debug(
                    f"Updating temperature to {new_val} from {st.session_state.temp_llm_config.parameters.temperature}"
                )
                st.session_state.temp_llm_config.parameters.temperature = new_val
        elif parameter == "max_output_tokens":
            if action == "clear":
                logger.debug(
                    f"Updating max_output_tokens to None from {st.session_state.temp_llm_config.parameters.max_output_tokens}"
                )
                st.session_state.temp_llm_config.parameters.max_output_tokens = None
                return
            else:
                assert (
                    key is not None
                ), "Key must be provided for max output tokens control"
                logger.debug(f"Got value for max_output_tokens: {value}")
                new_val = int(value if value is not None else st.session_state[key])
                logger.debug(
                    f"Updating max_output_tokens to {new_val} from {st.session_state.temp_llm_config.parameters.max_output_tokens}"
                )
                st.session_state.temp_llm_config.parameters.max_output_tokens = new_val
        elif parameter == "top_p":
            if action == "clear":
                logger.debug(
                    f"Updating top_p to None from {st.session_state.temp_llm_config.parameters.top_p}"
                )
                st.session_state.temp_llm_config.parameters.top_p = None
                return
            else:
                assert key is not None, "Key must be provided for top_p control"
                new_val = float(value or st.session_state[key])
                logger.debug(
                    f"Updating top_p to {new_val} from {st.session_state.temp_llm_config.parameters.top_p}"
                )
                st.session_state.temp_llm_config.parameters.top_p = new_val
        elif parameter == "top_k":
            if action == "clear":
                logger.debug(
                    f"Updating top_k to None from {st.session_state.temp_llm_config.parameters.top_k}"
                )
                st.session_state.temp_llm_config.parameters.top_k = None
                return
            else:
                assert key is not None, "Key must be provided for top_k control"
                new_val = int(value or st.session_state[key])
                logger.debug(
                    f"Updating top_k to {new_val} from {st.session_state.temp_llm_config.parameters.top_k}"
                )
                st.session_state.temp_llm_config.parameters.top_k = new_val
        elif parameter == "stop_sequences":
            if action == "clear":
                logger.debug(
                    f"Updating stop_sequences to None from {st.session_state.temp_llm_config.stop_sequences}"
                )
                st.session_state.temp_llm_config.stop_sequences = []
                return
            else:
                assert (
                    key is not None
                ), "Key must be provided for stop sequences control"
                new_val = value or st.session_state[key]
                logger.debug(
                    f"Updating stop_sequences to {new_val} from {st.session_state.temp_llm_config.stop_sequences}"
                )
                st.session_state.temp_llm_config.stop_sequences = new_val
        elif parameter == "system_prompt":
            if action == "clear":
                logger.debug(
                    f"Updating system prompt to None from {st.session_state.temp_llm_config.system}"
                )
                st.session_state.temp_llm_config.system = None
                return
            else:
                assert key is not None, "Key must be provided for system prompt control"
                new_val = (value or st.session_state[key]).strip()
                logger.debug(
                    f"Updating system to {new_val} from {st.session_state.temp_llm_config.system}"
                )
                st.session_state.temp_llm_config.system = new_val

    def render_system_prompt(self, config: LLMConfig) -> None:
        """Render system prompt control or view"""
        if self.read_only or self.session:
            read_only = bool(self.session)
            # st.markdown(f"*System prompt is not editable in existing session*\n\n")
            if not config.system:
                st.markdown("**System prompt is not set**")
            else:
                block_quote_system_prompt = config.system.replace("\n", "\n> ")
                line_count = len(block_quote_system_prompt.split("\n"))

                if (
                    line_count > self.max_system_prompt_lines
                    and self.truncate_system_prompt
                ):
                    truncated = "\n".join(
                        block_quote_system_prompt.split("\n")[
                            : self.max_system_prompt_lines
                        ]
                    )
                    st.markdown(
                        f"**System message (first {self.max_system_prompt_lines} lines):**\n> {truncated}"
                    )
                    with st.expander("Show full system message"):
                        st.markdown(f"> {block_quote_system_prompt}")
                else:
                    st.markdown(
                        f"**System message{' *(read-only)*' if read_only else ''}:**\n> {block_quote_system_prompt}"
                    )
        else:
            col1, col2 = st.columns((0.9, 0.1))
            system_prompt_key = "parameter_control_system_prompt"

            with col1:
                st.text_area(
                    "System Prompt",
                    value=config.system or "",
                    help=(
                        "Optional system prompt to provide context or instructions for the model"
                        if self.show_help
                        else None
                    ),
                    on_change=self.control_on_change,
                    kwargs=dict(key=system_prompt_key, parameter="system_prompt"),
                    key=system_prompt_key,
                )

            if config.system:
                with col2:
                    self._render_clear_button(
                        key=system_prompt_key, parameter="system_prompt"
                    )

    def render_temperature(self, config: LLMConfig) -> None:
        """Render temperature control or view"""
        if self.read_only:
            st.markdown(f"**Temperature:** `{config.parameters.temperature}`")
        else:
            key = "parameter_control_temperature"
            st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=config.parameters.temperature,
                step=0.1,
                help=(
                    "Higher values make the output more random, lower values more deterministic"
                    if self.show_help
                    else None
                ),
                on_change=self.control_on_change,
                key=key,
                kwargs=dict(key=key, parameter="temperature"),
            )

    def toggle_control(
        self,
        toggle_key: str,
        parameter: str,
        value: Any | None = None,
        control_key: str | None = None,
    ):
        """Toggle control"""

        self.control_on_change(
            key=control_key,
            parameter=parameter,
            action="clear" if not st.session_state[toggle_key] else "set",
            value=value,
        )

    def render_optional_parameter(
        self,
        param_name: str,
        param_value: Optional[float | int],
        control_type: str,
        **control_args,
    ) -> None:
        """Render an optional parameter with enable/disable checkbox"""
        if self.read_only:
            if param_value is not None:
                st.markdown(f"**{param_name}:** `{param_value}`")
            return

        escaped_param_name = param_name.lower().replace(" ", "_")

        col1, col2 = st.columns((0.4, 0.6))
        with col1:
            use_param_key = f"parameter_toggle_{escaped_param_name}"
            control_key = f"parameter_control_{escaped_param_name}"

            use_param = st.checkbox(
                f"Use {param_name}",
                value=param_value is not None,
                key=use_param_key,
                on_change=self.toggle_control,
                kwargs=dict(
                    toggle_key=use_param_key,
                    parameter=escaped_param_name,
                    value=(control_args["value"] if "value" in control_args else None),
                    control_key=control_key,
                ),
            )

        with col2:
            if use_param:
                if control_type == "slider":
                    st.slider(
                        param_name,
                        key=control_key,
                        on_change=self.control_on_change,
                        kwargs=dict(key=control_key, parameter=escaped_param_name),
                        **control_args,
                    )
                elif control_type == "number_input":
                    st.number_input(
                        param_name,
                        key=control_key,
                        on_change=self.control_on_change,
                        kwargs=dict(key=control_key, parameter=escaped_param_name),
                        **control_args,
                    )
            # else:
            # self.control_on_change(
            #     key=None,
            #     parameter=param_name.lower().replace(" ", "_"),
            #     action="clear",
            # )

    def render_stop_sequences(self, config: LLMConfig) -> None:
        """Render stop sequences control or view"""
        if self.read_only:
            if config.stop_sequences:
                st.markdown("**Stop Sequences:**")
                for seq in config.stop_sequences:
                    st.markdown(f"- `{seq}`")
        else:
            col1, col2 = st.columns((0.4, 0.6))
            parameter = "stop_sequences"
            with col1:
                use_stop_toggle_key = f"parameter_toggle_{parameter}"
                use_stop_sequences = st.checkbox(
                    "Use Stop Sequences",
                    value=bool(config.stop_sequences),
                    key=use_stop_toggle_key,
                    on_change=self.toggle_control,
                    kwargs=dict(toggle_key=use_stop_toggle_key, parameter=parameter),
                )
            with col2:
                if use_stop_sequences:
                    key = f"parameter_control_{parameter}"
                    stop_sequences = st.text_input(
                        "Stop Sequences",
                        value=", ".join(config.stop_sequences),
                        help=(
                            "Comma-separated list of sequences that will cause the model to stop"
                            if self.show_help
                            else None
                        ),
                        key=key,
                        on_change=self.control_on_change,
                        kwargs=dict(key=key, parameter=parameter),
                    )
                    config.stop_sequences = [
                        seq.strip() for seq in stop_sequences.split(",") if seq.strip()
                    ]
                # else:
                #     self.control_on_change(
                #         key=None, parameter="stop_sequences", action="clear"
                #     )

    def _render_clear_button(self, key: str, parameter: str) -> None:
        """Helper method to render a clear button"""
        options_map: PillOptions = {
            0: {
                "label": ":material/delete_forever:",
                "callback": functools.partial(
                    self.control_on_change,
                    key=key,
                    parameter=parameter,
                    action="clear",
                ),
            }
        }
        clear_key = f"clear_parameters_{parameter}"
        st.pills(
            f"Clear {parameter}",
            options=options_map.keys(),
            format_func=lambda option: options_map[option]["label"],
            selection_mode="single",
            key=clear_key,
            on_change=on_pills_change,
            kwargs=dict(OnPillsChange(key=clear_key, options_map=options_map)),
            label_visibility="hidden",
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
    def load_available_models() -> None:
        """Load available models from Bedrock"""
        if "available_models" not in st.session_state:
            try:
                st.session_state.available_models = (
                    BedrockService.get_compatible_models()
                )
            except Exception as e:
                st.error(f"Error getting compatible models: {e}")
                st.session_state.available_models = []

    @staticmethod
    def render_model_expander(
        current_model: FoundationModelSummary | None,
    ) -> None:
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
                                on_click=lambda p=provider, m=model.bedrock_model_id: ParameterControls._set_model(
                                    provider=p, model_id=m
                                ),
                            )

    @staticmethod
    def render_model_selector() -> None:
        """Render model selection UI"""

        ParameterControls.load_available_models()

        if not st.session_state.available_models:
            return

        current_model: FoundationModelSummary | None = (
            ParameterControls.get_current_model()
        )

        if current_model:
            ParameterControls.render_model_summary(current_model=current_model)

        ParameterControls.render_model_expander(current_model=current_model)

    def render_parameters(self, config: LLMConfig) -> None:
        """Main method to render all parameters"""
        # st.subheader("Model Settings")
        logger.debug(f"Rendering parameters for config: {config}")

        self.render_model_selector()

        # System Prompt
        self.render_system_prompt(config)

        # Temperature
        self.render_temperature(config)

        # Max Output Tokens
        max_tokens: int = BedrockService.get_max_output_tokens(
            bedrock_model_id=config.bedrock_model_id
        )
        self.render_optional_parameter(
            param_name="Max Output Tokens",
            param_value=config.parameters.max_output_tokens,
            control_type="number_input",
            min_value=1,
            max_value=max_tokens,
            value=config.parameters.max_output_tokens or max_tokens,
            help=(
                "Maximum number of tokens in the response" if self.show_help else None
            ),
        )

        # Top P
        self.render_optional_parameter(
            param_name="Top P",
            param_value=config.parameters.top_p,
            control_type="slider",
            min_value=0.0,
            max_value=1.0,
            value=config.parameters.top_p or 1.0,
            step=0.01,
            help=(
                "The percentage of most-likely candidates that the model considers"
                if self.show_help
                else None
            ),
        )

        # Top K (Anthropic only)
        if "anthropic" in config.bedrock_model_id.lower():
            self.render_optional_parameter(
                param_name="Top K",
                param_value=config.parameters.top_k,
                control_type="number_input",
                min_value=1,
                max_value=500,
                value=config.parameters.top_k or 250,
                help=(
                    "Number of most-likely candidates (Anthropic models only)"
                    if self.show_help
                    else None
                ),
            )

        # Stop Sequences
        self.render_stop_sequences(config)

        if self.show_json:
            with st.expander("View as JSON"):
                st.json(config.model_dump(), expanded=False)
