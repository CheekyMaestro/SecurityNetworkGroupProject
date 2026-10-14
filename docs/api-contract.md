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

Aturan isi (salah → 400 dengan pesan per field, mis. `{"detail": "NIK wajib 16 digit angka"}`):
- `nik` tepat 16 digit angka (tanpa spasi/tanda hubung di tengah).
- `birth_date` format `YYYY-MM-DD` (nilai dari `<input type="date">`), tidak boleh di masa depan.
- Spasi di awal/akhir dibuang. `religion`/`health_notes` berisi `""` disimpan sebagai `null`.
- Batas panjang: alamat 500, riwayat kesehatan 1000, nama 200 karakter.

`GET /profile` sebelum profil pernah disimpan: `data` semua `null`, `decrypt_ms` dan `updated_at` `null`. `id_card_file_id` tetap terisi kalau foto KTP sudah diunggah lebih dulu.

## Paket dan file

`POST /packages` → **201**, bentuk sama dengan satu item `GET /packages` (`video_file_id` `null`, `document_count` 0, `total_size_bytes` 0).

`POST /files`: **urutan field penting**. `category` (dan `package_id` kalau ada) harus di-`append` ke `FormData` **sebelum** `file`, karena server mengenkripsi file sambil menerimanya dan perlu tahu batas ukuran sejak awal.

```js
const fd = new FormData();
fd.append("category", "video");
fd.append("package_id", "3");     // opsional; jangan untuk id_card
fd.append("file", input.files[0]); // terakhir
```

Gagal:
- format, kategori, atau isi file tidak cocok dengan ekstensinya → **400**, mis. `{"detail": "Format video yang diterima: mkv, mov, mp4"}`
- terlalu besar → **413**, mis. `{"detail": "Ukuran video maksimal 100 MB"}` (KTP 5 MB, dokumen 20 MB)
- `category` dikirim setelah `file` → **400** `{"detail": "Field category harus dikirim sebelum file"}`
- `package_id` bukan milik user → **404**; `package_id` untuk `id_card` → **400**
- file kosong → **400**

`GET /files/{id}/download?alg=aes` → **200** isi file asli dengan `Content-Type` sesuai file dan `Content-Disposition` berisi nama asli. Bisa dipakai langsung sebagai `src` `<video>`/`<img>`. Untuk video: bisa diputar, tapi belum bisa dimajukan (seek) karena belum mendukung HTTP Range.

`DELETE /files/{id}` → **204** tanpa body.

## Klaim

Yang dilihat toko pada klaim ke tokonya: video dan dokumen paket itu, nama barang, no. pesanan, nama pembeli, status "KTP terverifikasi" (ya/tidak), pesan, dan balasan. Toko **tidak** menerima NIK, HP, alamat, rekening, atau foto KTP.

`POST /claims` gagal:
- paket bukan milik pembeli, atau `store_user_id` bukan toko → **404**
- paket masih punya klaim berstatus `diajukan`/`ditinjau` → **400** `{"detail": "Paket ini masih punya klaim yang berjalan"}`
- paket belum punya video/dokumen → **400**

File yang ditambahkan ke paket selama klaim masih `diajukan`/`ditinjau` (mis. setelah toko memilih "Minta bukti tambahan") otomatis ikut terbuka untuk toko itu.

`video_file_id` di `GET /claims` dan `files` di `GET /claims/{id}` hanya berisi file yang boleh dibuka oleh user yang sedang login.

`POST /claims/{id}/replies` body `{"body": "..."}` → **201**, bentuk satu item `replies` di `GET /claims/{id}`:

```json
{"id": 2, "author_role": "buyer", "author_name": "Dzaky A.", "body": "Baik, saya tunggu.", "created_at": "2026-10-13T10:00:00+07:00"}
```

`PATCH /claims/{id}`: `reply` boleh dikosongkan atau tidak dikirim.
