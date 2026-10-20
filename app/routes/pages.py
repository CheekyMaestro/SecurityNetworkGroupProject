"""Route halaman (FE). Hanya me-render template; semua data diambil JS lewat API."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(include_in_schema=False)


def render(request: Request, name: str, **ctx):
    return templates.TemplateResponse(request, f"pages/{name}.html", ctx)


@router.get("/")
def home():
    return RedirectResponse("/masuk")


@router.get("/masuk")
def masuk(request: Request):
    return render(request, "masuk")


@router.get("/daftar")
def daftar(request: Request):
    return render(request, "daftar")


@router.get("/brankas")
def brankas(request: Request):
    return render(request, "brankas", active="brankas")


@router.get("/unboxing/baru")
def unboxing_baru(request: Request):
    return render(request, "unboxing_baru", active="unboxing")


@router.get("/paket/{package_id}")
def paket_detail(request: Request, package_id: int):
    return render(request, "paket_detail", active="brankas", package_id=package_id)


@router.get("/paket/{package_id}/klaim")
def paket_klaim(request: Request, package_id: int):
    return render(request, "paket_klaim", package_id=package_id)


@router.get("/profil")
def profil(request: Request):
    return render(request, "profil", active="profil")


@router.get("/statistik")
def statistik(request: Request):
    return render(request, "statistik", active="statistik")


@router.get("/toko")
def toko(request: Request):
    return render(request, "toko", active="klaim")


@router.get("/toko/klaim/{claim_id}")
def toko_klaim(request: Request, claim_id: int):
    return render(request, "toko_klaim", active="klaim", claim_id=claim_id)


@router.get("/tidak-ditemukan")
def tidak_ditemukan(request: Request):
    return templates.TemplateResponse(request, "pages/not_found.html", status_code=404)
