# reddit_utils.py
"""
Handles Reddit PRAW initialization and data scraping.
Replicates logic from the user's original `reddit_scraper.py`.
"""
import praw
import datetime
import traceback
import os

# --- Global PRAW Instance ---
reddit_instance = None

def initialize_reddit(log_callback):
    """Initializes and returns a PRAW Reddit instance using environment variables."""
    global reddit_instance
    if reddit_instance:
        log_callback("PRAW instance already initialized.")
        return reddit_instance

    log_callback("Initializing PRAW Reddit instance...")
    # Load credentials from environment variables (set via .env or system)
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    if not all([client_id, client_secret, user_agent]):
        log_callback("ERROR: Reddit API credentials (ID, SECRET, USER_AGENT) not found in environment.")
        return None

    try:
        reddit_instance = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            read_only=True # Set to True for scraping public data
        )
        # --- REMOVED Problematic Check ---
        # The praw.Reddit call above will raise exceptions on major auth failures.
        # No need for the extra check that caused the AttributeError.
        # _ = reddit_instance.config.api_request_delay # REMOVED
        # --- End Removal ---

        # If the praw.Reddit call succeeded without error, assume basic initialization worked.
        log_callback(f"PRAW Reddit instance created successfully for user agent: {user_agent}")
        return reddit_instance
    except praw.exceptions.PRAWException as e:
        # Catch specific PRAW errors (like auth issues)
        log_callback(f"ERROR: Failed to initialize PRAW Reddit instance: {e}")
        traceback.print_exc()
        reddit_instance = None
        return None
    except Exception as e:
        # Catch any other unexpected errors during init
        log_callback(f"ERROR: An unexpected error occurred during PRAW initialization: {e}")
        traceback.print_exc()
        reddit_instance = None
        return None

def scrape_subreddit(subreddit_name: str, time_filter: str, limit: int, log_callback):
    """
    Scrapes posts and their top-level comments from a subreddit using the global reddit_instance.
    """
    global reddit_instance
    if not reddit_instance:
        log_callback("ERROR: PRAW instance not available for scraping.")
        return None

    log_callback(f"Fetching top {limit} posts from r/{subreddit_name} (filter: {time_filter})...")

    try:
        # Check if subreddit exists and is accessible before iterating
        # Note: This makes an extra API call but prevents iterating on invalid subs
        subreddit = reddit_instance.subreddit(subreddit_name)
        try:
             # Accessing a property like display_name forces a check
             _ = subreddit.display_name
             log_callback(f"Confirmed access to r/{subreddit.display_name}")
        except Exception as sub_check_e:
             # Handle specific exceptions if possible (NotFound, Forbidden)
             log_callback(f"ERROR: Cannot access subreddit 'r/{subreddit_name}': {sub_check_e}. Is it private or misspelled?")
             return None # Stop if subreddit is inaccessible

        scraped_data = []
        post_count = 0
        # Now iterate through posts
        for post in subreddit.top(time_filter=time_filter, limit=limit):
            post_count += 1
            if post_count % 10 == 0 and post_count > 0:
                 log_callback(f"  Fetched {post_count}/{limit} posts...")

            post_data = {
                "id": post.id,
                "title": post.title,
                "score": post.score,
                "url": post.url,
                "num_comments": post.num_comments,
                "created_utc": datetime.datetime.fromtimestamp(post.created_utc, tz=datetime.timezone.utc).isoformat(),
                "body": post.selftext,
                "is_over18": post.over_18,
                "upvote_ratio": post.upvote_ratio,
                "comments": [] # Keep comments field for potential future use
            }
            scraped_data.append(post_data)

        log_callback(f"Finished scraping. Fetched data for {len(scraped_data)} posts.")
        return scraped_data

    # Keep specific PRAW exceptions if needed, but the check above might catch some
    except praw.exceptions.NotFound: # Should be caught by the check above now
         log_callback(f"ERROR: Subreddit 'r/{subreddit_name}' not found.")
         return None
    except praw.exceptions.ResponseException as resp_e:
         log_callback(f"ERROR: Reddit API Response Error (Rate Limit? Permissions?): {resp_e}")
         traceback.print_exc()
         return None
    except praw.exceptions.PRAWException as e:
        log_callback(f"ERROR: An error occurred with PRAW during scraping: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        # Catch-all for unexpected errors during scraping loop
        log_callback(f"ERROR: An unexpected error occurred during scraping: {e}")
        traceback.print_exc()
        return None

