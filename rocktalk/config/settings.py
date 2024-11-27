import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Sequence

import dotenv
import streamlit as st
from models.interfaces import (
    PRESET_CONFIGS,
    ChatSession,
    LLMConfig,
    LLMParameters,
    LLMPresetName,
)
from models.storage_interface import StorageInterface
from pydantic import BaseModel
from services.bedrock import BedrockService, FoundationModelSummary
from streamlit.commands.page_config import Layout
from utils.log import logger


class AppConfig(BaseModel):
    page_title: str = "RockTalk"
    page_icon: str = "🪨"
    layout: Layout = "wide"
    db_path: str = "chat_database.db"


class SettingsManager:
    @staticmethod
    def set_preset_values():
        logger.debug(st.session_state.settings_preset)
        if st.session_state.settings_preset != LLMPresetName.CUSTOM:
            # set config values to preset values
            st.session_state.temp_llm_config.parameters = PRESET_CONFIGS[
                st.session_state.settings_preset
            ].model_copy()
        st.session_state.temp_llm_preset = st.session_state.settings_preset
        logger.debug(
            f"after setting temp_llm_preset {st.session_state.temp_llm_preset} = preset {st.session_state.settings_preset}"
        )

    @staticmethod
    def reorder_model_providers():
        st.session_state.ordered_providers = sorted(
            st.session_state.model_providers.keys(),
            key=lambda x: x != st.session_state.current_provider,
        )

    @staticmethod
    def set_temp_llm_config_model(provider: str, bedrock_model_id: str):
        logger.debug(f"set model to {bedrock_model_id}")

        st.session_state.temp_llm_config.bedrock_model_id = bedrock_model_id
        if st.session_state.temp_llm_config.parameters.max_output_tokens:
            st.session_state.temp_llm_config.parameters.max_output_tokens = min(
                st.session_state.temp_llm_config.parameters.max_output_tokens,
                BedrockService.get_max_output_tokens(bedrock_model_id=bedrock_model_id),
            )
        st.session_state.current_provider = provider

    @staticmethod
    def compute_preset(config: LLMParameters) -> LLMPresetName:
        logger.debug(f"Computing preset: {PRESET_CONFIGS}")
        for preset_name, preset_config in PRESET_CONFIGS.items():
            logger.debug(f"Checking preset {preset_name} {preset_config}")
            if all(
                getattr(config, key) == value
                for key, value in preset_config.model_dump().items()
            ):
                logger.debug(f"returning {preset_name}")
                return preset_name
        return LLMPresetName.CUSTOM

    @staticmethod
    def clear_cached_settings_vars():
        """Clear cached settings variables"""
        if "temp_llm_config" in st.session_state:
            del st.session_state.temp_llm_config
        if "temp_llm_preset" in st.session_state:
            del st.session_state.temp_llm_preset
        if "llm_preset" in st.session_state:
            del st.session_state.llm_preset
        if "providers_reorder" in st.session_state:
            del st.session_state.providers_reorder
        # TODO should we cache or not these?
        # if "available_models" in st.session_state:
        #     del st.session_state.available_models
        if "current_provider" in st.session_state:
            del st.session_state.current_provider

    @staticmethod
    def render_settings_widget(session: Optional[ChatSession] = None):
        """Render settings controls in the sidebar or dialog"""
        st.subheader("🛠️ Model Settings")

        if "available_models" not in st.session_state:
            # logger.debug("initial setting of available_models")
            bedrock = BedrockService()
            st.session_state.available_models = bedrock.get_compatible_models()

        if (
            "temp_llm_config" not in st.session_state
            or st.session_state.temp_llm_config is None
        ):
            if session:
                st.session_state.temp_llm_config = session.config
            else:
                st.session_state.temp_llm_config = st.session_state.llm.get_config()

        if "llm_preset" not in st.session_state or st.session_state.llm_preset is None:
            st.session_state.llm_preset = SettingsManager.compute_preset(
                st.session_state.temp_llm_config.get_parameters()
            )
            logger.debug(f"computed preset: {st.session_state.llm_preset}")

        if (
            "temp_llm_preset" not in st.session_state
            or st.session_state.temp_llm_preset is None
        ):
            st.session_state.temp_llm_preset = st.session_state.llm_preset
            logger.debug(
                f"initial setting of st.session_state.temp_llm_preset to {st.session_state.temp_llm_preset}"
            )
        if (
            "providers_reorder" not in st.session_state
            or st.session_state.providers_reorder is None
        ):
            st.session_state.providers_reorder = True

        st.json(
            st.session_state.temp_llm_config.model_dump(),
        )

        # Display currently selected model
        current_model = next(
            (
                m
                for m in st.session_state.available_models
                if m.bedrock_model_id
                == st.session_state.temp_llm_config.bedrock_model_id
            ),
            None,
        )
        # if current_model:
        #     st.markdown(f"**Currently Selected Model:** {current_model.bedrock_model_id}")
        #     if current_model.model_name:
        #         st.markdown(f"*{current_model.model_name}*")

        # Model selector in an expander
        with st.expander("Change Model", expanded=False):
            # TODO add refresh to get latest Bedrock models
            # bedrock = BedrockService()
            # st.session_state.available_models = bedrock.get_compatible_models()

            if (
                "model_providers" not in st.session_state
                or st.session_state.model_providers is None
            ):
                # Group models by provider
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
                # Reorder providers to put the current model's provider first
                st.session_state.current_provider = (
                    current_model.provider_name if current_model else None
                )
            if (
                "ordered_providers" not in st.session_state
                or st.session_state.ordered_providers is None
            ):
                # only order the providers once based on current model, otherwise the tabs will move on user causing bad UX
                SettingsManager.reorder_model_providers()

            # Create provider tabs
            provider_tabs = st.tabs(st.session_state.ordered_providers)
            # logger.debug("displaying models")
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
                                    if model.bedrock_model_id
                                    == st.session_state.temp_llm_config.bedrock_model_id
                                    else "secondary"
                                ),
                                on_click=SettingsManager.set_temp_llm_config_model,
                                args=(
                                    provider,
                                    model.bedrock_model_id,
                                ),
                            )
        # logger.debug(f"temp_llm_preset: {st.session_state.temp_llm_preset}")
        # Preset selector
        preset: LLMPresetName = st.selectbox(
            "Preset Configuration",
            options=list(LLMPresetName),
            format_func=lambda x: x.value,
            key="settings_preset",
            index=list(LLMPresetName).index(st.session_state.llm_preset),
            help="Select a preset configuration for the model settings",
            on_change=SettingsManager.set_preset_values,
        )

        # Show current settings with option to modify
        with st.expander("Advanced Settings", expanded=preset == LLMPresetName.CUSTOM):
            config: LLMConfig = st.session_state.temp_llm_config

            # logger.debug(f"temp from config: {float(config.parameters.temperature)}")

            if not session:
                # use_system = st.checkbox(
                #     "Use System Prompt", value=config.system is not None
                # )
                # if use_system:
                new_system = st.text_area(
                    "System Prompt",
                    value=config.system or "",
                    help="Optional system prompt to provide context or instructions for the model",
                    # disabled=config.system is None,
                )
                # if new_system != config.system:
                logger.debug(f"Setting system message to: '{new_system}'")
                st.session_state.temp_llm_config.system = new_system.strip() or None
            else:
                st.markdown(
                    f"*System prompt is not editable in existing session*\n\n**System message:** {st.session_state.temp_llm_config.system}"
                )

            # Temperature control
            use_temp = st.checkbox(
                "Use Temperature", value=config.parameters.temperature is not None
            )
            new_temp = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=float(config.parameters.temperature),
                step=0.1,
                help="Higher values make the output more random, lower values more deterministic",
                disabled=not use_temp,
            )
            if use_temp:
                # logger.debug(
                #     f"new_temp: {new_temp} | old {config.parameters.temperature}"
                # )
                st.session_state.temp_llm_config.parameters.temperature = new_temp
                st.session_state.temp_llm_preset = LLMPresetName.CUSTOM
            else:
                new_temp = None

            # logger.debug(
            #     f"max_tokens from config: {config.parameters.max_output_tokens}"
            # )
            use_max_tokens = st.checkbox(
                "Use Max Tokens", value=config.parameters.max_output_tokens is not None
            )
            # if use_max_tokens:
            new_max_tokens = st.number_input(
                "Max Output Tokens",
                min_value=1,
                max_value=BedrockService.get_max_output_tokens(config.bedrock_model_id),
                value=config.parameters.max_output_tokens
                or BedrockService.get_max_output_tokens(config.bedrock_model_id),
                help="Maximum number of tokens in the response",
                disabled=not use_max_tokens,
            )
            if use_max_tokens:
                st.session_state.temp_llm_config.parameters.max_output_tokens = (
                    new_max_tokens
                )
                st.session_state.temp_llm_preset = LLMPresetName.CUSTOM

            # logger.debug(f"top_p from config: {config.parameters.top_p}")
            use_top_p = st.checkbox(
                "Use Top P", value=config.parameters.top_p is not None
            )

            new_top_p = st.slider(
                "Top P",
                min_value=0.0,
                max_value=1.0,
                value=config.parameters.top_p or 1.0,
                step=0.01,
                help="The percentage of most-likely candidates that the model considers for the next token",
                disabled=not use_top_p,
            )
            if use_top_p:
                # logger.debug(f"new_top_p: {new_top_p} | old {config.parameters.top_p}")
                st.session_state.temp_llm_config.parameters.top_p = new_top_p
                st.session_state.temp_llm_preset = LLMPresetName.CUSTOM

            new_top_k = None
            if "anthropic" in config.bedrock_model_id.lower():
                use_top_k = st.checkbox(
                    "Use Top K", value=config.parameters.top_k is not None
                )
                if use_top_k:
                    new_top_k = st.number_input(
                        "Top K",
                        min_value=1,
                        max_value=500,
                        value=config.parameters.top_k or 250,
                        help="The number of most-likely candidates that the model considers for the next token (Anthropic models only)",
                        disabled=config.parameters.top_k is None,
                    )

                    # logger.debug(
                    #     f"new_top_k: {new_top_k} | old {config.parameters.top_k}"
                    # )
                    st.session_state.temp_llm_config.parameters.top_k = new_top_k
                    st.session_state.temp_llm_preset = LLMPresetName.CUSTOM

            new_stop_sequences = st.text_input(
                "Stop Sequences",
                value=", ".join(config.stop_sequences),
                help="Comma-separated list of sequences that will cause the model to stop generating",
            ).split(",")
            new_stop_sequences = [
                seq.strip() for seq in new_stop_sequences if seq.strip()
            ]
            # if new_stop_sequences != config.stop_sequences:
            st.session_state.temp_llm_config.stop_sequences = new_stop_sequences

        # Show Apply button
        # Add checkbox for setting as default
        set_as_default = st.checkbox("Set as default configuration", value=False)
        success_placeholder = st.empty()
        if st.button("Apply Settings", type="primary"):
            if session:
                logger.debug(
                    f"Saving config to session {session.session_id}: { st.session_state.temp_llm_config}"
                )
                session.config = st.session_state.temp_llm_config
                storage: StorageInterface = st.session_state.storage
                storage.update_session(session=session)

            st.session_state.llm.update_config(st.session_state.temp_llm_config)

            if set_as_default:
                LLMConfig.set_default(st.session_state.temp_llm_config)

            st.session_state.temp_llm_preset = None
            st.session_state.llm_preset = None
            st.session_state.temp_llm_config = None
            st.session_state.model_providers = None
            st.session_state.current_provider = None
            st.session_state.ordered_providers = None
            with success_placeholder:
                st.success("Settings applied successfully!")
            time.sleep(1)
            st.rerun()


# Load environment variables
dotenv.load_dotenv()
