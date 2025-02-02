# rocktalk/services/creds.py
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Optional

import streamlit as st
from pydantic import BaseModel, Field, SecretStr
from utils.log import logger


class AwsCredentials(BaseModel):
    aws_access_key_id: SecretStr
    aws_secret_access_key: SecretStr
    aws_session_token: Optional[SecretStr] = None
    aws_region: str
    created_at: datetime = Field(default_factory=partial(datetime.now, timezone.utc))


def secrets_file_exists() -> bool:
    """Check if the secrets.toml file exists in any of the standard locations."""
    # Standard locations for secrets.toml
    home_dir = Path.home()
    cwd = Path.cwd()
    possible_paths = [
        home_dir / ".streamlit" / "secrets.toml",  # Global secrets file
        cwd / ".streamlit" / "secrets.toml",  # Per-project secrets file
    ]

    # Check if any of the possible paths exist
    for path in possible_paths:
        if path.exists():
            return True
    return False


def get_aws_credentials(
    use_streamlit_secrets: bool = True,
) -> Optional[AwsCredentials]:
    """Get AWS credentials from Streamlit secrets if provided.
    Returns AwsCredentials object if secrets are provided, else None.
    """
    DEFAULT_REGION = "us-west-2"

    if use_streamlit_secrets and secrets_file_exists():
        # Now it's safe to access st.secrets without triggering FileNotFoundError
        aws_secrets = st.secrets.get("aws", {})
        aws_access_key_id = aws_secrets.get("aws_access_key_id")
        aws_secret_access_key = aws_secrets.get("aws_secret_access_key")

        if aws_access_key_id and aws_secret_access_key:
            aws_session_token = aws_secrets.get("aws_session_token")
            aws_region = aws_secrets.get("aws_region", DEFAULT_REGION)
            return AwsCredentials(
                aws_access_key_id=SecretStr(aws_access_key_id),
                aws_secret_access_key=SecretStr(aws_secret_access_key),
                aws_region=aws_region,
                aws_session_token=(
                    SecretStr(aws_session_token) if aws_session_token else None
                ),
            )
        else:
            logger.info("AWS access keys not found in Streamlit secrets.")
    else:
        logger.debug(
            "secrets.toml file not found; falling back to default credential chain."
        )

    # No Streamlit secrets provided or secrets.toml file doesn't exist; return None
    return None


def get_cached_aws_credentials() -> Optional[AwsCredentials]:
    """Return AwsCredentials from Streamlit secrets, if present. Credentials from other sources are not cached."""
    credentials = get_aws_credentials()
    return credentials
