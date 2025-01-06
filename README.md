# RockTalk: A ChatBot WebApp with Streamlit, LangChain, and Amazon Bedrock

[![Python 3.8-3.12](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## Project Overview

This project implements RockTalk, a ChatGPT-like chatbot webapp using Streamlit for the frontend, LangChain for the logic, and Amazon Bedrock as the backend. The webapp provides a user-friendly interface for interacting with various Language Models (LLMs) with advanced features for customization and data input.

## Key Features

- 💬 Real-time chat with streaming responses and interactive controls
- 🔍 Powerful search across chat history and session metadata
- 📝 Customizable templates for different use cases
- 🖼️ Support for text and image inputs
- 📚 Complete session management with import/export
- ⚙️ Fine-grained control over LLM parameters

## Technology Stack

- Frontend: Streamlit
- Backend: Amazon Bedrock
- Logic/Integration: LangChain
- Storage: SQLite

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
   - Search within chat history, keyword, date window, title, and contents search support

2. Multiple session management ✅
   - Create new sessions
   - Switch between existing sessions, active session at top
   - Delete sessions
   - Automatic session naming, and can regenerate session title on-demand
   - Duplicate sessions
   - Rename sessions
   - Export/Import sessions

3. Chat Templates ✅
   - Create templates from existing sessions
   - Save and load predefined configurations
   - Custom template naming and descriptions
   - Share configurations across sessions
   - Manage template library
   - Import/Export templates

4. Edit previous chat messages within a session ✅
   - Edit any user message in history
   - Automatic regeneration of subsequent response (destroys original chat history after the user message)
   - Stop and modify streaming responses

5. Customizable LLM settings ✅
   - Adjust model parameters (temperature, top_p, etc.)
   - Model selection
   - System prompt customization
   - Save configurations as templates

6. Support for multiple input types
   - Text input ✅
   - Image input ✅
   - PDF documents ⏳
   - Folder structures ⏳
   - ZIP files ⏳
   - Web links / Internet access ⏳
   - Additional connectors (e.g., databases, APIs) ⏳

## Requirements

- Python 3.8-3.12
- AWS Account with Bedrock model access
- Supported models: Claude, Titan, etc.

## Getting Started

To set up and run RockTalk locally, follow these steps:

1. Clone the repository
2. (Optional) Create python environment
   - `conda create -n rock 'python<3.11'
3. Install python requirements
   - `pip install -r requirements.txt`
4. (Optional) Disable Streamlit telemetry:
   - To disable Streamlit's usage statistics collection, run the following command:
5. (Optional) Disable Streamlit telemetry:
   - To disable Streamlit's usage statistics collection, create or edit the Streamlit configuration file:
     - On Linux/macOS: `~/.streamlit/config.toml`
     - On Windows: `%UserProfile%\.streamlit\config.toml`
   - Add the following line to the file:

     ```toml
     [browser]
     gatherUsageStats = false
     ```

6. Configure AWS credentials:
   - Set up your AWS credentials for accessing Amazon Bedrock. You can do this by configuring the AWS CLI or setting environment variables.
   1. Will attempt to use default profile from your ~/.aws/config or ~/.aws/credentials
   2. Can override by setting up environment variables:
      - Create a `.env` file in the project root directory.
      - Add necessary environment variables (e.g., AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION).
7. Run the application:
   - Start the Streamlit app by running:

     ```sh
     streamlit run app.py
     ```

8. Access the webapp:
   - Open your web browser and navigate to `http://localhost:8501` to interact with RockTalk.

Note: Make sure you have the necessary permissions and budget and access to Amazon Bedrock before running the application.

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
