from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Literal, Optional, Sequence

import dotenv
import streamlit as st
from models.interfaces import (
    ChatSession,
    LLMConfig,
    LLMParameters,
    LLMPresetName,
    PRESET_CONFIGS,
)
from models.storage_interface import (
    StorageInterface,
)
import json
from pydantic import BaseModel
from services.bedrock import BedrockService, FoundationModelSummary
from streamlit.commands.page_config import Layout


class AppConfig(BaseModel):
    page_title: str = "RockTalk"
    page_icon: str = "🪨"
    layout: Layout = "wide"
    db_path: str = "chat_database.db"


class SettingsManager:

    @staticmethod
    def compute_preset(config: LLMParameters) -> LLMPresetName:
        print(f"Computing preset: {PRESET_CONFIGS}")
        for preset_name, preset_config in PRESET_CONFIGS.items():
            print(f"Checking preset {preset_name} {preset_config}")
            if all(
                getattr(config, key) == value
                for key, value in preset_config.model_dump().items()
            ):
                print(f"returning {preset_name}")
                return preset_name
        return LLMPresetName.CUSTOM

    @staticmethod
    def render_settings_widget(session: Optional[ChatSession] = None):
        """Render settings controls in the sidebar or dialog"""
        st.subheader("🛠️ Model Settings")
        print(
            "------------------------------widget loaded-------------------------------"
        )

        if "available_models" not in st.session_state:
            print("initial setting of available_models")
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
            print(
                f"initial setting of st.session_state.temp_llm_config to {st.session_state.temp_llm_config}"
            )

        if "llm_preset" not in st.session_state or st.session_state.llm_preset is None:
            st.session_state.llm_preset = SettingsManager.compute_preset(
                st.session_state.temp_llm_config.get_parameters()
            )
            print(f"computed preset: {st.session_state.llm_preset}")

        if (
            "temp_llm_preset" not in st.session_state
            or st.session_state.temp_llm_preset is None
        ):
            st.session_state.temp_llm_preset = st.session_state.llm_preset
            print(
                f"initial setting of st.session_state.temp_llm_preset to {st.session_state.temp_llm_preset}"
            )

        st.json(
            st.session_state.temp_llm_config.model_dump(),
        )

        # Display currently selected model
        current_model = next(
            (
                m
                for m in st.session_state.available_models
                if m.model_id == st.session_state.temp_llm_config.model_id
            ),
            None,
        )
        # if current_model:
        #     st.markdown(f"**Currently Selected Model:** {current_model.model_id}")
        #     if current_model.model_name:
        #         st.markdown(f"*{current_model.model_name}*")

        # Model selector in an expander
        with st.expander("Change Model", expanded=False):
            # TODO add refresh to get latest Bedrock models
            # bedrock = BedrockService()
            # st.session_state.available_models = bedrock.get_compatible_models()

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
                                st.session_state.temp_llm_config.model_id = (
                                    model.model_id
                                )
                                if (
                                    st.session_state.temp_llm_config.parameters.max_output_tokens
                                ):
                                    st.session_state.temp_llm_config.parameters.max_output_tokens = min(
                                        st.session_state.temp_llm_config.parameters.max_output_tokens,
                                        BedrockService.get_max_output_tokens(
                                            model_id=model.model_id
                                        ),
                                    )

        st.divider()

        # print(f"temp_llm_preset: {st.session_state.temp_llm_preset}")
        # print(
        #     f"first render? index = {list(LLMPresetName).index(st.session_state.temp_llm_preset)}"
        # )
        # Preset selector
        preset: LLMPresetName = st.selectbox(
            "Preset Configuration",
            options=list(LLMPresetName),
            format_func=lambda x: x.value,
            key="settings_preset",
            index=list(LLMPresetName).index(st.session_state.llm_preset),
            help="Select a preset configuration for the model settings",
        )
        # print("trying widget key = widget key...")
        # st.session_state.settings_preset = st.session_state.settings_preset

        # print(f'selectbox key: {st.session_state["settings_preset"]}')
        # print(f"selectbox val: {preset}")
        if preset != st.session_state.temp_llm_preset:
            # print(f"setting temp preset now to {preset}")
            if preset != LLMPresetName.CUSTOM:
                # set config values to preset values
                st.session_state.temp_llm_config.parameters = PRESET_CONFIGS[
                    preset
                ].model_copy()
            st.session_state.temp_llm_preset = preset
            print(
                f"after setting temp_llm_preset {st.session_state.temp_llm_preset} = preset {preset}"
            )

        # Show current settings with option to modify
        with st.expander("Advanced Settings", expanded=preset == LLMPresetName.CUSTOM):
            config: LLMConfig = st.session_state.temp_llm_config

            print(f"temp from config: {float(config.parameters.temperature)}")
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
                print(f"new_temp: {new_temp} | old {config.parameters.temperature}")
                st.session_state.temp_llm_config.parameters.temperature = new_temp
                st.session_state.temp_llm_preset = LLMPresetName.CUSTOM
            else:
                new_temp = None

            print(f"max_tokens from config: {config.parameters.max_output_tokens}")
            use_max_tokens = st.checkbox(
                "Use Max Tokens", value=config.parameters.max_output_tokens is not None
            )
            # if use_max_tokens:
            new_max_tokens = st.number_input(
                "Max Output Tokens",
                min_value=1,
                max_value=BedrockService.get_max_output_tokens(config.model_id),
                value=config.parameters.max_output_tokens
                or BedrockService.get_max_output_tokens(config.model_id),
                help="Maximum number of tokens in the response",
                disabled=not use_max_tokens,
            )
            if use_max_tokens:
                # and new_max_tokens != config.parameters.max_output_tokens
                print(
                    f"new_max_tokens: {new_max_tokens} | old {config.parameters.max_output_tokens}"
                )
                st.session_state.temp_llm_config.parameters.max_output_tokens = (
                    new_max_tokens
                )
                st.session_state.temp_llm_preset = LLMPresetName.CUSTOM

            print(f"top_p from config: {config.parameters.top_p}")
            use_top_p = st.checkbox(
                "Use Top P", value=config.parameters.top_p is not None
            )
            # if use_top_p:
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
                print(f"new_top_p: {new_top_p} | old {config.parameters.top_p}")
                st.session_state.temp_llm_config.parameters.top_p = new_top_p
                st.session_state.temp_llm_preset = LLMPresetName.CUSTOM

            new_top_k = None
            if "anthropic" in config.model_id.lower():
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

                    print(f"new_top_k: {new_top_k} | old {config.parameters.top_k}")
                    st.session_state.temp_llm_config.parameters.top_k = new_top_k
                    st.session_state.temp_llm_preset = LLMPresetName.CUSTOM
            use_system = st.checkbox(
                "Use System Prompt", value=config.system is not None
            )
            if use_system:
                new_system = st.text_area(
                    "System Prompt",
                    value=config.system or "",
                    help="Optional system prompt to provide context or instructions for the model",
                    disabled=config.system is None,
                )
                # if new_system != config.system:
                st.session_state.temp_llm_config.system = new_system

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
        success_plecholder = st.empty()
        if st.button("Apply Settings", type="primary"):
            if session:
                print(
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
            with success_plecholder:
                st.success("Settings applied successfully!")
            time.sleep(1)
            st.rerun()


# Load environment variables
dotenv.load_dotenv()
