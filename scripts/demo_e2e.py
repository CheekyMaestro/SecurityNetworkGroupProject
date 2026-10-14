"""Skenario demo PRD dari awal sampai akhir lewat HTTP ke server uvicorn sungguhan.

    python scripts/demo_e2e.py               # video 10 MB
    python scripts/demo_e2e.py --video-mb 50

Memakai database, storage, dan secret sementara (tidak menyentuh .env, awan.db, atau storage/ milikmu).
Keluar dengan kode 1 kalau ada langkah yang gagal.
"""

import argparse
import base64
import hashlib
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PASSWORD = "demo-awan-123"
MB = 1024 * 1024

MARKERS = {
    "nama profil": "DzakyPenandaE2E",
    "NIK": "3578123412341234",
    "rekening": "BCA 9988776655",
    "nama barang": "MonitorPenandaE2E",
    "pesan klaim": "PesanKlaimPenandaE2E",
    "isi video": "IsiVideoPenandaE2E",
    "isi invoice": "IsiInvoicePenandaE2E",
    "nama file": "unboxing-penanda-e2e",
}

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> bool:
    results.append((bool(ok), label))
    print(f"  {'OK  ' if ok else 'GAGAL'} {label}")
    return bool(ok)


def step(title: str) -> None:
    print(f"\n== {title}")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_video(size: int) -> bytes:
    head = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + MARKERS["isi video"].encode()
    return head + os.urandom(size - len(head))


def make_pdf() -> bytes:
    return b"%PDF-1.4\n" + MARKERS["isi invoice"].encode() + b"\n" + os.urandom(40 * 1024) + b"\n%%EOF\n"


def make_docx() -> bytes:
    return b"PK\x03\x04\x14\x00\x06\x00" + os.urandom(12 * 1024)


def make_png() -> bytes:
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + os.urandom(30 * 1024)


def upload(c: httpx.Client, category: str, name: str, data: bytes, mime: str, package_id=None) -> httpx.Response:
    fields = {"category": category}
    if package_id is not None:
        fields["package_id"] = str(package_id)
    return c.post("/files", data=fields, files={"file": (name, data, mime)})


def login(base: str, username: str) -> httpx.Client:
    c = httpx.Client(base_url=base, timeout=120)
    r = c.post("/auth/login", json={"username": username, "password": PASSWORD})
    if r.status_code != 200:
        raise SystemExit(f"login {username} gagal: {r.status_code} {r.text}")
    return c


