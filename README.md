# Reddit RAG Chatbot

## Description

The Reddit RAG Chatbot is a Python application that allows users to scrape content from a specified Reddit subreddit, index this data, and then chat with an AI agent that uses this scraped content as a knowledge base. This is achieved using a Retrieval Augmented Generation (RAG) pipeline. The user interface is built with [Flet](https://flet.dev/), a framework for creating interactive multi-user web, desktop, and mobile applications in Python.

The application features an initial setup screen for users to input necessary API keys, which are then stored locally in a `.env` file for subsequent sessions.

## Heres How it looks like!
![image](https://github.com/user-attachments/assets/d3bebac2-fbf4-4a67-9d21-0fe03cdcdfb5)
![image](https://github.com/user-attachments/assets/a4fc617b-22cf-444e-8c39-3a0a53fc8c92)


## Features

*   **Subreddit Scraping**: Fetch posts (titles, self-text, comments) from any public subreddit.
*   **Customizable Scraping**: Users can specify the subreddit name, time filter (e.g., "day", "week", "all"), and the maximum number of posts to retrieve.
*   **Data Indexing**: Scraped text data is processed and indexed into a vector store using LangChain and Google's embedding models.
*   **Retrieval Augmented Generation (RAG)**: The chatbot uses the indexed Reddit data to provide contextually relevant answers to user queries.
*   **Interactive Chat Interface**: A user-friendly chat UI built with Flet.
*   **API Key Management**: An initial setup screen for users to securely enter their API keys for Google and Reddit.
*   **Dynamic Status Updates**: The UI provides feedback on ongoing processes like scraping, indexing, and chatbot responses.

## Tech Stack

*   **Python**: Core programming language.
*   **Flet**: For building the interactive desktop/web user interface.
*   **PRAW (Python Reddit API Wrapper)**: For interacting with the Reddit API to scrape data.
*   **LangChain**: Framework for building RAG applications, including document loading, splitting, embedding, and vector store management.
*   **Google Generative AI SDK (`google-generativeai`)**: For accessing Google's embedding models (e.g., `text-embedding-004`) and generative models for the chat agent (e.g., Gemini family).
*   **`python-dotenv`**: For managing environment variables (API keys) from a `.env` file.
*   **ADK (Agent Development Kit)**: Utilized for the chatbot's session management and interaction logic (as per `adk_chatbot.py`).

## Project Structure (Illustrative)
reddit_automation_agents/
├── main.py # Main Flet application, UI logic, view management
├── config.py # Application configuration (default subreddit, model names, etc.)
├── ui_utils.py # UI helper functions (status updates, control management)
├── reddit_utils.py # Functions for scraping Reddit using PRAW
├── rag_handler.py # Functions for LangChain RAG pipeline (indexing, retrieval)
├── adk_chatbot.py # Chatbot logic, interaction with ADK/generative models
├── requirements.txt # Python dependencies
├── .env.example # Example environment file
└── ... (other potential helper modules or assets)


## Setup and Installation

1.  **Clone the Repository**:
    ```bash
    git clone Reddit_RAG_Chatbot
    cd Reddit_RAG_Chatbot
    ```

2.  **Create a Python Virtual Environment**:
    (Recommended to avoid conflicts with global packages)
    ```bash
    python -m venv .venv
    ```
    Activate the environment:
    *   Windows: `.venv\Scripts\activate`
    *   macOS/Linux: `source .venv/bin/activate`

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables**:
    The application requires API keys for Google Cloud (for Generative AI models) and Reddit.
    *   If you run the application for the first time without a `.env` file or pre-configured system environment variables, it should present you with an API key entry screen.
    *   Alternatively, you can create a `.env` file in the project root directory (`reddit_automation_agents/`) by copying `.env.example` (if you create one) or by creating it manually.

    Your `.env` file should look like this:
    ```env
    GOOGLE_API_KEY="your_google_api_key_here"
    REDDIT_CLIENT_ID="your_reddit_client_id_here"
    REDDIT_CLIENT_SECRET="your_reddit_client_secret_here"
    REDDIT_USER_AGENT="your_reddit_user_agent_string_here" # e.g., "Python:RedditScraperApp:v1.0 (by u/yourusername)"
    ```
    *   **Google API Key**: Obtain from [Google AI Studio](https://aistudio.google.com/app/apikey) or Google Cloud Console.
    *   **Reddit API Credentials**: Create a "script" app on Reddit's [app preferences page](https://www.reddit.com/prefs/apps). The "client ID" is under the app name, and the "client secret" is also provided there. The `REDDIT_USER_AGENT` should be a unique string describing your script, including your Reddit username if possible.

## Usage

1.  Ensure your virtual environment is activated.
2.  Run the application:
    ```bash
    python main.py
    ```
3.  **API Key Entry (First Run)**: If API keys are not found, an initial screen will prompt you to enter them. These will be saved to a local `.env` file in the project directory.
4.  **Main Application**:
    *   Enter a **Subreddit Name** you want to scrape.
    *   Select a **Time Filter** (e.g., "day", "week", "all").
    *   Enter the **Post Limit** (number of posts to fetch).
    *   Click **"Scrape & Index"**. The application will fetch data from Reddit, process it, and build the knowledge base. Status updates will be shown.
    *   Once indexing is complete and the chatbot is initialized ("Ready to chat!"), you can type your questions into the "Ask the chatbot..." field and press Enter or click the send button.

## Configuration (`config.py`)

The `config.py` file contains default settings and model configurations:

*   `DEFAULT_SUBREDDIT`: The subreddit that appears by default in the input field.
*   `DEFAULT_TIME_FILTER`: Default time filter for scraping.
*   `DEFAULT_LIMIT`: Default number of posts to scrape.
*   `PARENT_CHUNK_SIZE`, `PARENT_CHUNK_OVERLAP`, `CHILD_CHUNK_SIZE`, `CHILD_CHUNK_OVERLAP`: Settings for LangChain's Parent Document Retriever.
*   `EMBEDDING_MODEL`: Name of the Google embedding model to use.
*   `ADK_AGENT_MODEL`: Name of the Google generative model used by the chatbot.
*   Paths for the `.env` file discovery.


## Potential Future Enhancements

*   More robust error handling and user feedback.
*   Option to choose different embedding or chat models from the UI.
*   Persistent storage for indexed data to avoid re-scraping/re-indexing on every run.
*   Ability to manage multiple subreddit indexes.
*   Improved UI styling and responsiveness.
*   Address all `DeprecationWarning`s by updating to the latest Flet API for colors, icons, etc.

---
