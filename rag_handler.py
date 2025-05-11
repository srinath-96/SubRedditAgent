# rag_handler.py
"""
Handles LangChain setup, document indexing using ParentDocumentRetriever,
and provides the retrieval function for the ADK agent tool.
Uses the newer langchain-chroma package with unique persistent directories per run.
"""
import datetime
import traceback
import os
import shutil # Still needed for cleanup if desired, but not for overwrite prevention
import uuid # For generating unique directory names

# LangChain Imports
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
# --- Use updated Chroma import ---
from langchain_chroma import Chroma
# --- End updated import ---
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore

# Import config
import config as cfg

# --- Global Variables for LangChain components ---
lc_vectorstore = None
lc_parent_store = None
lc_retriever = None
lc_embeddings = None
# --- Store the CURRENT persistence path ---
current_chroma_persist_dir = None

def index_data_with_langchain(scraped_data: list, log_callback):
    """
    Indexes the scraped data using LangChain ParentDocumentRetriever.
    Uses a NEW unique persistent directory for each run to avoid conflicts.
    """
    global lc_vectorstore, lc_parent_store, lc_retriever, lc_embeddings, current_chroma_persist_dir
    log_callback("Starting indexing process (using langchain-chroma, unique persistent dir)...")

    # Reset previous Python object references
    lc_vectorstore = None
    lc_parent_store = None
    lc_retriever = None
    lc_embeddings = None
    # No need to clear the *previous* directory anymore, as we create a new one.
    # Cleanup of old directories could be added as a separate maintenance step if needed.

    if not scraped_data:
        log_callback("Error: No scraped data provided for indexing.")
        return False

    try:
        # --- Generate a UNIQUE directory path for this run ---
        unique_id = uuid.uuid4()
        current_chroma_persist_dir = os.path.join(os.path.dirname(__file__), f"chroma_db_{unique_id}")
        log_callback(f"Using unique persistence directory for this run: {current_chroma_persist_dir}")
        # Create the directory if it doesn't exist (it shouldn't)
        os.makedirs(current_chroma_persist_dir, exist_ok=True)
        # --- End Unique Path Generation ---


        # 1. Convert scraped data to LangChain Documents (same as before)
        log_callback(f"Converting {len(scraped_data)} scraped posts to LangChain Documents...")
        documents = []
        for i, post in enumerate(scraped_data):
            content = f"Title: {post.get('title', '')}\nBody: {post.get('body', '')}".strip()
            if not content or content == "Title: \nBody:":
                continue
            metadata = {
                "post_id": post.get("id", f"post_{i}"),
                "url": post.get("url", "N/A"),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "created_utc_iso": post.get("created_utc", "N/A"),
                "source": f"reddit_scrape_{post.get('id', f'post_{i}')}"
            }
            documents.append(Document(page_content=content, metadata=metadata))

        log_callback(f"Created {len(documents)} LangChain Documents.")
        if not documents:
            log_callback("Error: No valid documents created from scraped data.")
            # Clean up the newly created empty directory
            if os.path.exists(current_chroma_persist_dir):
                 shutil.rmtree(current_chroma_persist_dir)
            current_chroma_persist_dir = None # Reset global path
            return False

        # 2. Initialize Stores
        log_callback("Initializing parent docstore (InMemoryStore)...")
        lc_parent_store = InMemoryStore() # Parent docs can stay in memory

        log_callback("Initializing Chroma vectorstore for child documents (persistent)...")
        lc_embeddings = GoogleGenerativeAIEmbeddings(model=cfg.EMBEDDING_MODEL)

        # --- Initialize Chroma using the UNIQUE Persistent Directory ---
        collection_name = "reddit_pdr_persistent_collection" # Collection name can be reused
        log_callback(f"Initializing Chroma with collection: {collection_name} in dir: {current_chroma_persist_dir}")

        # Initialize Chroma object pointing to the UNIQUE persistent directory
        lc_vectorstore = Chroma(
             collection_name=collection_name,
             embedding_function=lc_embeddings,
             persist_directory=current_chroma_persist_dir # Use the unique path
        )
        log_callback(f"Chroma vectorstore object initialized (pointing to {current_chroma_persist_dir}).")
        # --- End Chroma Initialization ---


        # 3. Initialize Splitters (same as before)
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg.PARENT_CHUNK_SIZE, chunk_overlap=cfg.PARENT_CHUNK_OVERLAP
        )
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg.CHILD_CHUNK_SIZE, chunk_overlap=cfg.CHILD_CHUNK_OVERLAP
        )
        log_callback("Initialized parent and child text splitters.")

        # 4. Initialize ParentDocumentRetriever (same as before)
        log_callback("Initializing ParentDocumentRetriever...")
        lc_retriever = ParentDocumentRetriever(
            vectorstore=lc_vectorstore, # Pass the Chroma object
            docstore=lc_parent_store,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter
        )

        # 5. Add Documents (this will populate the unique persistent Chroma DB)
        log_callback(f"Adding {len(documents)} documents to the retriever (embedding/indexing to persistent store)...")
        lc_retriever.add_documents(documents, ids=None, add_to_docstore=True)
        log_callback("Indexing complete.")
        log_callback(f"Parent store size: {len(list(lc_parent_store.yield_keys()))} keys.")

        # Explicitly persist changes
        try:
             log_callback("Attempting to persist Chroma vectorstore changes...")
             lc_vectorstore.persist()
             log_callback("Chroma persistence called.")
        except AttributeError:
             log_callback("Info: Chroma instance may not have a separate .persist() method (likely automatic).")
        except Exception as persist_e:
             log_callback(f"Warning: Error during explicit Chroma persist: {persist_e}")


        # Optional: Check Chroma count if possible
        try:
             count = lc_vectorstore._collection.count()
             log_callback(f"Chroma child vector count: {count}")
        except Exception:
             log_callback("Could not get Chroma vector count.")

        return True

    except Exception as e:
        log_callback(f"Error during indexing: {e}")
        traceback.print_exc()
        # Clean up potentially partially created directory on error
        if current_chroma_persist_dir and os.path.exists(current_chroma_persist_dir):
             try:
                 shutil.rmtree(current_chroma_persist_dir)
                 log_callback(f"Cleaned up directory {current_chroma_persist_dir} after error.")
             except Exception as clean_e:
                  log_callback(f"Warning: Error cleaning up directory {current_chroma_persist_dir} after error: {clean_e}")
        # Reset global state
        lc_vectorstore = None
        lc_parent_store = None
        lc_retriever = None
        current_chroma_persist_dir = None
        return False

