import os

WIKI_BASE_URL = "https://genshin-impact.fandom.com"
WIKI_API_URL = f"{WIKI_BASE_URL}/api.php"

CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "500"))

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.15"))  # seconds between requests
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
