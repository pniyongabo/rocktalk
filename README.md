# RockTalk: A ChatBot WebApp with Streamlit, LangChain, and Amazon Bedrock

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/rocktalk)](https://pypi.org/project/rocktalk/)
[![Total Downloads](https://static.pepy.tech/badge/rocktalk)](https://pepy.tech/project/rocktalk)
[![Monthly Downloads](https://img.shields.io/pypi/dm/rocktalk)](https://pypi.org/project/rocktalk/)

## Table of Contents

- [RockTalk: A ChatBot WebApp with Streamlit, LangChain, and Amazon Bedrock](#rocktalk-a-chatbot-webapp-with-streamlit-langchain-and-amazon-bedrock)
  - [Table of Contents](#table-of-contents)
  - [Project Overview](#project-overview)
  - [Key Features](#key-features)
  - [Getting Started](#getting-started)
    - [Requirements](#requirements)
    - [Quick Start (Recommended)](#quick-start-recommended)
  - [Usage](#usage)
    - [Starting a New Chat](#starting-a-new-chat)
    - [Managing Sessions](#managing-sessions)
    - [Working with Templates](#working-with-templates)
    - [Search Features](#search-features)
    - [Keyboard Shortcuts](#keyboard-shortcuts)
  - [Troubleshooting](#troubleshooting)
  - [Advanced Setup](#advanced-setup)
    - [File Locations](#file-locations)
    - [Environment Variables](#environment-variables)
  - [Development Details](#development-details)
    - [Technology Stack](#technology-stack)
    - [Storage](#storage)
    - [Chat Templates](#chat-templates)
    - [Implementation Status](#implementation-status)
    - [Features](#features)
    - [Development Setup](#development-setup)
  - [Contributing](#contributing)
  - [License](#license)

## Project Overview

This project implements RockTalk, a ChatGPT-like chatbot webapp using Streamlit for the frontend, LangChain for the logic, and Amazon Bedrock as the backend. The webapp provides a user-friendly interface for interacting with various Language Models (LLMs) with advanced features for customization and data input.

## Key Features

- 💬 Real-time chat with streaming responses and interactive controls
- 🔍 Powerful search across chat history and session metadata
- 📝 Customizable templates for different use cases
- 🖼️ Support for text and image inputs
- 📚 Complete session management with import/export
- ⏳ Temporary sessions for quick, unsaved interactions
- ⚙️ Fine-grained control over LLM parameters

## Getting Started

### Requirements

- Python >=3.11 (only 3.11 tested, but >3.11 expected to work as well)
- AWS Account with Bedrock model access
- Supported models: Claude, Titan, etc.

### Quick Start (Recommended)

1. Install RockTalk using pip:

   ```sh
   pip install rocktalk
   ```

2. Configure AWS credentials:
   - RockTalk uses AWS SDK for Python (Boto3). Configure credentials via:
     - AWS CLI configuration
     - Environment variables
     - For more details, see: <https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html>

3. Configure Bedrock Foundation Model access:
   - Enable [Model Access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) in AWS console
   - Default model: `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - Override default by setting `ROCKTALK_DEFAULT_MODEL` environment variable

4. Start RockTalk:

   ```sh
   rocktalk
   ```

5. Access the webapp at <http://localhost:8501>

## Usage

### Starting a New Chat

- **New Chat**: Click "New +" in the sidebar to start a new chat session. This session will be saved automatically.
- **New Temporary Chat**: Click <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/tahouse/rocktalk/main/docs/assets/history_toggle_off_light.svg">
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/tahouse/rocktalk/main/docs/assets/history_toggle_off_dark.svg">
      <img alt='history_toggle_off' src="https://raw.githubusercontent.com/tahouse/rocktalk/main/docs/assets/history_toggle_off_dark.svg" width="12">
    </picture> (temporary session) in the sidebar to start a temporary chat session that will not be saved unless you choose to save it. These are ideal for spontaneous conversations where you might not need to keep a record.
  - **Saving a Temporary Session**:
    - If you wish to save a temporary session, click "Save Temporary Session" in the sidebar.
    - Provide a session title and confirm. You can use LLM to auto-generate a title.
    - The session will then be saved to your session history and managed like any other session.
- **New Chat with Template**: Click <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/tahouse/rocktalk/main/docs/assets/playlist_add_light.svg">
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/tahouse/rocktalk/main/docs/assets/playlist_add_dark.svg">
      <img alt='playlist_add' src="https://raw.githubusercontent.com/tahouse/rocktalk/main/docs/assets/playlist_add_dark.svg" width="12">
    </picture> (quick template selector) to use a specific template when creating a new chat or temporary chat.
- Start typing in the chat input box.
- Use ⌘/⊞ + ⌫ to stop streaming responses.

### Managing Sessions

- **Switch sessions**: Click any session in the sidebar.
- **Rename**: Click the pencil icon next to session title.
- **Delete**: Click the trash icon next to session.
- **Duplicate**: Use the duplicate button in session settings.
- **Export**: Download session as JSON from session settings.
- **Import**: Upload previously exported session files.
- **Saving Temporary Sessions**: Temporary sessions can be saved at any time by clicking "Save Temporary Session" in the sidebar.

### Working with Templates

- **Create template**: Save current session settings as template.
- **Apply template**: Select template when creating new chat.
- **Modify templates**: Edit existing templates in template manager.
- **Share templates**: Export/Import template configurations.

### Search Features

- Full-text search across all chats.
- Filter by date range.
- Search by session title.
- Search within current session.
- Advanced search with multiple criteria.

### Keyboard Shortcuts

- ⌘/⊞ + ⌫ : Stop streaming response.
- Enter : Send message.
- ⌘/⊞ + Enter : Add new line.

## Troubleshooting

- AWS credentials setup.
- Common error messages.
- Performance tips.
- **Logging:**
  - Set `ROCKTALK_LOG_LEVEL=DEBUG` for detailed logging.
  - Logs are stored in `~/.rocktalk/logs/rocktalk.log`.
  - View logs in the application settings panel.

## Advanced Setup

### File Locations

RockTalk stores its data in the following locations:

- Main configuration directory: `~/.rocktalk/`
- Database file: `~/.rocktalk/chat_database.db`
- Log files: `~/.rocktalk/logs/`
- Environment file (optional): `~/.rocktalk/.env`

### Environment Variables

RockTalk can be configured using the following environment variables:

- `ROCKTALK_DIR`: Main configuration directory (default: `~/.rocktalk/`)
- `ROCKTALK_DEFAULT_MODEL`: Override default Bedrock model
- `ROCKTALK_LOG_LEVEL`: Set logging level (default: "INFO")
  - Available levels: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
  - DEBUG: Detailed information for debugging
  - INFO: General operational information
  - WARNING: Warning messages for potential issues
  - ERROR: Error messages for serious problems
  - CRITICAL: Critical errors that may prevent operation

## Development Details

### Technology Stack

- Frontend: Streamlit
- Backend: Amazon Bedrock
- Logic/Integration: LangChain
- Storage: SQLite

### Storage

The storage interface is designed to be extensible for future additional storage options. The storage engine interface:

- Stores all chat sessions, messages, and templates.
- Supports full-text search and complex queries.

By default:

- Chat database is stored in `chat_database.db` in the project root directory `~/.rocktalk`. This file is auto-generated with preset templates and necessary tables to meet the interface requirements. The database file can be deleted at any time and it will be regenerated.
- The database contents can be modified manually using any SQLite editing tool (e.g., SQLite3 Editor extension in VS Code). This can be useful for debugging application issues or just to see how your data is stored.
- **Security Note**: While default database file permissions restrict access to just the current user (read/write only), the database file itself is not encrypted. Exercise caution with sensitive information as the contents remain readable if the file is accessed.

### Chat Templates

RockTalk implements a flexible template system that allows users to save and reuse chat configurations. Templates include:

- **Configuration Persistence**: Save complete LLM configurations including model parameters, system prompts, and other settings.
- **Template Management**:
  - Create templates from successful chat sessions.
  - Save frequently used configurations.
  - Import/Export templates for sharing.
  - Duplicate and modify existing templates.
- **Easy Application**:
  - Apply templates to new sessions.
  - Quick-start conversations with predefined settings.
  - Consistent experience across multiple chats.
- **Template Metadata**:
  - Custom names and descriptions.
  - Unique template IDs for tracking.
  - Configuration versioning.
- **Use Cases**:
  - Specialized chat personas.
  - Task-specific configurations.
  - Team-wide standardized settings.
  - Experimental configurations.

### Implementation Status

1. ✅ Set up the development environment
2. ✅ Create the basic Streamlit interface for RockTalk
3. ✅ Integrate LangChain with Bedrock backend
4. ✅ Implement core chat functionality
5. ✅ Add session management features
6. ✅ Develop LLM settings customization
7. 🚧 Integrate support for various input types
8. ✅ Implement advanced features (editing, multiple sessions)
9. 🚧 Optimize performance and user experience
10. 🚧 Test and debug
11. ⏳ Deploy RockTalk webapp

### Features

✅ = Implemented | 🚧 = In Progress | ⏳ = Planned

1. Contextual chat with session history ✅
   - Full chat history persistence.
   - Stream responses with stop/edit capability.
   - Copy message functionality.
   - "Trim History" option to remove all session messages after selected message.

2. Advanced search capabilities:
     - Keyword search across all sessions and messages.
     - Filter by titles and/or content.
     - Date range filtering.
     - Configurable search logic (match ALL terms or ANY term).
     - Batch operations on search results:
       - Select all/clear selections.
       - Export multiple sessions.
       - Bulk visibility toggle (show/hide from session list).
       - Batch delete with confirmation.
     - Rich search results:
       - Message previews with search term context.
       - Quick access to session settings and chat.
       - Session metadata (last active, visibility status).
     - Search result actions:
       - Load session.
       - Export session.
       - Access session settings.
     - Support for wildcard searches using *.

3. Comprehensive Session Management ✅
   - Session Organization:
     - Active session pinned at top of sidebar.
     - Chronologically grouped session history (Today, Yesterday, This Week, etc.).
     - Session visibility control (hide from list while maintaining searchability).
     - **Temporary Sessions**:
       - Ability to create sessions that are not saved by default.
       - Option to save temporary sessions if needed.
   - Session Creation and Navigation:
     - Quick new chat creation.
     - Create from template option.
     - Seamless session switching.
     - Automatic session persistence.
   - Session Customization:
     - Auto-generated descriptive titles.
     - AI-powered title regeneration.
     - Manual title editing.
     - Template-based configuration.
     - Individual session settings.
     - Visibility control.
   - Session Management:
     - Copy sessions to new session with options:
       - Copy messages and/or settings.
       - Custom naming.
     - Import/Export capabilities:
       - Single session export.
       - Bulk session export.
       - JSON format for portability.
     - Session cleanup:
       - Individual session deletion.
       - Automatic cleanup of related messages.

4. Chat Templates ✅
   - Create templates from existing sessions.
   - Save and load predefined configurations.
   - Custom template naming and descriptions.
   - Share configurations across sessions.
   - Manage template library.
   - Import/Export templates.

5. Edit previous chat messages within a session ✅
   - Edit any user message in history.
   - Automatic regeneration of subsequent response (destroys original chat history after the user message).
   - Stop and modify streaming responses.

6. Customizable LLM settings ✅
   - Adjust model parameters (temperature, top_p, etc.).
   - Model selection.
   - System prompt customization.
   - Save configurations as templates.

7. Support for multiple input types
   - Text input ✅
   - Image input ✅
   - PDF documents ⏳
   - Folder structures ⏳
   - ZIP files ⏳
   - Web links / Internet access ⏳
   - Additional connectors (e.g., databases, APIs) ⏳

### Development Setup

If you want to contribute to RockTalk development:

1. Clone the repository:

   ```sh
   git clone https://github.com/tahouse/rocktalk.git
   cd rocktalk
   ```

2. Create a Python environment (optional):

   ```sh
   conda create -n rock 'python=3.11'
   conda activate rock
   ```

3. Install development dependencies:

   ```sh
   pip install -e ".[dev]"
   ```

4. Install pre-commit hooks:

   ```sh
   pre-commit install
   ```

5. Run the development version:

   ```sh
   streamlit run rocktalk/app.py
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to:

- Follow the existing code style.
- Update tests as appropriate.
- Update documentation as needed.
- Add yourself to CONTRIBUTORS.md (if you'd like).

By contributing to this project, you agree that your contributions will be licensed under the Apache License 2.0.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
