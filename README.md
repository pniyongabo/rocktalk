# RockTalk: A ChatBot WebApp with Streamlit, LangChain, and Bedrock

## Project Overview

This project aims to create RockTalk, a ChatGPT-like chatbot webapp using Streamlit for the frontend, LangChain for the logic, and Amazon Bedrock as the backend. The webapp will provide a user-friendly interface for interacting with various Language Models (LLMs) and offer advanced features for customization and data input.

## Planned Features

1. Contextual chat with session history
2. Multiple session management
   - Create new sessions
   - Switch between existing sessions
   - Delete sessions
3. Edit previous chat messages within a session
4. Customizable LLM settings
   - Adjust context window size
   - Set number of output tokens
5. Support for multiple input types:
   - Text input
   - PDF documents
   - Folder structures
   - ZIP files
   - Web links / Internet access
   - Additional connectors (e.g., databases, APIs)

## Technology Stack

- Frontend: Streamlit
- Backend: Amazon Bedrock
- Logic/Integration: LangChain

## Implementation Plan

1. Set up the development environment
2. Create the basic Streamlit interface for RockTalk
3. Integrate LangChain with Bedrock backend
4. Implement core chat functionality
5. Add session management features
6. Develop LLM settings customization
7. Integrate support for various input types
8. Implement advanced features (editing, multiple sessions)
9. Optimize performance and user experience
10. Test and debug
11. Deploy RockTalk webapp

## Getting Started

To set up and run RockTalk locally, follow these steps:

1. Clone the repository
2. (Optional) Create python environment
   - `conda create -n rock 'python<3.11'
3. Install python requirements
   - `pip install -r requirements.txt`
4. (Optional) Disable Streamlit telemetry:
   - To disable Streamlit's usage statistics collection, run the following command:
4. (Optional) Disable Streamlit telemetry:
   - To disable Streamlit's usage statistics collection, create or edit the Streamlit configuration file:
     - On Linux/macOS: `~/.streamlit/config.toml`
     - On Windows: `%UserProfile%\.streamlit\config.toml`
   - Add the following line to the file:
     ```toml
     [browser]
     gatherUsageStats = false
     ```
5. Configure AWS credentials:
   - Set up your AWS credentials for accessing Amazon Bedrock. You can do this by configuring the AWS CLI or setting environment variables.
6. Set up environment variables:
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

## Contributing

(Guidelines for contributing to the RockTalk project)
