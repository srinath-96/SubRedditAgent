# main_app.py
"""
Main Flet application for the Reddit RAG Chatbot.
Coordinates UI, scraping, indexing, and chatbot interaction.
Features an initial API key entry screen.
"""
import flet as ft
import asyncio
import threading
import traceback
import sys
import os
# Ensure these are at the top for use in .env loading
from dotenv import set_key, load_dotenv

# --- Environment Setup ---
# (Your existing .env loading code here, ensure 'script_dir' is defined globally or accessible)
# Make sure your actual .env loading sets up `script_dir` correctly.
try:
    import config as cfg
except ImportError:
    print("[App] CRITICAL: config.py not found. Cannot continue.")
    sys.exit(1)

# Assuming script_dir is set up correctly from your .env loading
# If not, define it:
if '__file__' in globals() and globals()['__file__'] is not None: # Check if __file__ is defined and not None
    script_dir = os.path.dirname(os.path.abspath(__file__)) # Use abspath for robustness
else:
    script_dir = os.getcwd() # Fallback for interactive environments
    print(f"[App] __file__ not available, using current working directory for script_dir: {script_dir}")

# --- Project Imports (after initial .env load if they depend on it) ---
import ui_utils
import reddit_utils
import rag_handler
import adk_chatbot
try:
    import google.generativeai as genai
except ImportError:
    print("[App] ERROR: google.generativeai not found. Run 'pip install google-generativeai'")
    sys.exit(1)


# --- Global State ---
is_scraping = False
is_indexing = False
is_chatbot_ready = False
current_chat_session_id = None

# --- Global UI Controls (initialized in their respective view builders) ---
# For API Key View
api_key_google_input: ft.TextField = None
api_key_reddit_id_input: ft.TextField = None
api_key_reddit_secret_input: ft.TextField = None
api_key_reddit_user_agent_input: ft.TextField = None
api_view_status_text: ft.Text = None

# For Main Chatbot View
subreddit_input: ft.TextField = None
time_filter_dropdown: ft.Dropdown = None
limit_input: ft.TextField = None
scrape_button: ft.ElevatedButton = None
progress_ring: ft.ProgressRing = None
status_text: ft.Text = None # Main app's status_text
chat_history: ft.ListView = None
chat_history_styled_area: ft.Container = None
chat_input: ft.TextField = None
send_button: ft.IconButton = None
input_row: ft.Row = None
background_image_path = "/Users/srinathmurali/Desktop/reddit_automation_agents/Gemini_Generated_Image_vuhf11vuhf11vuhf.jpeg"


# --- Backend Task Functions (Define these BEFORE they are referenced) ---
def scrape_and_index_task():
    """Task to handle scraping, indexing, and chatbot initialization."""
    global is_scraping, is_indexing, is_chatbot_ready, current_chat_session_id
    global subreddit_input, time_filter_dropdown, limit_input # Ensure all globals used are listed
    
    print("[Task] Full scrape_and_index_task initiated.")
    is_chatbot_ready = False # Reset
    if current_chat_session_id:
        print(f"[Task] Cleaning up previous chat session: {current_chat_session_id}")
        adk_chatbot.cleanup_chat_session(current_chat_session_id, ui_utils.update_status)
        current_chat_session_id = None
    
    ui_utils.set_app_state(scraping=True, indexing=False, chatbot_ready=False)
    ui_utils.update_status("Scraping...", show_progress=True)
    
    subreddit = subreddit_input.value.strip()
    time_filter = time_filter_dropdown.value 
    limit_str = limit_input.value.strip()

    if not subreddit:
        ui_utils.update_status("Error: Subreddit name cannot be empty.")
        ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=False)
        return
    if not time_filter:
        ui_utils.update_status("Error: Time filter cannot be empty.")
        ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=False)
        return
    try:
        limit = int(limit_str)
        if limit <= 0:
            ui_utils.update_status("Error: Limit must be a positive number.")
            ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=False)
            return
    except ValueError:
        ui_utils.update_status("Error: Limit must be a valid number for post limit.")
        ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=False)
        return

    print(f"[Task] Starting scrape for r/{subreddit}, filter: {time_filter}, limit: {limit}")
    scraped_data = reddit_utils.scrape_subreddit(subreddit, time_filter, limit, ui_utils.update_status)

    if scraped_data is None:
        ui_utils.update_status(f"Error during scraping r/{subreddit}. Check console/logs.")
        ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=False)
        return

    ui_utils.set_app_state(scraping=False, indexing=True, chatbot_ready=False)
    ui_utils.update_status("Indexing scraped data...", show_progress=True)
    indexing_success = rag_handler.index_data_with_langchain(scraped_data, ui_utils.update_status)
    
    if not indexing_success:
        ui_utils.update_status("Error during indexing. Check console/logs.")
        ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=False)
        return

    ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=False)
    ui_utils.update_status("Initializing chatbot...", show_progress=True)
    chatbot_success = adk_chatbot.initialize_adk_chatbot(ui_utils.update_status)

    if chatbot_success:
        is_chatbot_ready = True
        ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=True)
        ui_utils.update_status("Ready to chat!", show_progress=False)
    else:
        ui_utils.set_app_state(scraping=False, indexing=False, chatbot_ready=False)
        ui_utils.update_status("Error initializing chatbot. Check console/logs.", show_progress=False)

