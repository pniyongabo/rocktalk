# __main__.py
import json
import logging
import os
import pathlib
import signal
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import click
from dotenv import load_dotenv


def setup_logging():
    """Configure logging for RockTalk"""
    logging.basicConfig(
        level=os.getenv("ROCKTALK_LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


logger = logging.getLogger("rocktalk")

try:
    from rocktalk.version import __version__ as VERSION
except ImportError:
    try:
        VERSION: str = version("rocktalk")
    except Exception:
        VERSION = "unknown"

# Remove the duplicate VERSION assignment
DEFAULT_STREAMLIT_ARGS: dict[str, str] = {
    "--logger.level": "info",
}

REPO_URL = "https://github.com/tahouse/rocktalk"
AUTH_DOCS_URL = "https://github.com/mkhorasani/Streamlit-Authenticator"


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    logger.info("Received interrupt signal")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def check_dependencies():
    """Verify required dependencies are available"""
    try:
        subprocess.run(["streamlit", "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        raise click.ClickException(
            "Streamlit not found. Please install streamlit package."
        )


def get_rocktalk_dir() -> Path:
    """Get path to .rocktalk directory, creating if needed"""
    try:
        # Check environment variable first, then fall back to ~/.rocktalk
        rocktalk_dir: str | None = os.getenv("ROCKTALK_DIR")
        if rocktalk_dir:
            path = Path(rocktalk_dir)
        else:
            path = Path.home() / ".rocktalk"

        path.mkdir(exist_ok=True, mode=0o700)  # Secure permissions
        (path / ".streamlit").mkdir(exist_ok=True)

        return path
    except Exception as e:
        logger.error(f"Failed to create RockTalk directory: {e}")
        raise click.ClickException("Could not create RockTalk configuration directory")


def get_firstrun_path() -> Path:
    """Get path to the first run marker file"""
    return get_rocktalk_dir() / "firstrun.json"


def setup_rocktalk_dir() -> None:
    """Set up the .rocktalk directory with default configurations"""
    rocktalk_dir = get_rocktalk_dir()

    # Create default streamlit config if it doesn't exist
    streamlit_config = rocktalk_dir / ".streamlit" / "config.toml"
    if not streamlit_config.exists():
        streamlit_config.write_text("[browser]\n" "gatherUsageStats = false\n")

    # Do not create an auth file by default, instead just tell user where to put it and reference the documentation on what it should contain


def check_first_run() -> bool:
    """Check if this is the first run for this version"""
    firstrun_path = get_firstrun_path()

    if not firstrun_path.exists():
        setup_rocktalk_dir()
        return True

    try:
        with open(firstrun_path) as f:
            data = json.load(f)
            return data.get("version") != VERSION
    except (json.JSONDecodeError, FileNotFoundError):
        return True


def show_first_run_message() -> bool:
    """Show first run welcome message"""
    rocktalk_dir = get_rocktalk_dir()

    click.secho("\nWelcome to RockTalk!", fg="green", bold=True)
    click.secho(f"Version: {VERSION}", fg="blue")
    click.secho(f"Project repository: {REPO_URL}\n", fg="blue")

    click.secho("Configuration directory:", fg="yellow")
    click.secho(f"  Using: {rocktalk_dir}")
    click.secho(
        "  Note: To use a different location, use --config-dir or $ROCKTALK_DIR (see --help)"
    )
    click.secho("\nWill create these files they don't exist:")
    click.secho("  - .streamlit/config.toml: Streamlit configuration")
    click.secho("  - chat_database.db: Chat history and templates")

    click.secho("\nAuthentication (optional):")
    click.secho(f"  Add auth.yaml to {rocktalk_dir}")
    click.secho(f"  See: {AUTH_DOCS_URL}")

    click.secho("\nQuick start:", fg="yellow")
    click.secho("  1. Ensure AWS credentials are configured")
    click.secho("  2. Enable Bedrock model access in your AWS account")
    click.secho("  3. Configure authentication in auth.yaml (optional)")

    click.secho(f"\nFor more information: {REPO_URL}\n")

    if click.confirm("Continue using this configuration directory?", default=True):
        return True
    return False


def mark_first_run() -> None:
    """Mark this version as having been run by saving version info to firstrun.json"""
    firstrun_path = get_firstrun_path()
    data: dict[str, str] = {
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(firstrun_path, "w") as f:
        json.dump(data, f, indent=2)
    logger.debug(f"Marked first run for version {VERSION}")


def get_help_text() -> str:
    """Get help text for RockTalk"""
    return f"""RockTalk v{VERSION} - A ChatGPT-like chatbot webapp powered by Amazon Bedrock

Project repository: {REPO_URL}

Options:
  --config-dir PATH  Directory for RockTalk configuration and stored chat database
                    (default: ~/.rocktalk or $ROCKTALK_DIR)

Default arguments passed to streamlit:
{chr(10).join(f"  {k} {v}" for k, v in DEFAULT_STREAMLIT_ARGS.items())}

Configuration files:
  - .streamlit/config.toml: Streamlit configuration
  - auth.yaml: Authentication configuration (optional)
  - chat_database.db: Chat history and templates

For Streamlit-specific options:
  streamlit run --help
"""


def show_help() -> None:
    """Display help text"""
    click.echo(get_help_text())


@click.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.version_option(version=VERSION, prog_name="RockTalk")
@click.option(
    "--config-dir",
    type=click.Path(
        exists=False,  # We'll create it if it doesn't exist
        file_okay=False,
        dir_okay=True,
        path_type=Path,
    ),
    help="Directory for RockTalk configuration and chat database (default: ~/.rocktalk or $ROCKTALK_DIR)",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def main(config_dir, args) -> None:
    """RockTalk - A ChatGPT-like chatbot webapp powered by Amazon Bedrock

    Project repository: https://github.com/tahouse/rocktalk

    For Streamlit-specific options: streamlit run --help
    """
    # Load environment variables from .env if present
    setup_logging()
    load_dotenv()
    check_dependencies()

    # Check for help/version flags before doing first run
    if "--help" in args or "-h" in args:
        show_help()
        sys.exit(0)
    if "--version" in args:
        click.echo(f"RockTalk v{VERSION}")
        sys.exit(0)

    try:
        # Set ROCKTALK_DIR environment variable if config-dir provided
        if config_dir:
            os.environ["ROCKTALK_DIR"] = str(config_dir)

        if check_first_run():
            if not show_first_run_message():
                sys.exit(0)
            mark_first_run()

        config_dir = get_rocktalk_dir()
        run_streamlit(config_dir=config_dir, args=args)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


def run_streamlit(config_dir, args) -> None:
    """Run the Streamlit application.

    Args:
        config_dir (Path): Path to RockTalk configuration directory
        args (tuple): Additional arguments to pass to streamlit run
    """
    # Always change to config directory
    original_dir = os.getcwd()
    os.chdir(config_dir)
    logger.info(f"Changed to RockTalk directory: {config_dir}")

    try:
        # Base command with our default settings
        cmd = [
            "streamlit",
            "run",
            f"{pathlib.Path(__file__).parent}/app.py",
        ]

        # Add our default args
        for k, v in DEFAULT_STREAMLIT_ARGS.items():
            cmd.extend([k, v])

        # Set up environment
        env = dict(os.environ)
        env["ROCKTALK_DIR"] = str(config_dir)

        # Add any additional streamlit arguments
        if args:
            cmd.extend(args)

        logger.debug(f"cmd: {cmd}")
        subprocess.run(cmd, check=True, env=env)
    except KeyboardInterrupt:
        logger.info("exit streamlit...")
    except Exception as e:
        logger.warning(f"exit, err={e}\nstack trace={traceback.format_exc(chain=True)}")
    finally:
        os.chdir(original_dir)
        logger.info(f"Restored original directory: {original_dir}")


if __name__ == "__main__":
    main()
