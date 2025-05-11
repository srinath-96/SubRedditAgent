# adk_chatbot.py
"""
Handles ADK Agent initialization and processing chat turns.
Assumes the session is created externally before handle_adk_chat_turn is called.
"""
import traceback
import asyncio

# ADK Imports
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types as adk_types

# Import config and the retrieval tool function
import config as cfg
# Import the rag_handler module to access its state and tool function
import rag_handler
# from rag_handler import retrieve_context_parent_retriever_tool # Keep this specific import for the tool

# --- Global ADK Variables ---
adk_rag_agent = None
adk_runner = None
adk_session_service = None # This service instance is used by the runner

def initialize_adk_chatbot(log_callback):
    """Initializes the ADK Agent, Runner, and Session Service."""
    global adk_rag_agent, adk_runner, adk_session_service

    # Reset previous instances if re-initializing
    adk_rag_agent = None
    adk_runner = None
    adk_session_service = None

    log_callback("Initializing ADK chatbot components...")

    # 1. Check if retriever (and thus index) is ready
    # --- CORRECTED CHECK: Access the variable via the module ---
    if rag_handler.lc_retriever is None:
    # --- END CORRECTION ---
         log_callback("Error: RAG Retriever (in rag_handler) is not initialized. Cannot create agent.")
         return False

    # 2. Define Agent Instruction
    rag_agent_instruction = """You are a helpful chatbot answering questions about specific Reddit posts. Your task is to answer user questions based *only* on the context provided by the 'retrieve_context_parent_retriever_tool' function. Follow these steps precisely:
1.  When you receive a user query, analyze if you need external information from the Reddit posts. If yes, call the 'retrieve_context_parent_retriever_tool' function with the user query to find relevant information. If the question is conversational (e.g. "hello", "how are you?") or clearly follows up on previous context/answers, you might not need the tool. Use the tool if the user asks about specific topics, posts, or summaries related to the Reddit data.
2.  Examine the result from the tool if called. The 'context' field contains relevant information chunks.
3.  If the tool was called and returned context (status 'success', context not empty), synthesize an answer based *solely* on that retrieved context AND the conversation history. Start your response with: "Based on the retrieved context: ".
4.  If the tool was called and returned no relevant context, respond *exactly* with: "I couldn't find specific information about that in the indexed Reddit posts."
5.  If the tool was not called (e.g., for a conversational query or direct follow-up), answer naturally based on the conversation history.
6.  Do not use your general knowledge for questions that seem to ask about the Reddit data
7. Use General Knowledge to answer questions that are not related to the Reddit data.

"""
    # 3. Check if tool function is callable (using the imported function directly)
    if not callable(rag_handler.retrieve_context_parent_retriever_tool):
        log_callback("Error: Retrieval tool function (in rag_handler) is not callable.")
        return False

    # 4. Create Agent
    try:
        adk_rag_agent = Agent(
            name="reddit_rag_chat_agent_v1",
            model=cfg.ADK_AGENT_MODEL,
            description="Chatbot that uses RAG (ParentDocumentRetriever) over scraped Reddit data.",
            instruction=rag_agent_instruction,
            tools=[rag_handler.retrieve_context_parent_retriever_tool], # Pass the function directly
        )
        log_callback(f"ADK Agent '{adk_rag_agent.name}' created.")
    except Exception as e:
        log_callback(f"ERROR creating ADK Agent: {e}")
        traceback.print_exc()
        return False

    # 5. Create Session Service and Runner
    try:
        # Session service is created here and used by the runner
        adk_session_service = InMemorySessionService()
        adk_runner = Runner(
            agent=adk_rag_agent,
            app_name=cfg.APP_NAME,
            session_service=adk_session_service, # Runner holds reference to the service
        )
        log_callback("ADK Runner and Session Service initialized.")
        return True # Indicate success
    except Exception as e:
        log_callback(f"Error initializing ADK Runner/SessionService: {e}")
        traceback.print_exc()
        return False

async def handle_adk_chat_turn(session_id: str, user_query: str, log_callback):
    """
    Handles a single turn of the chat with the ADK agent.
    ASSUMES the session_id provided already exists in the adk_session_service.
    """
    global adk_runner # Runner holds the reference to the session service

    if not adk_runner: # Check runner which implies service exists too if init worked
        log_callback("Error: ADK Runner is not ready.")
        return "Error: Chatbot Runner not initialized."

    app_name = getattr(adk_runner, 'app_name', cfg.APP_NAME)
    final_response = "Agent did not provide a response."
    user_id = cfg.ADK_USER_ID # Use user ID from config

    try:
        # --- REMOVED Session Check/Creation ---
        # It's now assumed the session was created before calling this function
        # --- END REMOVAL ---

        log_callback(f"Running ADK agent for session {session_id}...") # Add log
        content = adk_types.Content(role='user', parts=[adk_types.Part(text=user_query)])

        # Run the agent asynchronously
        async for event in adk_runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            # Log tool calls to UI for visibility
            if hasattr(event, 'tool_call') and event.tool_call:
                 tool_name = getattr(event.tool_call, 'name', 'N/A')
                 log_callback(f"Agent requesting tool: {tool_name}")

            # Capture final model response
            if hasattr(event, 'content') and event.content:
                content_role = getattr(event.content, 'role', 'N/A')
                if hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text and content_role == 'model':
                            final_response = part.text

    except ValueError as ve:
        # Specifically catch the "Session not found" error if it still occurs
        if "Session not found" in str(ve):
             error_msg = f"CRITICAL ERROR: ADK Runner could not find session '{session_id}' even though it should exist."
             log_callback(error_msg)
             print(error_msg)
             traceback.print_exc()
             final_response = "Internal Error: Could not find chat session."
        else:
             # Handle other ValueErrors
             error_msg = f"ValueError during ADK chat turn: {ve}"
             log_callback(error_msg)
             print(error_msg)
             traceback.print_exc()
             final_response = f"A processing error occurred: {str(ve)}"
    except Exception as e:
        # Log other errors to UI and console
        error_msg = f"Error during ADK chat turn: {e}"
        log_callback(error_msg)
        print(error_msg) # Also print full error to console
        traceback.print_exc()
        final_response = f"An error occurred: {str(e)}"

    return final_response

def cleanup_chat_session(session_id: str, log_callback):
    """Attempts to delete the specified chat session."""
    global adk_session_service, adk_runner # Need access to the service instance
    if not adk_session_service or not adk_runner:
        log_callback("Cannot cleanup session, ADK service/runner not available.")
        return

    user_id = cfg.ADK_USER_ID
    app_name = getattr(adk_runner, 'app_name', cfg.APP_NAME)

    try:
        log_callback(f"Attempting to delete chat session {session_id}...")
        # Use the adk_session_service instance directly
        adk_session_service.delete_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        log_callback(f"Chat session {session_id} delete requested.")
    except Exception as del_e:
        log_callback(f"Info/Warning during chat session deletion for {session_id}: {del_e}")

