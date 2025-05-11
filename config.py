# config.py
"""
Stores configuration constants for the Reddit RAG Chatbot application.
"""

# --- Application Settings ---
APP_NAME = "RedditRAGChatbotApp"

# --- Reddit Scraper Settings ---
DEFAULT_SUBREDDIT = "wallstreetbets"
DEFAULT_TIME_FILTER = "day" # Shorter filter for faster testing/updates
DEFAULT_LIMIT = 1000        # Smaller limit for faster testing/updates

# --- LangChain Parent Document Retriever Settings ---
PARENT_CHUNK_SIZE = 2000
PARENT_CHUNK_OVERLAP = 200
CHILD_CHUNK_SIZE = 400
CHILD_CHUNK_OVERLAP = 50

# --- Model Settings ---
# Ensure the embedding model name matches the expected dimensions (e.g., 768 for text-embedding-004)
EMBEDDING_MODEL = 'models/text-embedding-004'
# Model used for the ADK agent's reasoning and response generation
ADK_AGENT_MODEL = 'gemini-2.5-flash-preview-04-17' 

# --- ADK Settings ---
ADK_USER_ID = "flet_chat_user"

# --- File Paths ---
# Assumes .env is in the same directory as main_app.py or one level up
DOTENV_PATH_SCRIPT_DIR = ".env"
DOTENV_PATH_PARENT_DIR = "../.env"

# Note: API Keys (GOOGLE_API_KEY, REDDIT_CLIENT_ID, etc.) should be loaded
# from the .env file or environment variables, not hardcoded here.
