from asyncio import CancelledError, create_task
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.router import router
from service.parser import Parser


@asynccontextmanager
async def lifespan(app: FastAPI):
    parser = Parser()
    cache_task = create_task(parser.clear_cache_task())
    try:
        yield
    finally:
        cache_task.cancel()
        try:
            await cache_task
        except CancelledError:
            print("✔ Cache clear task stopped")


app = FastAPI(lifespan=lifespan)


app.include_router(router=router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
