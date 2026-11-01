from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from wiki.client import WikiClient, WikiClientError


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = WikiClient()
    await client.start()
    app.state.wiki = client
    yield
    await client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Genshin Wiki API",
        version="2.1.0",
        description="Live-scraping API for Genshin Impact Fandom Wiki. Designed for LLM consumption.",
        lifespan=lifespan,
    )

    @app.exception_handler(WikiClientError)
    async def wiki_error(request: Request, exc: WikiClientError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    from api.routes.search import router as search_router
    from api.routes.pages import router as pages_router
    from api.routes.categories import router as categories_router

    app.include_router(search_router, tags=["Search"])
    app.include_router(pages_router, tags=["Pages"])
    app.include_router(categories_router, tags=["Categories"])

    @app.get("/", tags=["Meta"])
    async def root():
        return {
            "service": "Genshin Wiki API",
            "version": "2.1.0",
            "description": "Live-scraping API for Genshin Impact Fandom Wiki",
            "endpoints": {
                "GET /search?q=term&limit=10": "Search wiki pages by name",
                "GET /fulltext?q=term&limit=10": "Search inside page text, returns matching titles",
                "GET /page/{title}": "Full page as clean text (add ?format=structured for infobox + keyed sections)",
                "GET /page/{title}/sections": "List section names & indexes",
                "GET /page/{title}/section/{index}": "Fetch single section by index",
                "GET /category/{name}?limit=50": "List pages in a wiki category",
            },
            "workflow": [
                "1. GET /search?q=raiden shogun → find page title",
                "2. GET /page/Raiden_Shogun/sections → see available sections",
                "3. GET /page/Raiden_Shogun/section/3 → get specific section",
                "4. Or GET /page/Raiden_Shogun?format=structured → full page with infobox",
            ],
        }

    @app.get("/health", tags=["Meta"])
    async def health():
        return {"status": "ok"}

    return app
