import subprocess
import time
import streamlit as st
import html
from typing import Optional, List
from .log import logger

PAUSE_BEFORE_RELOADING = 2


def run_git_command(
    command: List[str],
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
    timeout: int = 30,
) -> str:
    """
    Helper function to run git commands and capture output

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
    """
    Validate git environment and repository configuration

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
    """
    Sanitize git command output to prevent potential XSS

    Args:
        output (str): Raw git command output

    Returns:
        str: Sanitized output
    """
    return html.escape(output)


def get_remote_changes(branch: str = "main") -> Optional[str]:
    """
    Retrieve remote changes for the specified branch

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
    """
    Update Python dependencies if requirements.txt has changed

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


def check_for_updates(branch: str = "main"):
    """
    Check for and potentially apply updates to the application

    Args:
        branch (str): Branch to check for updates
    """
    # Validate git environment first
    if not validate_git_environment():
        return

    try:
        # Fetch the latest changes from the remote repository
        logger.info("Checking for updates: Fetching latest changes")
        try:
            fetch_output = run_git_command(["git", "fetch"], timeout=10)
            if fetch_output:
                logger.debug(f"Fetch output: {fetch_output}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Fetch errors: {e.stderr}")

        # Check if there are any changes
        logger.info(f"Checking current git status for branch: {branch}")
        try:
            status_output = run_git_command(
                ["git", "status", "-uno", f"HEAD..origin/{branch}"]
            )
        except subprocess.CalledProcessError:
            st.error(f"Failed to check status for branch: {branch}")
            return

        if "Your branch is behind" in status_output:
            logger.info("Update available: Branch is behind remote")

            # Retrieve and display changes
            commits_diff = get_remote_changes(branch)

            try:
                code_diff = run_git_command(["git", "diff", "HEAD..origin/main"])
            except subprocess.CalledProcessError:
                code_diff = None

            # Create a container for update information
            with st.container():
                st.subheader("Update Available")

                # Display commits if available
                if commits_diff:
                    st.subheader("Pending Commits:")
                    for commit in commits_diff.split("\n"):
                        st.text(sanitize_git_output(commit))

                # Display code changes if available
                if code_diff:
                    st.subheader("Code Changes:")
                    st.code(sanitize_git_output(code_diff), language="diff")

                # Confirmation for update with more explicit UI
                update_confirmed = st.checkbox(
                    "I understand and want to update the application"
                )

                if update_confirmed:
                    update_button = st.button("Confirm Update", type="primary")

                    if update_button:
                        try:
                            logger.info("Initiating update process")

                            # Pull the latest changes
                            pull_result = run_git_command(
                                ["git", "pull"], capture_output=True, check=False
                            )

                            # Log and display pull result
                            if pull_result:
                                logger.info(f"Pull output: {pull_result}")
                                st.text(f"Pull details: {pull_result}")

                            # Check for dependency updates
                            dependencies_updated = update_dependencies()
                            if dependencies_updated:
                                st.success("Dependencies updated successfully")

                            # Verify update status
                            pull_status = run_git_command(
                                ["git", "status", "-uno"],
                                capture_output=True,
                                check=False,
                            )

                            if "Your branch is up to date" in pull_status:
                                logger.info("Update successful")

                                # Explicit rerun confirmation
                                rerun_confirmed = st.button("Restart Application")
                                if rerun_confirmed:
                                    st.success("Restarting app...")
                                    time.sleep(PAUSE_BEFORE_RELOADING)
                                    st.rerun()
                            else:
                                logger.error("Update may have failed")
                                st.error(
                                    "Update may have failed. Please check manually."
                                )

                        except Exception as pull_error:
                            logger.exception(
                                f"Unexpected error during update: {pull_error}"
                            )
                            st.error(f"Update failed: {str(pull_error)}")
        else:
            logger.info("App is up to date")
            st.info("App is up to date")

    except Exception as e:
        logger.exception(f"Unexpected error in update check: {e}")
        st.error(f"Error checking for updates: {str(e)}")
