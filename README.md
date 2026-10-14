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