async def send_message_task():
    """Task to handle sending a message and getting a response via ADK."""
    global current_chat_session_id, chat_input, is_chatbot_ready, is_scraping, is_indexing
    
    print("[Task] Full send_message_task initiated.")
    user_text = chat_input.value # Make sure chat_input is not None
    if not user_text or not user_text.strip(): # Check if chat_input.value is None or empty
        return
    ui_utils.add_chat_message("You", user_text, color=ft.colors.LIGHT_BLUE_ACCENT_200)
    chat_input.value = "" # Clear input
    
    ui_utils.set_app_state(scraping=is_scraping, indexing=is_indexing, chatbot_ready=False)
    ui_utils.update_status("Agent thinking...", show_progress=True)
    
    agent_response = "Error: Could not process message." # Default
    try:
        session_creation_needed = False
        if current_chat_session_id is None:
            current_chat_session_id = f"flet_chat_{os.urandom(6).hex()}"
            session_creation_needed = True
        
        if session_creation_needed: # This block was missing an indent
            if adk_chatbot.adk_session_service and adk_chatbot.adk_runner:
                adk_chatbot.adk_session_service.create_session(
                   app_name=getattr(adk_chatbot.adk_runner, 'app_name', cfg.APP_NAME),
                   user_id=cfg.ADK_USER_ID,
                   session_id=current_chat_session_id
                )
            else:
                raise ConnectionError("ADK Runner/Service not ready for session creation.")

        agent_response = await adk_chatbot.handle_adk_chat_turn(
            current_chat_session_id, user_text, ui_utils.update_status
        )
    except Exception as task_e:
        print(f"[Task Error] Exception in send_message_task: {task_e}")
        traceback.print_exc()
        agent_response = f"An internal error occurred: {task_e}"

    ui_utils.add_chat_message("Agent", agent_response, color=ft.colors.WHITE)
    ui_utils.set_app_state(scraping=is_scraping, indexing=is_indexing, chatbot_ready=True)
    ui_utils.update_status("Ready.", show_progress=False)

# --- Event Handlers (Define these AFTER tasks, but BEFORE UI elements that use them) ---
def scrape_button_click(e):
    global is_scraping, is_indexing
    if is_scraping or is_indexing: return
    print("[UI Event] Scrape button clicked.")
    thread = threading.Thread(target=scrape_and_index_task, daemon=True)
    thread.start()

def send_message_click(e):
    global is_chatbot_ready, chat_input
    if chat_input and chat_input.value and chat_input.value.strip() and is_chatbot_ready: # Added check for chat_input.value
        print("[UI Event] Send button clicked.")
        if ui_utils.page_ref:
            ui_utils.page_ref.run_task(send_message_task)
        else:
            print("[UI Event Error] Page reference not set in ui_utils.")
            ui_utils.update_status("Error: Cannot send message (page context missing).", False)

