import uvicorn

from config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("api.app:create_app", host=HOST, port=PORT, factory=True)
