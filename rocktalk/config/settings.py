from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Sequence

import dotenv
import streamlit as st
from langchain_aws import ChatBedrockConverse
from services.bedrock import BedrockService, FoundationModelSummary
from streamlit.commands.page_config import Layout


@dataclass
class LLMConfig:
    model_id: str
    temperature: float
    max_output_tokens: Optional[int]
    region_name: str
    stop_sequences: List[str] = field(default_factory=list)
    top_p: Optional[float] = None
    top_k: Optional[int] = None  # Additional parameter for Anthropic models
    system: Optional[str] = None
    guardrail_config: Optional[Dict[str, Any]] = None
    additional_model_request_fields: Optional[Dict[str, Any]] = None
    additional_model_response_field_paths: Optional[List[str]] = None
    disable_streaming: bool = False
    supports_tool_choice_values: Optional[Sequence[Literal["auto", "any", "tool"]]] = (
        None
    )


class LLMPreset(Enum):
    DETERMINISTIC = "Deterministic"
    CREATIVE = "Creative"
    BALANCED = "Balanced"
    CUSTOM = "Custom"


@dataclass
class AppConfig:
    page_title: str = "RockTalk"
    page_icon: str = "🪨"
    layout: Layout = "wide"
    db_path: str = "chat_database.db"

    @classmethod
    def get_llm_config(cls) -> LLMConfig:
        return LLMConfig(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            temperature=0.5,
            max_output_tokens=None,
            region_name="us-west-2",
        )


