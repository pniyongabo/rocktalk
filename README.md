# RockTalk: A ChatBot WebApp with Streamlit, LangChain, and Amazon Bedrock

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/rocktalk)](https://pypi.org/project/rocktalk/)
[![Total Downloads](https://static.pepy.tech/badge/rocktalk)](https://pepy.tech/project/rocktalk)
[![Monthly Downloads](https://img.shields.io/pypi/dm/rocktalk)](https://pypi.org/project/rocktalk/)

## Project Overview

This project implements RockTalk, a ChatGPT-like chatbot webapp using Streamlit for the frontend, LangChain for the logic, and Amazon Bedrock as the backend. The webapp provides a user-friendly interface for interacting with various Language Models (LLMs) with advanced features for customization and data input.

## Key Features

- 💬 Real-time chat with streaming responses and interactive controls
- 🔍 Powerful search across chat history and session metadata
- 📝 Customizable templates for different use cases
- 🖼️ Support for text and image inputs
- 📚 Complete session management with import/export
- ⚙️ Fine-grained control over LLM parameters

## Table of Contents

- [RockTalk: A ChatBot WebApp with Streamlit, LangChain, and Amazon Bedrock](#rocktalk-a-chatbot-webapp-with-streamlit-langchain-and-amazon-bedrock)
  - [Project Overview](#project-overview)
  - [Key Features](#key-features)
  - [Table of Contents](#table-of-contents)
  - [Technology Stack](#technology-stack)
  - [Storage](#storage)
  - [Chat Templates](#chat-templates)
  - [Implementation Status](#implementation-status)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Getting Started](#getting-started)
  - [Usage](#usage)
    - [Starting a New Chat](#starting-a-new-chat)
    - [Managing Sessions](#managing-sessions)
    - [Working with Templates](#working-with-templates)
    - [Search Features](#search-features)
    - [Keyboard Shortcuts](#keyboard-shortcuts)
  - [Troubleshooting (TBD)](#troubleshooting-tbd)
  - [Contributing](#contributing)
  - [License](#license)


## Technology Stack

- Frontend: Streamlit
- Backend: Amazon Bedrock
- Logic/Integration: LangChain
- Storage: SQLite

## Storage

The storage interface is designed to be extensible for future additional storage options. The storage engine interface:

- Stores all chat sessions, messages, and templates
- Supports full-text search and complex queries

That said, SQLite is currently the only supported storage implementation. By default:

- Chat database is stored in `chat_database.db` in the project root directory. This file is auto-generated with preset templates and necessary tables to meet the interface requirements. The database file can be deleted it at any time and it will be regenerated.
- The database contents can be modified manually using any SQLite editing tool (e.g. SQLite3 Editor extension in VS Code). This can be useful for debugging application issues or just to see how your data is stored.
- *Security Note: While default database file permissions restrict access to just the current user (read/write only), the database file itself is not encrypted. Exercise caution with sensitive information as the contents remain readable if the file is accessed.*

## Chat Templates

RockTalk implements a flexible template system that allows users to save and reuse chat configurations. Templates include:

- **Configuration Persistence**: Save complete LLM configurations including model parameters, system prompts, and other settings
- **Template Management**:
  - Create templates from successful chat sessions
  - Save frequently used configurations
  - Import/Export templates for sharing
  - Duplicate and modify existing templates
- **Easy Application**:
  - Apply templates to new sessions
  - Quick-start conversations with predefined settings
  - Consistent experience across multiple chats
- **Template Metadata**:
  - Custom names and descriptions
  - Unique template IDs for tracking
  - Configuration versioning
- **Use Cases**:
  - Specialized chat personas
  - Task-specific configurations
  - Team-wide standardized settings
  - Experimental configurations

## Implementation Status

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

## Features

✅ = Implemented | 🚧 = In Progress | ⏳ = Planned

1. Contextual chat with session history ✅
   - Full chat history persistence
   - Stream responses with stop/edit capability
   - Copy message functionality
   - "Trim History" option to remove all session messages after selected message.

2. Advanced search capabilities:
     - Keyword search across all sessions and messages
     - Filter by titles and/or content
     - Date range filtering
     - Configurable search logic (match ALL terms or ANY term)
     - Batch operations on search results:
       - Select all/clear selections
       - Export multiple sessions
       - Bulk visibility toggle (show/hide from session list)
       - Batch delete with confirmation
     - Rich search results:
       - Message previews with search term context
       - Quick access to session settings and chat
       - Session metadata (last active, visibility status)
     - Search result actions:
       - Load session
       - Export session
       - Access session settings
     - Support for wildcard searches using *

3. Comprehensive Session Management ✅
   - Session Organization:
     - Active session pinned at top of sidebar
     - Chronologically grouped session history (Today, Yesterday, This Week, etc.)
     - Session visibility control (hide from list while maintaining searchability)
   - Session Creation and Navigation:
     - Quick new chat creation
     - Create from template option
     - Seamless session switching
     - Automatic session persistence
   - Session Customization:
     - Auto-generated descriptive titles
     - AI-powered title regeneration
     - Manual title editing
     - Template-based configuration
     - Individual session settings
     - Visibility control
   - Session Management:
     - Copy sessions to new session with options:
       - Copy messages and/or settings
       - Custom naming
     - Import/Export capabilities:
       - Single session export
       - Bulk session export
       - JSON format for portability
     - Session cleanup:
       - Individual session deletion
       - Automatic cleanup of related messages

4. Chat Templates ✅
   - Create templates from existing sessions
   - Save and load predefined configurations
   - Custom template naming and descriptions
   - Share configurations across sessions
   - Manage template library
   - Import/Export templates

5. Edit previous chat messages within a session ✅
   - Edit any user message in history
   - Automatic regeneration of subsequent response (destroys original chat history after the user message)
   - Stop and modify streaming responses

6. Customizable LLM settings ✅
   - Adjust model parameters (temperature, top_p, etc.)
   - Model selection
   - System prompt customization
   - Save configurations as templates

7. Support for multiple input types
   - Text input ✅
   - Image input ✅
   - PDF documents ⏳
   - Folder structures ⏳
   - ZIP files ⏳
   - Web links / Internet access ⏳
   - Additional connectors (e.g., databases, APIs) ⏳

## Requirements

- Python >=3.11 (only 3.11 tested, but >3.11 expected to work as well)
- AWS Account with Bedrock model access
- Supported models: Claude, Titan, etc.

## Getting Started

To set up and run RockTalk locally, follow these steps:

1. Clone the repository
   - `git clone https://github.com/tahouse/rocktalk.git && cd rocktalk`
2. (Optional) Create python environment
   - `conda create -n rock 'python=3.11'`
   - `conda activate rock`
3. Install python requirements
   - `pip install -r requirements.txt`
4. (Optional) Disable Streamlit telemetry:
   - To disable Streamlit's usage statistics collection, create or edit the Streamlit configuration file:
     - On Linux/macOS: `~/.streamlit/config.toml`
     - On Windows: `%UserProfile%\.streamlit\config.toml`
     - Add the following line to the file:

        ```toml
        [browser]
        gatherUsageStats = false
        ```

     - Or just run this in your shell (Linux/macOS)

        ```shell
        mkdir -p ~/.streamlit

        cat << 'EOF' > ~/.streamlit/config.toml
        [browser]
        gatherUsageStats = false
        EOF
        ```

5. Configure AWS credentials:
   - This application uses AWS SDK for Python (Boto3). For more information about setting up credentials, check <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>. In short, you can configure your AWS credentials using the AWS CLI or setting environment variables.
   1. RockTalk will attempt to use default profile defined in `~/.aws/config` or `~/.aws/credentials`
   2. Can override by setting up environment variables:
      - Create a `.env` file in the project root directory.
      - Add necessary environment variables (e.g., AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION).

6. Configure Bedrock Foundation Model access (if needed):
   - Make sure you have the necessary permissions and budget and access to Amazon Bedrock before running the application. You'll need to enable [Model Access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) in the AWS console for your default region (set up in your credentials/config above). By default, RockTalk tries to use `anthropic.claude-3-5-sonnet-20241022-v2:0`. This can be adjusted by modifying `ROCKTALK_DEFAULT_MODEL` in your environment (setting environment variable or adding to `.env` in the project root directory). *Note that `ROCKTALK_DEFAULT_MODEL` is only used when first initializing your preset chat templates. Once they are initialized, adjusting the default model will have no effect.*

7. Run the application:
   - Start the Streamlit app by running from the project root directory (main repository path you cloned above):

     ```sh
     streamlit run rocktalk/app.py
     ```

8. Access the webapp:
   - If it didn't open automatically, open your web browser and navigate to `http://localhost:8501` to interact with RockTalk.

## Usage

### Starting a New Chat

- Click "New Chat" in the sidebar
- Select a template (optional) or use default settings
- Start typing in the chat input box
- Use ⌘/⊞ + ⌫ to stop streaming responses

### Managing Sessions

- Switch sessions: Click any session in the sidebar
- Rename: Click the pencil icon next to session title
- Delete: Click the trash icon next to session
- Duplicate: Use the duplicate button in session settings
- Export: Download session as JSON from session settings
- Import: Upload previously exported session files

### Working with Templates

- Create template: Save current session settings as template
- Apply template: Select template when creating new chat
- Modify templates: Edit existing templates in template manager
- Share templates: Export/Import template configurations

### Search Features

- Full-text search across all chats
- Filter by date range
- Search by session title
- Search within current session
- Advanced search with multiple criteria

### Keyboard Shortcuts

- ⌘/⊞ + ⌫ : Stop streaming response
- Enter : Send message
- ⌘/⊞ + Enter : Add new line

## Troubleshooting (TBD)

- AWS credentials setup
- Common error messages
- Performance tips

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to:

- Follow the existing code style
- Update tests as appropriate
- Update documentation as needed
- Add yourself to CONTRIBUTORS.md (if you'd like)

By contributing to this project, you agree that your contributions will be licensed under the Apache License 2.0.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
