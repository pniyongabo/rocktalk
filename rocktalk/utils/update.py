import html
import os
import subprocess
import sys
import time
from enum import StrEnum
from typing import List, Optional

import streamlit as st

from .log import logger

PAUSE_BEFORE_RELOADING = 2

# Add to top of update.py
from config.button_group import ButtonGroupManager


class UpdateActions(StrEnum):
    check_updates = "check_updates_action"
    apply_update = "apply_update_action"
    cancel_update = "cancel_update_action"


class UpdateManager:
    """Manages the update process UI and state"""

    update_actions = ButtonGroupManager(
        "update_actions",
        [
            UpdateActions.check_updates,
            UpdateActions.apply_update,
            UpdateActions.cancel_update,
        ],
    )

    def __init__(self):
        if "update_available" not in st.session_state:
            st.session_state.update_available = False
        if "update_error" not in st.session_state:
            st.session_state.update_error = None

    def render(self):
        """Render the update interface"""
        # Only validate git environment when user clicks check
        if self.update_actions.is_active(UpdateActions.check_updates):
            if not validate_git_environment():
                st.error("Git environment is not properly configured")
                return

            try:
                if fetch_updates():
                    st.session_state.update_available = check_update_status()
                self.render_update_form()
            except Exception as e:
                st.session_state.update_error = str(e)
                logger.exception("Error checking for updates")
                self.render_update_form()
        else:
            # Just show the initial button
            if st.button("Check for Updates"):
                self.update_actions.toggle_action(UpdateActions.check_updates)
                st.rerun(scope="fragment")

    def render_update_form(self):
        """Render the update confirmation form"""
        with st.form(
            "update_form", clear_on_submit=False
        ):  # Prevent form from clearing
            if st.session_state.update_error:
                st.error(f"Error checking for updates: {st.session_state.update_error}")

            elif st.session_state.update_available:
                st.info("A new version is available")

                # Show available changes if any
                if changes := get_remote_changes():
                    st.markdown("#### Available updates:")
                    st.text(changes)

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button(
                        ":material/save: Update Now",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            if pull_updates():
                                # Check if dependencies need updating
                                if update_dependencies():
                                    st.info("Dependencies updated successfully")

                                st.success("Update successful. Restarting app...")
                                time.sleep(PAUSE_BEFORE_RELOADING)

                                # Restart the Streamlit app
                                python = sys.executable
                                os.execl(python, python, *sys.argv)
                            else:
                                st.error("Update failed")
                        except Exception as e:
                            st.error(f"Error during update: {str(e)}")
                            logger.exception("Error during update")

                with col2:
                    if st.form_submit_button(
                        ":material/cancel: Cancel", use_container_width=True
                    ):
                        self.reset_state()
                        self.update_actions.rerun()
            else:
                st.success("App is up to date")
                if st.form_submit_button("Close", use_container_width=True):
                    self.reset_state()
                    self.update_actions.rerun()

    def reset_state(self):
        """Reset all update-related state."""
        st.session_state.update_available = False
        st.session_state.update_error = None
        self.update_actions.clear_all()


def check_for_updates():
    """Initialize and render the update manager"""
    UpdateManager().render()


def run_git_command(
    command: List[str],
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
    timeout: int = 30,
) -> str:
    """Helper function to run git commands and capture output

    Args:
        command (list): Git command to run
        capture_output (bool): Capture stdout and stderr
        text (bool): Return output as text
        check (bool): Raise exception on non-zero return code
        timeout (int): Timeout for command execution

    Returns:
        str: Command output
    """
    try:
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=text,
            check=check,
            timeout=timeout,
        )
        logger.debug(f"Git command {command}:\n{result}\n")
        return result.stdout.strip() if result.stdout else ""
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {command}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        logger.error(f"Git command timed out: {command}")
        raise


def validate_git_environment() -> bool:
    """Validate git environment and repository configuration

    Returns:
        bool: True if git environment is valid, False otherwise
    """
    try:
        # Check git installation
        run_git_command(["git", "--version"])

        # Verify it's a git repository
        run_git_command(["git", "rev-parse", "--is-inside-work-tree"])

        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Git environment validation failed: {e}")
        st.error("Git environment is not properly configured")
        return False


def sanitize_git_output(output: str) -> str:
    """Sanitize git command output to prevent potential XSS

    Args:
        output (str): Raw git command output

    Returns:
        str: Sanitized output
    """
    return html.escape(output)


def get_remote_changes(branch: str = "main") -> Optional[str]:
    """Retrieve remote changes for the specified branch

    Args:
        branch (str): Branch to check for changes

    Returns:
        Optional[str]: Formatted list of commits or None
    """
    try:
        return run_git_command(
            [
                "git",
                "log",
                f"HEAD..origin/{branch}",
                "--pretty=format:%h | %an | %ad | %s",
                "--date=short",
            ]
        )
    except subprocess.CalledProcessError:
        return None


def update_dependencies() -> bool:
    """Update Python dependencies if requirements.txt has changed

    Returns:
        bool: True if dependencies were updated, False otherwise
    """
    try:
        # Check if requirements.txt was modified in the last commit
        requirements_updated = run_git_command(
            ["git", "diff", "--name-only", "HEAD^", "HEAD", "requirements.txt"]
        )

        if requirements_updated:
            st.info("Requirements changed. Updating dependencies...")
            subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        return False
    except Exception as e:
        st.error(f"Dependency update failed: {e}")
        logger.exception("Dependency update error")
        return False


def fetch_updates() -> bool:
    """Fetch updates from remote repository

    Returns:
        bool: True if fetch was successful
    """
    try:
        output = run_git_command(["git", "fetch"], timeout=10)
        if output:
            logger.info(f"Git fetch output: {output}")
        return True
    except Exception as e:
        logger.exception("Error fetching updates")
        return False


def check_update_status() -> bool:
    """Check if local branch is behind remote

    Returns:
        bool: True if updates are available
    """
    try:
        status_output = run_git_command(["git", "status", "-uno"])
        return "Your branch is behind" in status_output
    except Exception as e:
        logger.exception("Error checking update status")
        raise


def pull_updates() -> bool:
    """Pull latest changes from remote

    Returns:
        bool: True if pull was successful
    """
    try:
        output = run_git_command(["git", "pull"], timeout=30)
        if output:
            logger.info(f"Git pull output: {output}")
        return True
    except Exception as e:
        st.error(f"Update failed: {e}")
        logger.exception("Error pulling updates")
        raise e