class SettingsManager:
    PRESET_CONFIGS: Dict[LLMPreset, Dict[str, float]] = {
        LLMPreset.DETERMINISTIC: {"temperature": 0.0},
        LLMPreset.CREATIVE: {"temperature": 0.9},
        LLMPreset.BALANCED: {"temperature": 0.5},
    }

    @staticmethod
    def initialize_settings():
        if "app_config" not in st.session_state:
            st.session_state.app_config = AppConfig()
        if "llm_config" not in st.session_state:
            st.session_state.llm_config = AppConfig.get_llm_config()
        if "llm_preset" not in st.session_state:
            st.session_state.llm_preset = LLMPreset.BALANCED
        if "available_models" not in st.session_state:
            bedrock = BedrockService()
            st.session_state.available_models = bedrock.get_compatible_models()

    @staticmethod
    def render_settings_widget():
        """Render settings controls in the sidebar or dialog"""
        st.subheader("🛠️ Model Settings")

        # Initialize temp_llm_config if it doesn't exist
        if "temp_llm_config" not in st.session_state:
            st.session_state.temp_llm_config = st.session_state.llm_config

        # Display currently selected model
        current_model = next(
            (
                m
                for m in st.session_state.available_models
                if m.model_id == st.session_state.temp_llm_config.model_id
            ),
            None,
        )
        if current_model:
            st.markdown(f"**Currently Selected Model:** {current_model.model_id}")
            if current_model.model_name:
                st.markdown(f"*{current_model.model_name}*")

        # Model selector in an expander
        with st.expander("Change Model", expanded=False):
            # Group models by provider
            providers = {}
            for model in st.session_state.available_models:
                provider = model.provider_name or "Other"
                if provider not in providers:
                    providers[provider] = []
                providers[provider].append(model)

            # Reorder providers to put the current model's provider first
            current_provider = current_model.provider_name if current_model else None
            ordered_providers = sorted(
                providers.keys(), key=lambda x: x != current_provider
            )

            # Create provider tabs
            provider_tabs = st.tabs(ordered_providers)

            for tab, provider in zip(provider_tabs, ordered_providers):
                with tab:
                    for model in providers[provider]:
                        col1, col2 = st.columns([0.7, 0.3])
                        with col1:
                            st.markdown(f"**{model.model_id}**")
                            if model.model_name:
                                st.markdown(f"*{model.model_name}*")
                        with col2:
                            if st.button(
                                "Select",
                                key=f"select_{model.model_id}",
                                type=(
                                    "primary"
                                    if model.model_id
                                    == st.session_state.temp_llm_config.model_id
                                    else "secondary"
                                ),
                            ):
                                st.session_state.temp_llm_config = LLMConfig(
                                    model_id=model.model_id,
                                    temperature=st.session_state.temp_llm_config.temperature,
                                    max_output_tokens=BedrockService.get_max_output_tokens(
                                        model.model_id
                                    ),
                                    region_name=st.session_state.temp_llm_config.region_name,
                                )
                                # st.rerun()

        st.divider()

        # Preset selector
        preset = st.selectbox(
            "Preset Configuration",
            options=list(LLMPreset),
            format_func=lambda x: x.value,
            key="settings_preset",
            index=list(LLMPreset).index(st.session_state.llm_preset),
        )

        if preset != st.session_state.llm_preset:
            if preset != LLMPreset.CUSTOM:
                st.session_state.temp_llm_config.temperature = (
                    SettingsManager.PRESET_CONFIGS[preset]["temperature"]
                )
            st.session_state.temp_llm_preset = preset

        # Show current settings with option to modify
        with st.expander("Advanced Settings"):
            config = st.session_state.temp_llm_config

            new_temp = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=float(config.temperature),
                step=0.1,
                help="Higher values make the output more random, lower values more deterministic",
            )

            new_max_tokens = st.number_input(
                "Max Output Tokens",
                min_value=1,
                max_value=BedrockService.get_max_output_tokens(config.model_id),
                value=config.max_output_tokens
                or BedrockService.get_max_output_tokens(config.model_id),
                help="Maximum number of tokens in the response",
            )

            new_top_p = st.slider(
                "Top P",
                min_value=0.0,
                max_value=1.0,
                value=config.top_p or 1.0,
                step=0.01,
                help="The percentage of most-likely candidates that the model considers for the next token",
            )

            new_stop_sequences = st.text_input(
                "Stop Sequences",
                value=", ".join(config.stop_sequences),
                help="Comma-separated list of sequences that will cause the model to stop generating",
            ).split(",")
            new_stop_sequences = [
                seq.strip() for seq in new_stop_sequences if seq.strip()
            ]

            new_top_k = None
            if "anthropic" in config.model_id.lower():
                new_top_k = st.number_input(
                    "Top K",
                    min_value=1,
                    max_value=500,
                    value=config.top_k or 250,
                    help="The number of most-likely candidates that the model considers for the next token (Anthropic models only)",
                )

            new_system = st.text_area(
                "System Prompt",
                value=config.system or "",
                help="Optional system prompt to provide context or instructions for the model",
            )

            new_disable_streaming = st.checkbox(
                "Disable Streaming",
                value=config.disable_streaming,
                help="Disable streaming for this model",
            )

            # Add UI elements for other new parameters as needed

            # Update temp_llm_config with new values
            if (
                new_temp != config.temperature
                or new_max_tokens != config.max_output_tokens
                or new_top_p != config.top_p
                or new_stop_sequences != config.stop_sequences
                or (new_top_k is not None and new_top_k != config.top_k)
                or new_system != config.system
                or new_disable_streaming != config.disable_streaming
            ):
                st.session_state.temp_llm_config = LLMConfig(
                    model_id=config.model_id,
                    temperature=new_temp,
                    max_output_tokens=new_max_tokens,
                    region_name=config.region_name,
                    stop_sequences=new_stop_sequences,
                    top_p=new_top_p,
                    top_k=(
                        new_top_k if "anthropic" in config.model_id.lower() else None
                    ),
                    system=new_system,
                    disable_streaming=new_disable_streaming,
                    # Include other new parameters here
                )
                st.session_state.temp_llm_preset = LLMPreset.CUSTOM

        # Show Apply button
        if st.button("Apply Settings", type="primary"):
            # Apply temporary settings to actual settings
            st.session_state.llm_config = st.session_state.temp_llm_config
            st.session_state.llm_preset = st.session_state.temp_llm_preset

            # Recreate LLM with new settings
            additional_model_request_fields = {}
            if st.session_state.llm_config.top_k:
                additional_model_request_fields["top_k"] = (
                    st.session_state.llm_config.top_k
                )

            st.session_state.llm = ChatBedrockConverse(
                region_name=st.session_state.llm_config.region_name,
                model=st.session_state.llm_config.model_id,
                temperature=st.session_state.llm_config.temperature,
                max_tokens=st.session_state.llm_config.max_output_tokens,
                stop=st.session_state.llm_config.stop_sequences,
                top_p=st.session_state.llm_config.top_p,
                additional_model_request_fields=additional_model_request_fields,
            )
            st.success("Settings applied successfully!")
            st.rerun()


# Load environment variables
dotenv.load_dotenv()
