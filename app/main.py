from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routes import pages

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Awan — Brankas Bukti Unboxing")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(pages.router)
# BE: include router API di sini (auth, profile, packages, files, claims, stats)


@app.exception_handler(StarletteHTTPException)
async def not_found_page(request: Request, exc: StarletteHTTPException):
    # Browser yang membuka URL tak dikenal mendapat halaman "Data tidak ditemukan";
    # panggilan API (fetch dengan Accept: application/json) tetap menerima {"detail": ...}.
    wants_html = "text/html" in request.headers.get("accept", "")
    if exc.status_code == 404 and wants_html and request.method == "GET":
        return templates.TemplateResponse(request, "pages/not_found.html", status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))
