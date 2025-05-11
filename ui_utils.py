# ui_utils.py
"""
Utility functions for safely updating the Flet UI from background threads.
Includes fix for text wrapping in chat messages.
"""
import flet as ft
import traceback # Import traceback for error logging

# --- Global Variables ---
# These will be set by the main application
_page_ref = None
_status_text_ref = None
_progress_ring_ref = None
_scrape_button_ref = None
_chat_input_ref = None
_send_button_ref = None
_chat_history_ref = None

# Flags to track application state (managed by main_app)
_is_scraping = False
_is_indexing = False
_is_chatbot_ready = False

def set_ui_refs(page, status_text, progress_ring, scrape_button, chat_input, send_button, chat_history):
    """Stores references to UI elements needed for updates."""
    global _page_ref, _status_text_ref, _progress_ring_ref, _scrape_button_ref
    global _chat_input_ref, _send_button_ref, _chat_history_ref
    _page_ref = page
    _status_text_ref = status_text
    _progress_ring_ref = progress_ring
    _scrape_button_ref = scrape_button
    _chat_input_ref = chat_input
    _send_button_ref = send_button
    _chat_history_ref = chat_history
    print("[UI Utils] UI references set.") # Confirm refs are set

def set_app_state(scraping: bool, indexing: bool, chatbot_ready: bool):
    """Updates the internal state flags and triggers a UI status update."""
    global _is_scraping, _is_indexing, _is_chatbot_ready
    changed = (
        _is_scraping != scraping or
        _is_indexing != indexing or
        _is_chatbot_ready != chatbot_ready
    )
    _is_scraping = scraping
    _is_indexing = indexing
    _is_chatbot_ready = chatbot_ready
    # Trigger a UI update if state impacting controls changed
    if changed and _status_text_ref and _progress_ring_ref:
        # Call update_status to refresh button states etc.
        # Use the current status message if available
        current_status = "Unknown" # Default status
        try:
            # Safely get current status text
            if _status_text_ref and hasattr(_status_text_ref, 'value'):
                 current_status = _status_text_ref.value.replace("Status: ", "")
        except Exception as e:
             print(f"[UI Utils Warning] Could not get current status text: {e}")

        # Check progress ring visibility safely
        current_progress_visible = False
        try:
            if _progress_ring_ref and hasattr(_progress_ring_ref, 'visible'):
                 current_progress_visible = _progress_ring_ref.visible
        except Exception as e:
             print(f"[UI Utils Warning] Could not get current progress visibility: {e}")

        update_status(current_status, current_progress_visible)
    elif changed:
         print("[UI Utils Warning] State changed but status/progress refs missing or inaccessible.")


def update_status(message: str, show_progress: bool = False):
    """Safely update the status text and progress ring from any thread."""
    # Also print to console for backend debugging
    print(f"[UI Status Update] Message: '{message}', Progress: {show_progress}")

    if not _page_ref:
        print("[UI Update Error] Page reference (_page_ref) is not set.")
        return
    if not _status_text_ref or not _progress_ring_ref:
        print("[UI Update Error] Status or Progress Ring refs not set.")
        # Attempt to update anyway if page exists
        # return # Optionally return if refs are missing

    try:
        # Modify controls directly
        if _status_text_ref:
            _status_text_ref.value = f"Status: {message}"
        if _progress_ring_ref:
            _progress_ring_ref.visible = show_progress

        # Update button states based on global flags
        if _scrape_button_ref:
            _scrape_button_ref.disabled = _is_scraping or _is_indexing
        if _chat_input_ref:
            _chat_input_ref.disabled = not _is_chatbot_ready or _is_scraping or _is_indexing
        if _send_button_ref:
            _send_button_ref.disabled = not _is_chatbot_ready or _is_scraping or _is_indexing

        # Call page.update() - Flet should handle thread safety
        _page_ref.update()

    except Exception as e:
        print(f"[UI Update Error] Failed during update_status execution: {e}")
        print(traceback.format_exc())


def add_chat_message(sender: str, message: str, color: str = ft.colors.BLACK):
    """
    Safely add a message to the chat history ListView, ensuring text wraps.
    """
    print(f"[Chat Update] Sender: {sender}, Message: {message[:60]}...") # Log chat updates

    if not _page_ref:
        print("[UI Update Error] Page reference (_page_ref) is not set.")
        return
    if not _chat_history_ref:
        print("[UI Update Error] Chat history reference (_chat_history_ref) is not set.")
        return

    try:
        # --- Text Wrapping Fix ---
        # Wrap the message content (Markdown) in a Container that can expand
        message_content = ft.Container(
            content=ft.Markdown(
                message,
                selectable=True,
                # Use updated enum if needed based on Flet version:
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB if hasattr(ft, 'MarkdownExtensionSet') else "gitHubWeb",
                code_theme="atom-one-dark", # Check if theme name is valid
                # code_theme_style=ft.TextStyle(font_family="monospace") # Alternative styling
            ),
            expand=True, # Allow the container (and thus Markdown) to take available width
            padding=ft.padding.only(left=5) # Add slight padding from sender label
        )

        # Create the new message row, putting the sender label and the container together
        new_message_row = ft.Row(
            [
                # Fixed width for sender label to prevent it from pushing content
                ft.Text(f"{sender}:", weight=ft.FontWeight.BOLD, color=color, width=50, no_wrap=True),
                message_content, # Add the container with the message that can expand
            ],
            vertical_alignment=ft.CrossAxisAlignment.START # Align items to the top
        )
        # --- End Text Wrapping Fix ---


        # Append to controls list
        _chat_history_ref.controls.append(new_message_row)

        # Call page.update() - Flet should handle thread safety
        _page_ref.update()

    except Exception as e:
        print(f"[UI Update Error] Failed during add_chat_message execution: {e}")
        print(traceback.format_exc())