# Retrieval function to be used as ADK tool
def retrieve_context_parent_retriever_tool(query: str) -> dict:
    """
    Retrieves relevant PARENT document chunks using the initialized LangChain
    ParentDocumentRetriever. Uses the CURRENT persistent Chroma store path.
    """
    global lc_retriever, current_chroma_persist_dir # Need path if re-initialization is attempted

    print(f"\n--- ADK Tool: ParentDocumentRetriever called with query: '{query}' ---")

    # Check if the retriever object exists from the most recent indexing step
    if lc_retriever is None:
        print("  [Tool Error] ParentDocumentRetriever object is not initialized (indexing likely failed or hasn't run).")
        # Attempting re-initialization here is complex because the parent_store is in memory.
        # It's better to rely on the indexing step completing successfully.
        return {"status": "error", "message": "Retriever not ready (indexing likely failed or hasn't run).", "context": ""}

    try:
        print(f"  Performing retrieval via ParentDocumentRetriever (using store at {current_chroma_persist_dir})...")
        # Use invoke which is the newer method
        retrieved_docs = lc_retriever.invoke(query) # Returns List[Document]

        if not retrieved_docs:
            print("  [Tool Info] No relevant parent documents found.")
            return {"status": "success", "message": "No relevant context found.", "context": ""}
        else:
            context_list = []
            print(f"  [Tool Info] Retrieved {len(retrieved_docs)} parent document(s).")
            for i, doc in enumerate(retrieved_docs):
                context_chunk = (
                    f"--- Retrieved Context Chunk {i+1} ---\n"
                    f"Source Post ID: {doc.metadata.get('post_id', 'N/A')}\n"
                    f"Content: {doc.page_content}"
                )
                context_list.append(context_chunk)
            context_string = "\n\n".join(context_list)
            print(f"  [Tool Success] Formatted context from {len(retrieved_docs)} parent document(s).")
            return {"status": "success", "message": "Context retrieved.", "context": context_string}

    except Exception as e:
        print(f"  [Tool Error] Error during ParentDocumentRetriever retrieval: {e}")
        if "sqlite3.OperationalError: no such table" in str(e):
             print(f"  [Tool Error Detail] SQLite 'no such table' error. ChromaDB state issue persists or path mismatch? Current Path: {current_chroma_persist_dir}")
        elif "sqlite3" in str(e).lower():
             print(f"  [Tool Error Detail] Other SQLite error detected: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"An error occurred during retrieval: {str(e)}", "context": ""}

