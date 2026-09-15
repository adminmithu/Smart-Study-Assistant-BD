import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8949634299:AAFYAILyoX0lJxtP92mgmXs8PWuZ6Ka4mZ4")

# Default Admin User IDs
ADMIN_IDS = [
    int(admin_id.strip())
    for admin_id in os.getenv("ADMIN_IDS", "8929349073").split(",")
    if admin_id.strip().isdigit()
]

# File Paths
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "bot_database.db"))
CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_db")
TEMP_PDF_DIR = str(BASE_DIR / "temp_pdfs")

# Ensure directories exist
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(TEMP_PDF_DIR, exist_ok=True)

# Embedding & AI Model Configuration
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# PDF Upload Limits (To prevent memory overload)
MAX_PDF_SIZE_MB = 20    # Maximum file size in MB
MAX_PDF_PAGES = 150     # Maximum pages to process per PDF