def scenario(base: str, env: dict, video_mb: int) -> None:
    step("Seed akun toko dan pembeli")
    out = subprocess.run([sys.executable, "scripts/seed.py", "--password", PASSWORD],
                         cwd=ROOT, env=env, capture_output=True, text=True)
    check(out.returncode == 0 and "elektra" in out.stdout, "seed membuat elektra, gadgetin, dzaky")
    out2 = subprocess.run([sys.executable, "scripts/seed.py"], cwd=ROOT, env=env, capture_output=True, text=True)
    check(out2.returncode == 0 and out2.stdout.count("sudah ada") == 3, "seed aman dijalankan dua kali")

    anon = httpx.Client(base_url=base)
    step("R7: login dan sesi")
    check(anon.get("/packages").status_code == 401, "tanpa login -> 401")
    bad = anon.post("/auth/login", json={"username": "dzaky", "password": "salah-banget"})
    check(bad.status_code == 401 and bad.json() == {"detail": "Username atau password salah"},
          "password salah -> 401 pesan generik")
    dzaky = login(base, "dzaky")
    me = dzaky.get("/auth/me").json()
    check(me["username"] == "dzaky" and me["role"] == "buyer", "dzaky masuk sebagai pembeli")

    step("R1 + R5: profil terenkripsi tiga kali")
    profile = {
        "full_name": MARKERS["nama profil"], "nik": MARKERS["NIK"], "birth_date": "2004-05-12",
        "gender": "Laki-laki", "nationality": "WNI", "marital_status": "Belum kawin",
        "address": "Jl. Contoh No. 12, Surabaya", "phone": "081234567890",
        "bank_account": MARKERS["rekening"], "religion": None, "health_notes": "Golongan darah O",
    }
    r = dzaky.put("/profile", json={"data": profile})
    check(r.status_code == 200 and set(r.json()["enc_ms"]) == {"aes", "rc4", "des"}, "PUT /profile")
    for alg in ("aes", "rc4", "des"):
        got = dzaky.get("/profile", params={"alg": alg}).json()
        check(got["data"] == profile, f"GET /profile?alg={alg} kembali asli ({got['decrypt_ms']} ms)")

    step("R2: foto KTP")
    ktp = upload(dzaky, "id_card", "ktp-contoh.png", make_png(), "image/png").json()
    check(dzaky.get("/profile").json()["id_card_file_id"] == ktp["id"], "KTP tersimpan dan tertaut ke profil")

    step(f"R3 + R4: simpan unboxing (video {video_mb} MB + 2 dokumen)")
    pkg = dzaky.post("/packages", json={"item_name": MARKERS["nama barang"], "store": "Toko Elektra",
                                        "order_no": "INV/2026/10/0412"}).json()
    video_data = make_video(video_mb * MB)
    t = time.perf_counter()
    video = upload(dzaky, "video", f"{MARKERS['nama file']}.mp4", video_data, "video/mp4", pkg["id"])
    check(video.status_code == 201, f"upload video ({time.perf_counter() - t:.1f} s)")
    video = video.json()
    invoice_data = make_pdf()
    invoice = upload(dzaky, "document", "invoice-elektra.pdf", invoice_data, "application/pdf", pkg["id"]).json()
    upload(dzaky, "document", "kronologi.docx", make_docx(),
           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", pkg["id"])
    check(video["algorithms"] == ["aes", "rc4", "des"], "video punya 3 ciphertext")
    item = dzaky.get("/packages").json()["items"][0]
    check(item["video_file_id"] == video["id"] and item["document_count"] == 2, "brankas menampilkan paket")
    big = upload(dzaky, "id_card", "besar.png", make_png() + os.urandom(5 * MB), "image/png")
    check(big.status_code == 413, f"KTP > 5 MB ditolak 413 ({big.json()['detail']})")
    wrong = upload(dzaky, "document", "virus.pdf", b"MZ" + os.urandom(100), "application/pdf")
    check(wrong.status_code == 400, "file .exe yang diganti nama .pdf ditolak 400")

    step("R6: unduh dalam bentuk asli dengan tiap algoritma")
    for alg in ("aes", "rc4", "des"):
        t = time.perf_counter()
        r = dzaky.get(f"/files/{video['id']}/download", params={"alg": alg})
        check(r.status_code == 200 and sha(r.content) == sha(video_data),
              f"video alg={alg} identik ({time.perf_counter() - t:.1f} s)")
    cd = dzaky.get(f"/files/{invoice['id']}/download", params={"alg": "des"})
    check(cd.content == invoice_data and "invoice-elektra.pdf" in cd.headers["content-disposition"],
          "invoice alg=des identik, nama file asli kembali")

    step("Klaim ke Toko Elektra")
    elektra = login(base, "elektra")
    gadgetin = login(base, "gadgetin")
    check(elektra.get(f"/files/{video['id']}/download").status_code == 404, "Elektra sebelum klaim -> 404")
    stores = {s["store_name"]: s["id"] for s in dzaky.get("/stores").json()["items"]}
    r = dzaky.post("/claims", json={"package_id": pkg["id"], "store_user_id": stores["Toko Elektra"],
                                    "message": MARKERS["pesan klaim"]})
    check(r.status_code == 201 and r.json()["status"] == "diajukan", "pembeli mengajukan klaim")
    claim_id = r.json()["id"]

    step("Admin Toko Elektra meninjau")
    claims = elektra.get("/claims").json()["items"]
    check(len(claims) == 1 and claims[0]["buyer_name"] == MARKERS["nama profil"], "klaim masuk ke Elektra")
    detail = elektra.get(f"/claims/{claim_id}").json()
    check(detail["buyer"] == {"name": MARKERS["nama profil"], "ktp_verified": True}, "nama + KTP terverifikasi")
    check(all(f["category"] != "id_card" for f in detail["files"]) and len(detail["files"]) == 3,
          "toko melihat video + 2 dokumen, tanpa KTP")
    raw = elektra.get(f"/claims/{claim_id}").text
    check(not any(m in raw for m in (MARKERS["NIK"], MARKERS["rekening"], "081234567890")),
          "NIK, HP, rekening tidak terkirim ke toko")
    r = elektra.get(f"/files/{video['id']}/download", params={"alg": "aes"})
    check(r.status_code == 200 and sha(r.content) == sha(video_data), "Elektra memutar video (200, identik)")
    check(elektra.get(f"/files/{ktp['id']}/download").status_code == 404, "Elektra membuka KTP -> 404")
    r = elektra.patch(f"/claims/{claim_id}", json={"status": "ditinjau", "reply": "Kami cek ke kurir dulu."})
    check(r.status_code == 200 and r.json()["status"] == "ditinjau", "Elektra ubah status + balas")

    step("Toko lain dan user lain")
    for alg in ("aes", "rc4", "des"):
        check(gadgetin.get(f"/files/{video['id']}/download", params={"alg": alg}).status_code == 404,
              f"Gadgetin unduh video alg={alg} -> 404")
    check(gadgetin.get(f"/claims/{claim_id}").status_code == 404, "Gadgetin buka klaim -> 404")
    anon.post("/auth/register", json={"username": "penyusup", "password": PASSWORD})
    intruder = login(base, "penyusup")
    check(intruder.get(f"/files/{video['id']}/download").status_code == 404, "pembeli lain unduh -> 404")
    check(intruder.get(f"/packages/{pkg['id']}").status_code == 404, "pembeli lain buka paket -> 404")
    check(intruder.get("/profile").json()["data"]["nik"] is None, "pembeli lain tidak melihat profil dzaky")
    check(dzaky.patch(f"/claims/{claim_id}", json={"status": "diterima"}).status_code == 403,
          "pembeli ubah status klaim -> 403")

    step("Pembeli melihat balasan")
    check(dzaky.get(f"/packages/{pkg['id']}").json()["claim"] == {"id": claim_id, "status": "ditinjau"},
          "status klaim tampil di detail paket")
    bodies = [x["body"] for x in dzaky.get(f"/claims/{claim_id}").json()["replies"]]
    check(bodies == ["Kami cek ke kurir dulu."], "balasan toko terbaca pembeli")

    step("Statistik")
    stats = {s["algorithm"]: s for s in dzaky.get("/stats").json()["per_algorithm"]}
    for alg in ("aes", "rc4", "des"):
        s = stats[alg]
        check(s["avg_enc_ms_per_mb"] is not None and s["avg_dec_ms_per_mb"] is not None,
              f"{alg}: enc {s['avg_enc_ms_per_mb']} ms/MB, dec {s['avg_dec_ms_per_mb']} ms/MB, "
              f"cipher {s['total_cipher_bytes']:,} byte")

    step("Tidak ada plaintext di disk")
    storage = Path(env["STORAGE_DIR"])
    blobs = [p.read_bytes() for p in storage.rglob("*") if p.is_file()]
    db_raw = Path(env["DATABASE_URL"].removeprefix("sqlite:///")).read_bytes()
    check(len(blobs) == 4 * 3, f"storage berisi {len(blobs)} ciphertext: 4 file sah x 3 algoritma, upload yang ditolak tidak bersisa")
    for label, marker in MARKERS.items():
        m = marker.encode()
        check(not any(m in b for b in blobs) and m not in db_raw, f"'{label}' tidak ada di storage maupun database")

    step("Hapus dan keluar")
    before = len(list(storage.rglob("*.bin")))
    check(dzaky.delete(f"/files/{invoice['id']}").status_code == 204, "hapus invoice -> 204")
    check(len(list(storage.rglob("*.bin"))) == before - 3, "3 ciphertext invoice terhapus dari disk")
    check(dzaky.post("/auth/logout").status_code == 200, "logout")
    check(dzaky.get("/packages").status_code == 401, "setelah logout -> 401")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video-mb", type=int, default=10)
    args = parser.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="awan-e2e-"))
    env = {
        **os.environ,
        "MASTER_SECRET": base64.b64encode(os.urandom(32)).decode(),
        "JWT_SECRET": secrets.token_urlsafe(48),
        "DATABASE_URL": f"sqlite:///{(tmp / 'e2e.db').as_posix()}",
        "STORAGE_DIR": str(tmp / "storage"),
        "SESSION_MINUTES": "60",
    }
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                httpx.get(f"{base}/docs", timeout=1)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        scenario(base, env, args.video_mb)
    finally:
        server.terminate()
        server.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [label for ok, label in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} langkah OK")
    for label in failed:
        print(f"  GAGAL: {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
