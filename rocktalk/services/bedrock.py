# rocktalk/services/bedrock.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import boto3
from mypy_boto3_bedrock.type_defs import (
    ListFoundationModelsResponseTypeDef,
    FoundationModelSummaryTypeDef,
)
from mypy_boto3_bedrock.literals import (
    ModelModalityType,
    ModelCustomizationType,
    InferenceTypeType,
    FoundationModelLifecycleStatusType,
)

# Known maximum output tokens for specific models
# These values are approximate and may change; always refer to the latest documentation
KNOWN_MAX_OUTPUT_TOKENS: Dict[str, int] = {
    "anthropic.claude-3-sonnet-20240229-v1:0": 4096,
    "anthropic.claude-3-haiku-20240307-v1:0": 4096,
    "anthropic.claude-3-opus-20240229-v1:0": 4096,
    "anthropic.claude-v2:1": 4096,
    "anthropic.claude-instant-v1": 4096,
    "amazon.titan-text-express-v1": 8192,
    "cohere.command-text-v14": 4096,
    "meta.llama3-1-70b-instruct-v1:0": 4096,
    "mistral.mistral-large-2407-v1:0": 32768,
}

DEFAULT_MAX_OUTPUT_TOKENS: int = 4096


@dataclass
class FoundationModelSummary:
    model_id: str
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    model_arn: Optional[str] = None
    input_modalities: Optional[List[ModelModalityType]] = None
    output_modalities: Optional[List[ModelModalityType]] = None
    response_streaming_supported: Optional[bool] = None
    customizations_supported: Optional[List[ModelCustomizationType]] = None
    inference_types_supported: Optional[List[InferenceTypeType]] = None
    model_lifecycle: Optional[FoundationModelLifecycleStatusType] = None

    @classmethod
    def from_dict(cls, data: FoundationModelSummaryTypeDef) -> "FoundationModelSummary":
        return cls(
            model_id=data["modelId"],
            provider_name=data.get("providerName"),
            model_name=data.get("modelName"),
            model_arn=data.get("modelArn"),
            input_modalities=data.get("inputModalities"),
            output_modalities=data.get("outputModalities"),
            response_streaming_supported=data.get("responseStreamingSupported"),
            customizations_supported=data.get("customizationsSupported"),
            inference_types_supported=data.get("inferenceTypesSupported"),
            model_lifecycle=data.get("modelLifecycle", dict()).get("status"),
        )


class BedrockService:
    def __init__(self, region_name: str = "us-west-2"):
        self.client = boto3.client("bedrock", region_name=region_name)
        self.runtime = boto3.client("bedrock-runtime", region_name=region_name)

    def list_foundation_models(self) -> List[FoundationModelSummary]:
        """Get list of available foundation models from Bedrock."""
        try:
            response: ListFoundationModelsResponseTypeDef = (
                self.client.list_foundation_models()
            )
            models = []

            for model_summary in response["modelSummaries"]:
                model = FoundationModelSummary.from_dict(model_summary)
                models.append(model)
            # Sort models by provider and name
            return sorted(
                models,
                key=lambda x: (
                    x.provider_name if x.provider_name else "",
                    x.model_id,
                ),
            )

        except Exception as e:
            print(f"Error fetching models: {str(e)}")
            return []

    @staticmethod
    def get_compatible_models() -> List[FoundationModelSummary]:
        """Get list of models compatible with chat functionality."""
        service = BedrockService()
        models = service.list_foundation_models()

        # Filter for models that:
        # - Support text output
        # - Support streaming
        # - Are in ACTIVE state
        # - Support ON_DEMAND inference
        return [
            model
            for model in models
            if (
                model.output_modalities is not None
                and "TEXT" in model.output_modalities
                and model.response_streaming_supported
                and model.model_lifecycle is not None
                and model.model_lifecycle == "ACTIVE"
                and model.inference_types_supported is not None
                and "ON_DEMAND" in model.inference_types_supported
            )
        ]

    @staticmethod
    def get_max_output_tokens(model_id: str) -> int:
        """
        Get the maximum number of output tokens for a specific model.

        Args:
            model_id (str): The ID of the Bedrock model

        Returns:
            int: The maximum number of output tokens for the model
        """
        return KNOWN_MAX_OUTPUT_TOKENS.get(model_id, DEFAULT_MAX_OUTPUT_TOKENS)
