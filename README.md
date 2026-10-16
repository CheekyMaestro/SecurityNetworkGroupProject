# Awan — Brankas Bukti Unboxing

Tugas 1 Keamanan Informasi (ITS). Web app untuk menyimpan data pribadi, foto KTP, dokumen, dan video unboxing yang dienkripsi dengan AES, RC4, dan DES.

Spesifikasi lengkap: [`docs/PRD.md`](docs/PRD.md).

## Branch

| Branch | Isi | Pemegang |
| --- | --- | --- |
| `main` | Versi gabungan yang sudah jalan | semua |
| `fe` | Halaman, CSS, JS, mock API | Dzaky |
| `be` | Model, auth, endpoint API, modul enkripsi | Yae, Anggota 2 |

## Struktur folder (disepakati)

```
app/
  main.py              # FastAPI app: mount static, include semua router
  routes/
    pages.py           # FE: route GET yang me-render template
    auth.py, profile.py, packages.py, files.py, claims.py, stats.py   # BE: endpoint API
  templates/           # FE
  static/              # FE (css, js, img, mock)
  models.py, db.py     # BE
  crypto/              # BE: aes.py, rc4.py, des.py, keys.py, vault.py
storage/               # ciphertext file (tidak di-commit)
docs/
tests/
```

## Menjalankan

```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Buka http://localhost:8000/masuk. Tambahkan `?mock=1` untuk memakai data contoh tanpa backend.

### Backend: isi `.env`

```
python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"   # -> MASTER_SECRET
python -c "import secrets;print(secrets.token_urlsafe(48))"                     # -> JWT_SECRET
```

Aplikasi menolak start kalau `MASTER_SECRET` atau `JWT_SECRET` kosong. Jangan bagikan `.env`: siapa pun yang memegang `MASTER_SECRET` bisa menurunkan semua kunci user.

- Dokumentasi API interaktif: http://localhost:8000/docs
- Contoh JSON untuk endpoint yang belum dicontohkan PRD: [`docs/api-contract.md`](docs/api-contract.md)
- Test: `pytest -q`; skenario demo lewat server sungguhan: `python scripts/demo_e2e.py`
- Hasil pengujian dan keterbatasan: [`docs/hasil-pengujian.md`](docs/hasil-pengujian.md)

### Akun demo

```
python scripts/seed.py                     # password acak per akun dicetak di terminal
python scripts/seed.py --password rahasia1 # atau satu password untuk semua akun baru
```

Membuat `elektra` (Toko Elektra), `gadgetin` (Toko Gadgetin), dan pembeli `dzaky`. Aman dijalankan berulang; akun yang sudah ada tidak diubah.

Belum ada migrasi database. Kalau skema berubah setelah `git pull`, hapus `awan.db` dan folder `storage/`, lalu jalankan seed lagi.
