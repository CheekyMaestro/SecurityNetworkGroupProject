# Kontrak API: pelengkap PRD

Bentuk JSON utama ada di [`docs/PRD.md`](PRD.md) bagian "Contoh JSON response". File ini hanya berisi yang **belum** dicontohkan di sana. Kalau ada yang bertentangan, PRD yang menang. Semua endpoint bisa dicoba lewat `http://localhost:8000/docs`.

## Aturan umum

- Error selalu `{"detail": "pesan untuk user"}`, langsung bisa ditampilkan.
- Status error: **400** input salah (termasuk `alg` selain `aes`/`rc4`/`des`), **401** belum login atau sesi habis, **403** salah peran, **404** tidak ada atau bukan haknya, **413** file terlalu besar.
- **403 (tambahan dari PRD)**: pembeli memanggil endpoint khusus toko (`PATCH /claims/{id}`), atau toko memanggil endpoint khusus pembeli (`/profile`, `/packages`, `POST /files`, `/stats`, `/stores`, `POST /claims`). Saran: arahkan ke beranda perannya.

## Auth

`POST /auth/register` body `{"username": "dzaky", "password": "minimal8"}` → **201**, bentuk sama dengan `/auth/me`, dan cookie sesi langsung dipasang (masuk otomatis, tidak perlu memanggil login lagi).

- Username 3 sampai 32 karakter `[a-zA-Z0-9_]`, password minimal 8 karakter. Salah format → 400.
- Username sudah dipakai → 400 `{"detail": "Username sudah dipakai"}`.

`POST /auth/login` salah → **401** `{"detail": "Username atau password salah"}`.

`POST /auth/logout` → **200** `{"ok": true}`.

## Profil

`PUT /profile` body `{"data": {...11 field}}`. `religion` dan `health_notes` boleh `null`, field lain wajib diisi. → **200**

```json
{"updated_at": "2026-10-14T10:12:00+07:00", "enc_ms": {"aes": 0.31, "rc4": 0.12, "des": 0.55}}
```

`enc_ms` = waktu enkripsi profil per algoritma (ms), bisa ditampilkan di mode demo.

## Paket dan file

`POST /packages` → **201**, bentuk sama dengan satu item `GET /packages` (`video_file_id` `null`, `document_count` 0, `total_size_bytes` 0).

`POST /files` gagal:
- format atau kategori salah → **400**, mis. `{"detail": "Format file tidak didukung. Video: mp4, mkv, mov"}`
- terlalu besar → **413**, mis. `{"detail": "Ukuran video maksimal 100 MB"}`

`GET /files/{id}/download?alg=aes` → **200** isi file asli dengan `Content-Type` sesuai file dan `Content-Disposition` berisi nama asli. Bisa dipakai langsung sebagai `src` `<video>`/`<img>`. Untuk video: bisa diputar, tapi belum bisa dimajukan (seek) karena belum mendukung HTTP Range.

`DELETE /files/{id}` → **204** tanpa body.

## Klaim

`POST /claims/{id}/replies` body `{"body": "..."}` → **201**, bentuk satu item `replies` di `GET /claims/{id}`:

```json
{"id": 2, "author_role": "buyer", "author_name": "Dzaky A.", "body": "Baik, saya tunggu.", "created_at": "2026-10-13T10:00:00+07:00"}
```

`PATCH /claims/{id}`: `reply` boleh dikosongkan atau tidak dikirim.
