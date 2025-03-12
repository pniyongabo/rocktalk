import os
from pathlib import Path
from unittest import mock

import pytest
import streamlit as st
import yaml

from rocktalk.app_context import AppContext
from rocktalk.utils.log import ROCKTALK_DIR


def create_test_auth_config(tmp_path: Path) -> Path:
    """Create a test auth.yaml file"""
    auth_config = {
        "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
        "credentials": {
            "usernames": {
                "testuser": {
                    "name": "Test User",
                    "password": "hashedpassword",  # In reality, this would be properly hashed
                }
            }
        },
    }

    auth_file = tmp_path / "auth.yaml"
    with open(auth_file, "w") as f:
        yaml.dump(auth_config, f)

    return auth_file


def test_auth_initialization(tmp_path):
    """Test authentication initialization"""
    # Create test auth config
    auth_file = create_test_auth_config(tmp_path)

    # Mock ROCKTALK_DIR to use our temporary path
    with mock.patch("rocktalk.utils.log.ROCKTALK_DIR", str(tmp_path)):
        ctx = AppContext()

        # Verify auth was initialized
        assert ctx.using_auth
        assert ctx.auth is not None


def test_auth_disabled_without_config():
    """Test authentication is disabled when no config exists"""
    # Use a non-existent directory for ROCKTALK_DIR
    with mock.patch("rocktalk.utils.log.ROCKTALK_DIR", "/nonexistent"):
        ctx = AppContext()

        # Verify auth is disabled
        assert not ctx.using_auth
        assert ctx.auth is None


def test_successful_login(tmp_path):
    """Test successful login flow"""
    # Create test auth config
    auth_file = create_test_auth_config(tmp_path)

    # Mock ROCKTALK_DIR and session state
    with (
        mock.patch("rocktalk.utils.log.ROCKTALK_DIR", str(tmp_path)),
        mock.patch("streamlit.session_state", {}) as mock_state,
    ):

        ctx = AppContext()

        # Mock successful authentication
        mock_state["authentication_status"] = True
        mock_state["username"] = "testuser"

        # Verify authentication succeeds
        assert ctx.handle_authentication()


def test_failed_login(tmp_path):
    """Test failed login flow"""
    # Create test auth config
    auth_file = create_test_auth_config(tmp_path)

    # Mock ROCKTALK_DIR and session state
    with (
        mock.patch("rocktalk.utils.log.ROCKTALK_DIR", str(tmp_path)),
        mock.patch("streamlit.session_state", {}) as mock_state,
    ):

        ctx = AppContext()

        # Mock failed authentication
        mock_state["authentication_status"] = False

        # Verify authentication fails
        assert not ctx.handle_authentication()


def test_auth_persistence(tmp_path):
    """Test authentication persistence across sessions"""
    # Create test auth config
    auth_file = create_test_auth_config(tmp_path)

    # Mock ROCKTALK_DIR and session state
    with (
        mock.patch("rocktalk.utils.log.ROCKTALK_DIR", str(tmp_path)),
        mock.patch("streamlit.session_state", {}) as mock_state,
    ):

        # First session
        ctx1 = AppContext()
        mock_state["authentication_status"] = True
        mock_state["username"] = "testuser"

        assert ctx1.handle_authentication()

        # Simulate new session with cookie
        ctx2 = AppContext()
        assert ctx2.handle_authentication()


def test_invalid_auth_config(tmp_path):
    """Test handling of invalid auth configuration"""
    # Create invalid auth config
    auth_file = tmp_path / "auth.yaml"
    with open(auth_file, "w") as f:
        f.write("invalid: yaml: content")

    # Mock ROCKTALK_DIR
    with mock.patch("rocktalk.utils.log.ROCKTALK_DIR", str(tmp_path)):
        ctx = AppContext()

        # Verify auth is disabled due to invalid config
        assert not ctx.using_auth
        assert ctx.auth is None


def test_auth_error_handling(tmp_path):
    """Test authentication error handling"""
    # Create test auth config
    auth_file = create_test_auth_config(tmp_path)

    # Mock ROCKTALK_DIR and session state
    with (
        mock.patch("rocktalk.utils.log.ROCKTALK_DIR", str(tmp_path)),
        mock.patch("streamlit.session_state", {}) as mock_state,
    ):

        ctx = AppContext()

        # Mock authentication error
        mock_state["authentication_status"] = None

        # Verify graceful error handling
        assert not ctx.handle_authentication()


def test_auth_with_private_sessions(tmp_path, temp_database):
    """Test authentication with private sessions"""
    # Create test auth config
    auth_file = create_test_auth_config(tmp_path)

    # Mock ROCKTALK_DIR and session state
    with (
        mock.patch("rocktalk.utils.log.ROCKTALK_DIR", str(tmp_path)),
        mock.patch("streamlit.session_state", {}) as mock_state,
    ):

        ctx = AppContext()

        # Mock successful authentication
        mock_state["authentication_status"] = True
        mock_state["username"] = "testuser"

        # Create a private session
        session = temp_database.create_session("Private Test Session")
        session.is_private = True
        temp_database.store_session(session)

        # Verify authenticated user can access private session
        sessions = temp_database.get_recent_sessions(include_private=True)
        assert any(s.is_private for s in sessions)

        # Mock unauthenticated state
        mock_state["authentication_status"] = False
        mock_state["username"] = None

        # Verify unauthenticated user cannot see private sessions
        sessions = temp_database.get_recent_sessions(include_private=False)
        assert not any(s.is_private for s in sessions)