# --- Service Initialization Helper ---
def attempt_service_initialization(status_update_callback) -> bool:
    """Initializes Google GenAI and Reddit. Returns True on success."""
    print("[ServiceInit] Attempting to initialize services...")
    try:
        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            status_update_callback("Error: GOOGLE_API_KEY not found.", False)
            return False
        genai.configure(api_key=google_key)
        print("[ServiceInit] Google GenAI configured.")
        
        if not reddit_utils.initialize_reddit(status_update_callback):
            # reddit_utils.initialize_reddit should call the callback with its status
            print("[ServiceInit] Reddit (PRAW) initialization failed.")
            return False
        print("[ServiceInit] Reddit (PRAW) initialized.")
        status_update_callback("Services initialized successfully.", False) # General success for this function
        return True
    except Exception as e:
        error_msg = f"Service initialization error: {e}"
        print(f"[ServiceInit] {error_msg}")
        traceback.print_exc()
        status_update_callback(error_msg, False)
        return False

# --- View Switching and API Key Logic ---
def show_main_chatbot_view(page: ft.Page):
    global subreddit_input, time_filter_dropdown, limit_input, scrape_button, progress_ring
    global status_text, chat_history, chat_history_styled_area, chat_input, send_button, input_row
    global background_image_path

    print("[ViewSwitch] Building and showing Main Chatbot View.")
    page.controls.clear()
    page.vertical_alignment = None # Allow main app to use full height
    page.horizontal_alignment = None
    page.bgcolor = ft.colors.with_opacity(0.1, ft.colors.BLACK)

    # Define Main App UI Controls
    subreddit_input = ft.TextField(
        label="Subreddit Name", value=cfg.DEFAULT_SUBREDDIT, width=200, dense=True,
        border_radius=ft.border_radius.all(5),
        border_color=ft.colors.with_opacity(0.6, ft.colors.WHITE),
        focused_border_color=ft.colors.RED_ACCENT_200
    )
    time_filter_dropdown = ft.Dropdown(
        label="Time Filter", value=cfg.DEFAULT_TIME_FILTER,
        options=[ft.dropdown.Option(tf) for tf in ["all", "year", "month", "week", "day", "hour"]],
        width=120, dense=True,
        border_radius=ft.border_radius.all(5),
        border_color=ft.colors.with_opacity(0.6, ft.colors.WHITE),
        focused_border_color=ft.colors.RED_ACCENT_200
    )
    limit_input = ft.TextField(
        label="Post Limit", value=str(cfg.DEFAULT_LIMIT), width=100, dense=True,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=ft.border_radius.all(5),
        border_color=ft.colors.with_opacity(0.6, ft.colors.WHITE),
        focused_border_color=ft.colors.RED_ACCENT_200
    )
    scrape_button = ft.ElevatedButton(
        "Scrape & Index", on_click=scrape_button_click,
        bgcolor=ft.colors.RED_600, color=ft.colors.WHITE,
        height=40, # Added height
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5), elevation=4, shadow_color=ft.colors.BLACK54) # Added style
    )
    progress_ring = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=3, color=ft.colors.RED_ACCENT_200)
    status_text = ft.Text("Status: Ready.", size=11, italic=True, color=ft.colors.with_opacity(0.8, ft.colors.WHITE))
    chat_history = ft.ListView(expand=True, spacing=12, auto_scroll=True)
    chat_history_styled_area = ft.Container(
        content=chat_history, expand=True,
        border=ft.border.all(2, ft.colors.with_opacity(0.8, ft.colors.RED_600)),
        border_radius=ft.border_radius.all(8),
        padding=10,
        bgcolor=ft.colors.with_opacity(0.75, ft.colors.BLACK),
        shadow=ft.BoxShadow(
             spread_radius=1, blur_radius=5, color=ft.colors.with_opacity(0.4, ft.colors.BLACK),
             offset=ft.Offset(0, 0), blur_style=ft.ShadowBlurStyle.INNER
        )
    )
    chat_input = ft.TextField(
        label="Ask the chatbot...", expand=True, on_submit=send_message_click, shift_enter=True, # Added shift_enter
        border_radius=ft.border_radius.all(20),
        border_color=ft.colors.with_opacity(0.6, ft.colors.WHITE),
        focused_border_color=ft.colors.RED_ACCENT_200
    )
    send_button = ft.IconButton(
        icon=ft.icons.SEND_ROUNDED, on_click=send_message_click,
        icon_color=ft.colors.RED_600,
        tooltip="Send message" # Added tooltip
    )
    input_row = ft.Row([chat_input, send_button], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    ui_utils.set_ui_refs(page, status_text, progress_ring, scrape_button, chat_input, send_button, chat_history)
    ui_utils.page_ref = page # For page.run_task in send_message_click

    main_layout = ft.Container(
        content=ft.Stack([
            ft.Container(
                content=ft.Image(src=background_image_path, fit=ft.ImageFit.CONTAIN, opacity=1.0),
                alignment=ft.alignment.center, expand=True
            ),
            ft.Container(
                content=ft.Column([
                    ft.Row([subreddit_input, time_filter_dropdown, limit_input, scrape_button, progress_ring],
                           alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    status_text,
                    ft.Divider(height=5, thickness=1, color=ft.colors.with_opacity(0.3, ft.colors.WHITE)), # Added thickness and color
                    chat_history_styled_area,
                    ft.Divider(height=5, thickness=1, color=ft.colors.with_opacity(0.3, ft.colors.WHITE)), # Added thickness and color
                    input_row,
                ], expand=True, spacing=10),
                padding=20, margin=0, expand=True, # Removed redundant border_radius
            )
        ], expand=True),
        bgcolor=ft.colors.RED_700, expand=True
    )
    page.add(main_layout)
    ui_utils.update_status("Chatbot ready. Please scrape data first.", False)
    scrape_button.disabled = False
    chat_input.disabled = True
    send_button.disabled = True
    page.update()

def handle_save_keys_and_proceed(e, page: ft.Page):
    global api_key_google_input, api_key_reddit_id_input, api_key_reddit_secret_input
    global api_key_reddit_user_agent_input, api_view_status_text, script_dir

    print("[APIKeysSave] Attempting to save keys...")
    google_api = api_key_google_input.value.strip()
    reddit_id = api_key_reddit_id_input.value.strip()
    reddit_secret = api_key_reddit_secret_input.value.strip()
    reddit_agent = api_key_reddit_user_agent_input.value.strip()

    required = {"GOOGLE_API_KEY": google_api, "REDDIT_CLIENT_ID": reddit_id,
                "REDDIT_CLIENT_SECRET": reddit_secret, "REDDIT_USER_AGENT": reddit_agent}

    if not all(required.values()):
        api_view_status_text.value = "Error: All API key fields are required."
        api_view_status_text.color = ft.colors.RED_ACCENT_700
        page.update()
        return

    try:
        dotenv_path = os.path.join(script_dir, cfg.DOTENV_PATH_SCRIPT_DIR)
        if not os.path.exists(os.path.dirname(dotenv_path)):
            os.makedirs(os.path.dirname(dotenv_path), exist_ok=True)

        for key_name, key_value in required.items():
            set_key(dotenv_path, key_name, key_value, quote_mode="always")
            os.environ[key_name] = key_value
        
        api_view_status_text.value = "Keys saved. Initializing services..."
        api_view_status_text.color = ft.colors.WHITE70
        page.update()

        load_dotenv(dotenv_path=dotenv_path, override=True)

        # Define the callback for attempt_service_initialization
        def api_view_status_updater(message_str, show_progress_bool=None): # Default show_progress_bool
            if api_view_status_text: # Check if the UI element exists
                api_view_status_text.value = message_str
                # Determine color based on message content if show_progress_bool is not definitive
                if "error" in message_str.lower() or "fail" in message_str.lower():
                    api_view_status_text.color = ft.colors.RED_ACCENT_700
                elif "success" in message_str.lower() or "ready" in message_str.lower() or "config" in message_str.lower(): # added "config"
                    api_view_status_text.color = ft.colors.GREEN_ACCENT_400
                else:
                    api_view_status_text.color = ft.colors.WHITE70 # Default/neutral
            if page: # Check if page exists
                page.update()

        if attempt_service_initialization(api_view_status_updater):
            if api_view_status_text: # Check if UI element exists
                api_view_status_text.value = "Success! Services initialized. Loading chatbot..."
                api_view_status_text.color = ft.colors.GREEN_ACCENT_400
            if page: page.update()
            #time.sleep(1) # Optional pause
            show_main_chatbot_view(page)
        else:
            # Error message should have been set in api_view_status_text by the updater
            print("[APIKeysSave] Service initialization failed after saving keys.")
            # No need to update api_view_status_text here again if the callback did it.
        # if page: page.update() # Update to ensure UI consistency

    except Exception as ex:
        error_msg = f"Error during key saving: {ex}"
        print(f"[APIKeysSave] {error_msg}")
        traceback.print_exc()
        api_view_status_text.value = error_msg
        api_view_status_text.color = ft.colors.RED_ACCENT_700
        page.update()

def show_api_key_entry_view(page: ft.Page):
    global api_key_google_input, api_key_reddit_id_input, api_key_reddit_secret_input
    global api_key_reddit_user_agent_input, api_view_status_text

    print("[ViewSwitch] Building and showing API Key Entry View.")
    page.controls.clear()
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = ft.colors.BLUE_GREY_800

    api_key_google_input = ft.TextField(label="Google API Key", password=True, can_reveal_password=True, width=400)
    api_key_reddit_id_input = ft.TextField(label="Reddit Client ID", width=400)
    api_key_reddit_secret_input = ft.TextField(label="Reddit Client Secret", password=True, can_reveal_password=True, width=400)
    api_key_reddit_user_agent_input = ft.TextField(label="Reddit User Agent", hint_text="e.g., my-app/1.0 by u/username", width=400)
    api_view_status_text = ft.Text("Enter your API keys to use the chatbot.", italic=True, color=ft.colors.WHITE70) # Added color

    save_button = ft.ElevatedButton(
        "Save and Continue",
        on_click=lambda e: handle_save_keys_and_proceed(e, page),
        bgcolor=ft.colors.RED_600, color=ft.colors.WHITE, height=40 # Added height
    )

    page.add(
        ft.Column(
            [
                ft.Text("Reddit RAG Chatbot Setup", size=24, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE), # Added color
                ft.Text("Please provide API credentials to continue.", color=ft.colors.WHITE70), # Added color
                ft.Divider(height=20, color=ft.colors.TRANSPARENT),
                api_key_google_input,
                api_key_reddit_id_input,
                api_key_reddit_secret_input,
                api_key_reddit_user_agent_input,
                ft.Container(content=api_view_status_text, padding=ft.padding.only(top=10)),
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                save_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
            expand=True
        )
    )
    page.update()

# --- Flet UI Main Function ---
def main(page: ft.Page):
    page.title = "Reddit RAG Chatbot"
    page.padding = 0
    print("[AppMain] Application starting...")

    # ui_utils needs to be initialized with a page and status_text first if its update_status is used directly
    # For the very initial check, we can use a simpler lambda if ui_utils isn't fully ready.
    # However, if show_api_key_entry_view is called, it sets up its own status text.
    # Let's ensure ui_utils has a basic status update capability even before main UI is built.
    
    initial_check_status_messages = []
    def initial_check_status_collector(msg, prog=None):
        print(f"[InitialServiceCheck] Status: {msg}, Progress: {prog}")
        initial_check_status_messages.append(msg)

    keys_configured_and_services_ready = attempt_service_initialization(initial_check_status_collector)

    if keys_configured_and_services_ready:
        print("[AppMain] Services initialized successfully at startup.")
        show_main_chatbot_view(page)
    else:
        print("[AppMain] API keys missing or initial service configuration failed.")
        show_api_key_entry_view(page)
        # Optionally, display the last message from initial_check_status_messages in the API view status
        if api_view_status_text and initial_check_status_messages:
            api_view_status_text.value = initial_check_status_messages[-1]
            if "error" in initial_check_status_messages[-1].lower():
                api_view_status_text.color = ft.colors.RED_ACCENT_700
            page.update()
    
# --- Run the Flet App ---
if __name__ == "__main__":
    print("Starting Reddit RAG Chatbot Flet application...")
    ft.app(target=main)

