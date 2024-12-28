from datetime import datetime
import os
from typing import Optional

import boto3
import streamlit as st
from botocore.exceptions import NoCredentialsError
from pydantic import BaseModel, Field, SecretStr
from utils.log import logger


class AwsCredentials(BaseModel):
    aws_access_key_id: SecretStr
    aws_secret_access_key: SecretStr
    aws_session_token: Optional[SecretStr] = None
    aws_region: str
    created_at: datetime = Field(default_factory=datetime.now)


def get_aws_credentials(use_streamlit_secrets: bool = True) -> AwsCredentials:
    """
    Get AWS credentials in following order:
    1. boto3 credential chain (AWS CLI/IAM role/environment)
    2. Streamlit secrets (if deployed)
    3. Environment variables
    Returns AwsCredentials object
    """
    DEFAULT_REGION = "us-west-2"
    # Try boto3 credential chain first
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            frozen_credentials = credentials.get_frozen_credentials()
            return AwsCredentials(
                aws_access_key_id=SecretStr(frozen_credentials.access_key),
                aws_secret_access_key=SecretStr(frozen_credentials.secret_key),
                aws_session_token=(
                    SecretStr(frozen_credentials.token)
                    if frozen_credentials.token
                    else None
                ),
                aws_region=session.region_name or DEFAULT_REGION,
            )
    except NoCredentialsError:
        pass

    # Fall back to Streamlit secrets or environment variables
    try:
        if use_streamlit_secrets:
            # Get AWS secrets from Streamlit
            aws_secrets = st.secrets.get("aws", {})
            return AwsCredentials(
                aws_access_key_id=SecretStr(aws_secrets["aws_access_key_id"]),
                aws_secret_access_key=SecretStr(aws_secrets["aws_secret_access_key"]),
                aws_region=aws_secrets.get("aws_region", DEFAULT_REGION),
                aws_session_token=(
                    SecretStr(aws_secrets["aws_session_token"])
                    if "aws_session_token" in aws_secrets
                    else None
                ),
            )
        else:
            # Get AWS credentials from environment variables
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")

            if not aws_access_key or not aws_secret_key:
                raise ValueError(
                    "Required AWS credentials not found in environment variables"
                )

            return AwsCredentials(
                aws_access_key_id=SecretStr(aws_access_key),
                aws_secret_access_key=SecretStr(aws_secret_key),
                aws_session_token=(
                    SecretStr(aws_session_token) if aws_session_token else None
                ),
                aws_region=os.getenv("AWS_REGION", DEFAULT_REGION),
            )

    except Exception as e:
        logger.error(f"Error getting AWS credentials: {e}")
        raise RuntimeError from e


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cached_aws_credentials() -> AwsCredentials:
    """
    Cached version of AWS credentials retrieval
    TTL of 1 hour to allow for credential rotation
    """
    credentials = get_aws_credentials()
    return credentials
