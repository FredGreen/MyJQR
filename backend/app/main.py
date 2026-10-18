import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import admin, auth, joule, memory, templates, works

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

app = FastAPI(title="MyJQR API", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(templates.router, prefix=API_PREFIX)
app.include_router(works.router, prefix=API_PREFIX)
app.include_router(joule.router, prefix=API_PREFIX)
app.include_router(memory.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logging.exception("unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"code": 500, "msg": "internal error"})


@app.get("/health")
def health():
    return {"code": 0, "msg": "ok"}
