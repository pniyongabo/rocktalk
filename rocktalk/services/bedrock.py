# rocktalk/services/bedrock.py
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import boto3
from mypy_boto3_bedrock.literals import (
    FoundationModelLifecycleStatusType,
    InferenceTypeType,
    ModelCustomizationType,
    ModelModalityType,
)
from mypy_boto3_bedrock.type_defs import (
    FoundationModelSummaryTypeDef,
    ListFoundationModelsResponseTypeDef,
)
from utils.log import logger

from .creds import get_cached_aws_credentials

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
    bedrock_model_id: str
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
            bedrock_model_id=data["modelId"],
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
    def __init__(self):
        creds = get_cached_aws_credentials()
        region_name = (
            creds.aws_region if creds else os.getenv("AWS_REGION", "us-west-2")
        )
        if creds:
            # Use credentials from Streamlit secrets
            self.client = boto3.client(
                "bedrock",
                region_name=region_name,
                aws_access_key_id=creds.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=creds.aws_secret_access_key.get_secret_value(),
                aws_session_token=(
                    creds.aws_session_token.get_secret_value()
                    if creds.aws_session_token
                    else None
                ),
            )
        else:
            # Let boto3 manage credentials
            self.client = boto3.client(
                "bedrock",
                region_name=region_name,
            )

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
                    x.bedrock_model_id,
                ),
            )

        except Exception as e:
            logger.error(f"Error fetching models: {str(e)}")
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
        compatible_models = []
        for model in models:
            if model.output_modalities is None:
                logger.debug(
                    f"Model {model.bedrock_model_id} skipped: No output modalities specified"
                )
            elif "TEXT" not in model.output_modalities:
                logger.debug(
                    f"Model {model.bedrock_model_id} skipped: Does not support TEXT output"
                )
            elif not model.response_streaming_supported:
                logger.debug(
                    f"Model {model.bedrock_model_id} skipped: Does not support streaming"
                )
            elif model.model_lifecycle is None:
                logger.debug(
                    f"Model {model.bedrock_model_id} skipped: No lifecycle status specified"
                )
            elif model.model_lifecycle != "ACTIVE":
                logger.debug(
                    f"Model {model.bedrock_model_id} skipped: Not in ACTIVE state"
                )
            elif model.inference_types_supported is None:
                logger.debug(
                    f"Model {model.bedrock_model_id} skipped: No inference types specified"
                )
            elif "ON_DEMAND" not in model.inference_types_supported:
                logger.debug(
                    f"Model {model.bedrock_model_id} skipped: Does not support ON_DEMAND inference. Model supports inference type: {model.inference_types_supported}"
                )
                if "INFERENCE_PROFILE" in model.inference_types_supported:
                    # arn=f"arn:aws:bedrock:{creds.aws_region}::foundation-model/{model.bedrock_model_id}"
                    # logger.info(f"Model {model.bedrock_model_id} supports INFERENCE_PROFILE inference. Trying model arn: {arn}")
                    inference_profile_id = f"us.{model.bedrock_model_id}"
                    logger.debug(
                        f"Model {model.bedrock_model_id} supports INFERENCE_PROFILE inference. Trying model inference profile id: {inference_profile_id}"
                    )

                    compatible_models.append(
                        FoundationModelSummary(
                            bedrock_model_id=inference_profile_id,
                            model_arn=model.model_arn,
                            provider_name=model.provider_name,
                            model_name=model.model_name,
                        )
                    )

            else:
                compatible_models.append(model)

        return compatible_models

    @staticmethod
    def get_max_output_tokens(bedrock_model_id: str) -> int:
        """Get the maximum number of output tokens for a specific model.

        Args:
            bedrock_model_id (str): The ID of the Bedrock model

        Returns:
            int: The maximum number of output tokens for the model
        """
        return KNOWN_MAX_OUTPUT_TOKENS.get(bedrock_model_id, DEFAULT_MAX_OUTPUT_TOKENS)
