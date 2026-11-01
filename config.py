import os

WIKI_BASE_URL = "https://genshin-impact.fandom.com"
WIKI_API_URL = f"{WIKI_BASE_URL}/api.php"

IMAGE_API_URL = "https://gi.yatta.moe/api/v2/en"
IMAGE_ASSET_URL = "https://gi.yatta.moe/assets/UI"
IMAGE_CATALOG_TTL = int(os.getenv("IMAGE_CATALOG_TTL", "21600"))  # 6 hours

CACHE_TTL = int(os.getenv("CACHE_TTL", "1800"))  # 30 minutes
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "500"))

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.15"))  # seconds between requests
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
