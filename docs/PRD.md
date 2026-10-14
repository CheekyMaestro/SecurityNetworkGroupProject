# PRD Gabungan — Awan: Brankas Bukti Unboxing

Assignment 1 Keamanan Informasi · Oct 14, 2026 · disusun dari PRD @yae + lapisan user oleh @Omotopuawa

## Ringkasan

Kita membangun **Awan**, brankas pribadi tempat pembeli online menyimpan bukti unboxing (video, invoice, KTP, data pribadi). Semua data dienkripsi dengan AES, RC4, dan DES, lalu bisa diambil lagi dalam bentuk asli setelah login dengan username dan password.

Dokumen ini memakai **PRD Yae sebagai dasar**: scope, desain enkripsi, skema database, dan API tetap. Yang ditambahkan adalah lapisan dari sisi user. Empat perubahan utama:

1. **Bingkai cerita unboxing**, supaya jelas kenapa user menyimpan video dan dokumen di sini. Endpoint dan skema tidak berubah, hanya label dan tampilan.
2. **Peran admin toko** yang hanya bisa membuka bukti dari klaim yang diajukan ke tokonya. Ini bukti bahwa kunci benar-benar dipakai: pihak yang diberi akses bisa mendekripsi, pihak lain tidak.
3. **Agama dan riwayat kesehatan jadi field opsional** (minimisasi data menurut UU PDP), tetap ada sebagai contoh kategori spesifik di laporan.
4. **User journey, state umpan balik, dan desain halaman** ditulis dari sudut pandang user, dengan baseline UI Supabase dan warna langit.

Fokus penilaian tetap di enkripsi dan penyimpanan. Semua tools gratis dan jalan di localhost.

## Sudut pandang user

User kita adalah pembeli online yang sering belanja barang bernilai, dan pernah atau takut menerima paket rusak. Ia menyimpan bukti di Awan karena bukti itu berisi data sensitif dan baru dibutuhkan berminggu-minggu kemudian.

**Skenario demo.** Dzaky membeli monitor. Saat paket datang, ia merekam unboxing dan menyimpannya ke Awan bersama invoice PDF. Seminggu kemudian layarnya bergaris. Ia membuka Awan, mengunduh video dan invoice dalam bentuk asli, lalu mengirimkannya ke toko lewat marketplace.

Setiap jenis data punya alasan yang masuk akal bagi user:

| Data | Kenapa user menyimpannya | Requirement |
| --- | --- | --- |
| Profil pribadi | Identitas dan rekening refund siap pakai saat mengajukan komplain | R1 |
| Foto KTP | Marketplace sering meminta verifikasi identitas penerima untuk klaim | R2 |
| Invoice / kronologi / rekap belanja (PDF, DOC, XLS) | Bukti transaksi dan cerita kejadian | R3 |
| Video unboxing | Bukti utama bahwa barang rusak sejak dibuka | R4 |

Yang dirasakan user: semua buktinya aman di satu tempat, hanya ia yang bisa membuka, dan file kembali utuh saat dibutuhkan.

## Scope

Assignment 1 punya dua peran: **pembeli** yang mengelola datanya sendiri, dan **admin toko** yang hanya bisa membuka bukti dari klaim yang diajukan ke tokonya. Admin toko dipertahankan karena menjadi demonstrasi paling jelas bahwa kunci dipakai: toko yang dituju bisa mendekripsi, toko lain dan user lain tidak bisa.

**Dikerjakan sekarang:**

- Register dan login dengan username dan password
- Profil pribadi (11 field, 2 opsional) disimpan terenkripsi
- Upload foto KTP, dokumen PDF/DOC/XLS, dan video unboxing
- Enkripsi setiap data dengan AES, RC4, dan DES (tiga ciphertext terpisah)
- Lihat dan unduh data dalam bentuk terdekripsi, dengan pilihan algoritma di mode demo
- Ajukan klaim ke satu toko; kunci file paket dibungkus ulang untuk admin toko itu
- Admin toko melihat klaim masuk, membuka video dan dokumen, lalu mengubah status dan membalas
- Tiap user hanya bisa mengakses data miliknya sendiri atau yang dibagikan kepadanya
- Halaman statistik waktu dan ukuran per algoritma

**Ditunda ke Assignment 2:**

- Surat kronologi otomatis (.docx) dari form
- Chat real-time dan notifikasi email
- Registrasi toko (akun toko dibuat lewat seed)

**Tidak dikerjakan:** deploy ke cloud, lupa password, verifikasi email, rekam kamera langsung, responsive mobile, dark mode.

## Requirement dan fitur

Setiap poin di slide tugas punya satu fitur dan satu halaman, supaya tidak ada yang terlewat saat demo.

| ID | Requirement di slide | Fitur | Halaman |
| --- | --- | --- | --- |
| R1 | Store user's private data in a database | Form profil, isi dienkripsi lalu disimpan di tabel | Profil & KTP |
| R2 | Store user's ID card image | Upload JPG/PNG kategori KTP | Profil & KTP |
| R3 | Store user's PDF/DOC/XLS files | Upload dokumen (pdf, doc, docx, xls, xlsx), dikaitkan ke paket | Simpan unboxing, Detail paket |
| R4 | Store user's video files | Upload video unboxing (mp4, mkv, mov) | Simpan unboxing |
| R5 | Encrypted with AES, RC4, DES | Tiga ciphertext per data, satu per algoritma | Semua upload dan simpan profil |
| R6 | Retrieve decrypted data | Lihat profil dan unduh file; mode demo bisa memilih algoritma; admin toko membuka bukti klaim | Detail paket, Profil |
| R7 | Username and password | Register, login, cek kepemilikan di setiap endpoint | Masuk, Daftar |

Batas ukuran upload: KTP 5 MB, dokumen 20 MB, video 100 MB. Karena tiap file disimpan tiga kali, satu video 100 MB memakan sekitar 300 MB di disk.

## Data pribadi yang disimpan

Form profil berisi 11 field dari PRD Yae. Dua field ditandai **opsional** karena tidak dibutuhkan untuk tujuan aplikasi (prinsip minimisasi data UU PDP), tapi tetap disediakan sebagai contoh data kategori spesifik di laporan.

| Field | Wajib? | Kategori UU PDP | Kategori GDPR | Dipakai untuk |
| --- | --- | --- | --- | --- |
| Nama lengkap | Wajib | Umum | Personal data | Identitas penerima |
| NIK | Wajib | Umum (kombinasi) | Personal data (identification number) | Verifikasi klaim |
| Tanggal lahir | Wajib | Umum (kombinasi) | Personal data | Verifikasi identitas |
| Jenis kelamin | Wajib | Umum | Personal data | Data KTP |
| Kewarganegaraan | Wajib | Umum | Personal data | Data KTP |
| Status perkawinan | Wajib | Umum | Personal data | Data KTP |
| Alamat | Wajib | Umum (kombinasi) | Personal data | Alamat pengiriman |
| Nomor telepon | Wajib | Umum (kombinasi) | Personal data | Kontak klaim |
| Nomor rekening bank | Wajib | Spesifik (keuangan pribadi) | Personal data | Refund |
| Agama | Opsional | Umum | Special category | Contoh kategori khusus GDPR |
| Riwayat kesehatan / golongan darah | Opsional | Spesifik | Special category | Contoh kategori spesifik |

Foto KTP juga data pribadi karena memuat NIK, foto wajah, dan alamat sekaligus. Kategori di tabel perlu dicek ulang ke teks pasalnya (UU No. 27 Tahun 2022, GDPR Pasal 4 dan 9) sebelum dikutip di laporan.

Di form, field opsional diberi keterangan "Opsional, boleh dikosongkan". Untuk demo, pakai data dummy. **Jangan upload KTP asli.**

## User journey

Alur ini ditulis dari sisi user. Kolom server mengikuti user flow di PRD Yae, jadi kedua sisi bertemu di endpoint yang sama.

| # | Yang user lakukan | Yang user lihat | Yang terjadi di server |
| --- | --- | --- | --- |
| 1 | Daftar dengan username dan password | Form singkat, catatan "Datamu akan dienkripsi" | Hash password (bcrypt), buat `key_salt` |
| 2 | Masuk | Diarahkan ke Brankas | Verifikasi password, set cookie session |
| 3 | Lengkapi profil dan unggah foto KTP | Form 11 field (2 opsional), pratinjau foto sebelum disimpan | Profil dan KTP dienkripsi 3 kali |
| 4 | Paket datang: simpan unboxing | Pilih video, isi nama barang, toko, no. pesanan, lampirkan invoice; progress bar | Video dan dokumen dienkripsi per potongan, 3 ciphertext |
| 5 | Buka Brankas | Daftar paket dengan video, dokumen, status "Terenkripsi" | Daftar metadata milik user |
| 6 | Barang ternyata rusak: buka detail paket | Putar video, lihat daftar dokumen | Dekripsi saat diminta |
| 7 | Unduh bukti | File asli terunduh, nama file kembali seperti semula | Dekripsi dari algoritma terpilih (default AES) |
| 8 | Keluar | Kembali ke halaman masuk | Cookie session dihapus |

Lanjutan saat barang rusak, dari pembeli ke admin toko:

| # | Siapa | Yang dilakukan | Yang dilihat | Yang terjadi di server |
| --- | --- | --- | --- | --- |
| 9 | Pembeli | Ajukan klaim dari detail paket: pilih toko, tulis keluhan | Ringkasan file yang akan dibuka toko + catatan "NIK, HP, dan rekening tidak ikut dibagikan" | Kunci file paket dibuka dengan kunci pembeli, lalu dibungkus ulang dengan kunci admin toko |
| 10 | Admin toko | Masuk dan buka Klaim masuk | Daftar klaim untuk tokonya saja | Query klaim dengan `store_user_id` = dirinya |
| 11 | Admin toko | Buka klaim | Video bisa diputar, invoice dan dokumen bisa diunduh, nama pembeli tanpa data sensitif | Kunci dibuka dengan kunci toko, file didekripsi |
| 12 | Admin toko | Ubah status, tulis balasan | Status berubah di sisi pembeli | Balasan dienkripsi |
| 13 | Toko lain / user lain | Coba buka URL file yang sama | Halaman 404 | Tidak ada kunci terbungkus untuknya, jadi file tidak bisa didekripsi |

Mode demo (untuk presentasi, bukan user biasa) ditampilkan di detail paket dan profil: user bisa memilih AES, RC4, atau DES untuk dekripsi dan melihat ketiganya menghasilkan file yang sama.

## Halaman dan state umpan balik

Lima halaman PRD Yae tetap dipakai, dengan nama dan isi yang mengikuti cerita unboxing. Satu halaman statistik ditambahkan untuk demo.

| Halaman (PRD Yae) | Nama di aplikasi | Isi | Endpoint |
| --- | --- | --- | --- |
| Register | Daftar | Username, password, konfirmasi password | `POST /auth/register` |
| Login | Masuk | Panel langit + maskot di kiri, form di kanan | `POST /auth/login` |
| Dashboard | Brankas saya | Stat tile (paket, dokumen, ukuran terenkripsi), tabel paket unboxing, tombol Simpan unboxing | `GET /files` |
| File | Simpan unboxing + Detail paket | Upload video dan dokumen; detail berisi player, daftar dokumen, Unduh, Hapus, mode demo pilih algoritma | `POST /files`, `GET /files/{id}/download`, `DELETE /files/{id}` |
| Profil | Profil & KTP | 11 field, foto KTP, NIK disamarkan dengan tombol tampilkan | `GET/PUT /profile`, `POST /files` (category `id_card`) |
| (baru) | Statistik enkripsi | Waktu dan ukuran per algoritma, tabel dan grafik | `GET /stats` |

Halaman admin toko (top bar dengan label "Toko", tanpa menu profil pribadi):

| Halaman | Isi | Endpoint |
| --- | --- | --- |
| Klaim masuk | Filter status, grid kartu klaim (thumbnail, nama barang, no. pesanan, pembeli, badge status) | `GET /claims` |
| Tinjau klaim | Player video, daftar dokumen dengan Unduh, nama pembeli + "KTP terverifikasi", pilihan Terima / Tolak / Minta bukti tambahan, balasan | `GET /claims/{id}`, `GET /files/{id}/download`, `PATCH /claims/{id}` |

Di sisi pembeli, detail paket mendapat tombol **Ajukan klaim** dan panel status klaim serta balasan toko.

State yang wajib ada di setiap halaman, supaya user tidak bingung saat sesuatu tidak berjalan:

| Situasi | Yang ditampilkan |
| --- | --- |
| Brankas masih kosong | Maskot awan + "Belum ada unboxing tersimpan" + tombol Simpan unboxing |
| Upload berjalan | Progress bar per file, tombol simpan nonaktif |
| Upload selesai | Toast "Tersimpan dan terenkripsi" |
| File melebihi batas / format ditolak | Pesan di bawah field: batas ukuran dan format yang diterima |
| Username atau password salah | Pesan di atas form, tanpa menyebut mana yang salah |
| Sesi habis (60 menit) | Diarahkan ke Masuk dengan pesan "Sesi berakhir, silakan masuk lagi"; upload besar memperpanjang sesi atau memberi peringatan sebelum habis |
| Hapus file | Dialog konfirmasi "File akan dihapus permanen" |
| File milik orang lain / tidak ada | Halaman 404 biasa |

## Desain enkripsi

Desain enkripsi diambil utuh dari PRD Yae. Setiap data dienkripsi terpisah dengan ketiga algoritma, jadi satu data menghasilkan tiga ciphertext yang bisa dibandingkan waktu dan ukurannya.

| Algoritma | Mode | Panjang key | IV / nonce | Padding |
| --- | --- | --- | --- | --- |
| AES | CBC | 32 byte (AES-256) | IV acak 16 byte | PKCS7 |
| DES | CBC | 8 byte (efektif 56 bit) | IV acak 8 byte | PKCS7 |
| RC4 | Stream | 16 byte | Nonce acak 16 byte | Tidak ada |

Semua memakai PyCryptodome (`AES`, `DES`, `ARC4`).

**Manajemen key**

- Satu master secret di `.env`, tidak ikut di-commit.
- Tiap user punya `key_salt` acak 16 byte yang dibuat saat register.
- Key user diturunkan dengan HKDF-SHA256 dari master secret dan `key_salt` (56 byte, dipotong jadi AES 32, RC4 16, DES 8). Key tidak pernah disimpan.
- IV dan nonce baru untuk setiap enkripsi, disimpan di samping ciphertext.

**Hal teknis**

- Key RC4 per data = 16 byte pertama `HMAC-SHA256(key RC4 user, nonce)`, supaya key RC4 tidak pernah dipakai dua kali. Dengan kunci file acak (bagian berikut), key RC4 otomatis baru untuk setiap file.
- File besar dienkripsi per potongan 64 KB secara streaming.
- Nama file asli ikut dienkripsi; nama file di disk memakai UUID.
- Waktu enkripsi tiap algoritma dicatat (ms) untuk laporan.
- RC4 dan DES sudah tidak aman untuk sistem nyata, dipakai karena syarat tugas. Ini ditulis di laporan.
- Integritas (HMAC-SHA256 per ciphertext) ditambahkan kalau ada waktu.

### Berbagi ke admin toko: kunci dibungkus per penerima

Agar akses toko terbukti secara kriptografis (bukan sekadar cek izin), kunci file dipisah dari kunci user:

1. Saat upload, server membuat **kunci file acak** per algoritma (AES 32, RC4 16, DES 8 byte). Isi file dienkripsi dengan kunci ini, tiga ciphertext seperti di atas.
2. Kunci file tidak disimpan polos. Kunci itu **dibungkus** (AES-256-GCM) dengan kunci AES pemilik hasil HKDF, lalu disimpan di tabel `file_keys` sebagai baris milik pemilik.
3. Saat klaim diajukan, server membuka bungkus dengan kunci pemilik, lalu **membungkus ulang dengan kunci admin toko yang dituju** (HKDF dari `key_salt` admin toko). Hasilnya baris baru di `file_keys` untuk toko itu.
4. Saat unduh, server mencari baris `file_keys` untuk pasangan (file, user yang login). Tidak ada baris = tidak ada kunci = 404.

Yang bisa ditunjukkan saat demo: tabel `file_keys` untuk satu video hanya berisi baris pemilik dan Toko Elektra. Toko lain tidak punya baris, jadi walaupun ciphertext-nya ada di disk, mereka tidak punya kunci untuk membukanya.

Data profil (NIK, HP, alamat, rekening) **tidak pernah** dibungkus untuk toko. Toko hanya menerima nama pembeli dan status KTP terverifikasi.

Catatan untuk laporan: server tetap memegang master secret, jadi secara teori server bisa menurunkan semua kunci. Enkripsi end-to-end (kunci hanya di perangkat user) di luar scope tugas ini.

**Fallback kalau waktu mepet:** pakai desain HKDF Yae apa adanya, dan akses toko cukup dicek lewat `claims.store_user_id`. Demonya tetap jalan, tapi buktinya lewat izin, bukan lewat kunci.

## Arsitektur, skema, dan API

Satu server FastAPI melayani API JSON dan halaman Jinja2, dengan SQLite dan folder `storage/`. Stack dari PRD Yae tidak berubah: Python 3.11+, FastAPI, SQLAlchemy, PyCryptodome, passlib bcrypt, JWT di cookie HttpOnly (60 menit). Halaman frontend memanggil API lewat `fetch`.

&#91;embedded content: alur upload · 3 algoritma, 2 tempat simpan\]

Saat unduh alurnya dibalik: server mengambil satu ciphertext sesuai algoritma yang dipilih, mendekripsinya, lalu mengirim file asli ke browser.

### Skema database

Empat tabel dari PRD Yae, ditambah satu tabel kecil `packages` untuk mengelompokkan video dan dokumen per paket.

| Tabel | Kolom | Keterangan |
| --- | --- | --- |
| `users` | id, username (unik), password\_hash, key\_salt, created\_at | Dari PRD Yae |
| `profile_ciphertexts` | id, user\_id, algorithm, iv, ciphertext, enc\_time\_ms, updated\_at | Dari PRD Yae, 3 baris per user |
| `files` | id, user\_id, **package\_id (nullable)**, category, name\_iv, name\_ciphertext, mime\_type, size\_bytes, created\_at | Dari PRD Yae + `package_id`. `category`: `id_card`, `document`, `video` |
| `file_ciphertexts` | id, file\_id, algorithm, iv, storage\_path, enc\_time\_ms | Dari PRD Yae, 3 baris per file |
| `packages` | id, user\_id, meta\_iv, meta\_ciphertext, created\_at | **Baru.** `meta` = JSON terenkripsi AES berisi nama barang, toko, no. pesanan |

Tambahan untuk peran admin toko:

| Tabel | Kolom | Keterangan |
| --- | --- | --- |
| `users` | + **role** (`buyer` / `store`), + **store\_name** (nullable) | Akun toko dibuat lewat seed |
| `file_keys` | id, file\_id, user\_id, algorithm, wrap\_nonce, wrapped\_key, wrap\_tag | **Baru.** Satu baris per (file, penerima, algoritma): pemilik saat upload, toko saat klaim |
| `claims` | id, package\_id, buyer\_id, store\_user\_id, status, message\_iv, message\_ciphertext, created\_at, updated\_at | **Baru.** Status: `diajukan`, `ditinjau`, `diterima`, `ditolak` |
| `claim_replies` | id, claim\_id, author\_id, body\_iv, body\_ciphertext, created\_at | **Baru.** Balasan dienkripsi AES |

`file_ciphertexts` tetap seperti di PRD Yae (tanpa kolom kunci). Semua kunci file tersimpan terbungkus di `file_keys`.

### API endpoint

Semua endpoint PRD Yae tetap. Tambahannya hanya tiga endpoint paket dan field `package_id` saat upload.

| Method | Path | Fungsi |
| --- | --- | --- |
| POST | `/auth/register` | Buat akun |
| POST | `/auth/login` | Verifikasi password, set cookie |
| POST | `/auth/logout` | Hapus cookie |
| GET | `/profile?alg=aes` | Profil terdekripsi dari algoritma terpilih |
| PUT | `/profile` | Simpan profil, dienkripsi 3 kali |
| POST | `/packages` | **Baru.** Buat paket (nama barang, toko, no. pesanan) |
| GET | `/packages` | **Baru.** Daftar paket milik user beserta jumlah file |
| GET | `/packages/{id}` | **Baru.** Detail paket + daftar file-nya |
| POST | `/files` | Upload multipart: `file`, `category`, `package_id` (opsional) |
| GET | `/files?category=video` | Daftar file milik user |
| GET | `/files/{id}/download?alg=des` | Unduh file terdekripsi |
| DELETE | `/files/{id}` | Hapus file + 3 ciphertext |
| GET | `/stats` | Waktu dan ukuran per algoritma |

Endpoint tambahan untuk klaim dan toko:

| Method | Path | Siapa | Fungsi |
| --- | --- | --- | --- |
| GET | `/stores` | Pembeli | Daftar admin toko untuk dipilih saat klaim |
| POST | `/claims` | Pembeli | Ajukan klaim (`package_id`, `store_user_id`, `message`); kunci file paket dibungkus ulang untuk toko |
| GET | `/claims` | Keduanya | Pembeli: klaim miliknya. Toko: klaim yang masuk ke tokonya |
| GET | `/claims/{id}` | Keduanya | Detail klaim, daftar file, balasan |
| PATCH | `/claims/{id}` | Toko | Ubah status + tambah balasan |
| POST | `/claims/{id}/replies` | Keduanya | Tambah balasan |

`GET /files/{id}/download` tidak berubah, tapi sekarang mengecek `file_keys`: toko yang punya baris kunci untuk file itu bisa mengunduh.

Parameter `alg` default `aes`. File milik user lain dijawab 404.

### Contoh JSON response (kontrak FE ↔ BE)

FE membuat mock dengan bentuk persis seperti ini; BE mengembalikan bentuk yang sama. Kalau ada perubahan, ubah di sini dulu.

`GET /profile?alg=aes`

```json
{
  "algorithm": "aes",
  "decrypt_ms": 0.42,
  "updated_at": "2026-10-14T10:12:00+07:00",
  "data": {
    "full_name": "Dzaky A.",
    "nik": "3578xxxxxxxxxxxx",
    "birth_date": "2004-05-12",
    "gender": "Laki-laki",
    "nationality": "WNI",
    "marital_status": "Belum kawin",
    "address": "Jl. Contoh No. 12, Surabaya",
    "phone": "0812xxxxxxxx",
    "bank_account": "BCA 1234xxxxxx",
    "religion": null,
    "health_notes": null
  },
  "id_card_file_id": 7
}
```

`GET /packages`

```json
{
  "items": [
    {
      "id": 3,
      "item_name": "Monitor 24 inci",
      "store": "Toko Elektra",
      "order_no": "INV/2026/10/0412",
      "created_at": "2026-10-11T16:45:00+07:00",
      "video_file_id": 12,
      "document_count": 2,
      "total_size_bytes": 190840112
    }
  ]
}
```

`GET /files?category=video`

```json
{
  "items": [
    {
      "id": 12,
      "package_id": 3,
      "category": "video",
      "name": "unboxing-monitor.mp4",
      "mime_type": "video/mp4",
      "size_bytes": 190601216,
      "created_at": "2026-10-11T16:45:00+07:00",
      "algorithms": ["aes", "rc4", "des"]
    }
  ]
}
```

`GET /stats`

```json
{
  "per_algorithm": [
    {"algorithm": "aes", "avg_enc_ms_per_mb": 4.1, "avg_dec_ms_per_mb": 3.9, "total_cipher_bytes": 191004672},
    {"algorithm": "rc4", "avg_enc_ms_per_mb": 2.7, "avg_dec_ms_per_mb": 2.6, "total_cipher_bytes": 190601216},
    {"algorithm": "des", "avg_enc_ms_per_mb": 21.8, "avg_dec_ms_per_mb": 21.2, "total_cipher_bytes": 191004680}
  ],
  "per_category": [
    {"category": "video", "algorithm": "aes", "avg_enc_ms_per_mb": 4.0}
  ]
}
```

`GET /auth/me` (**baru**, dipakai FE untuk tahu siapa yang login dan perannya; juga bentuk response `POST /auth/login`)

```json
{"id": 1, "username": "dzaky", "role": "buyer", "store_name": null}
```

`GET /packages/{id}`

```json
{
  "id": 3,
  "item_name": "Monitor 24 inci",
  "store": "Toko Elektra",
  "order_no": "INV/2026/10/0412",
  "created_at": "2026-10-11T16:45:00+07:00",
  "files": [
    {"id": 12, "package_id": 3, "category": "video", "name": "unboxing-monitor.mp4", "mime_type": "video/mp4", "size_bytes": 190601216, "created_at": "2026-10-11T16:45:00+07:00", "algorithms": ["aes", "rc4", "des"]},
    {"id": 13, "package_id": 3, "category": "document", "name": "invoice-elektra.pdf", "mime_type": "application/pdf", "size_bytes": 2888, "created_at": "2026-10-11T16:46:00+07:00", "algorithms": ["aes", "rc4", "des"]}
  ],
  "claim": {"id": 5, "status": "ditinjau"}
}
```

`GET /stores`

```json
{"items": [{"id": 21, "store_name": "Toko Elektra"}, {"id": 22, "store_name": "Sportiva"}]}
```

`POST /claims` body `{"package_id": 3, "store_user_id": 21, "message": "Layar retak di pojok kanan bawah"}` → 201 `{"id": 5, "status": "diajukan"}`

`GET /claims` (pembeli: klaim miliknya; toko: klaim yang masuk)

```json
{
  "items": [
    {"id": 5, "package_id": 3, "item_name": "Monitor 24 inci", "order_no": "INV/2026/10/0412", "buyer_name": "Dzaky A.", "store_name": "Toko Elektra", "status": "ditinjau", "video_file_id": 12, "created_at": "2026-10-12T14:20:00+07:00"}
  ]
}
```

`GET /claims/{id}`

```json
{
  "id": 5,
  "status": "ditinjau",
  "message": "Layar retak di pojok kanan bawah",
  "created_at": "2026-10-12T14:20:00+07:00",
  "package": {"id": 3, "item_name": "Monitor 24 inci", "order_no": "INV/2026/10/0412"},
  "buyer": {"name": "Dzaky A.", "ktp_verified": true},
  "store": {"id": 21, "store_name": "Toko Elektra"},
  "files": [{"id": 12, "category": "video", "name": "unboxing-monitor.mp4", "mime_type": "video/mp4", "size_bytes": 190601216}],
  "replies": [{"id": 1, "author_role": "store", "author_name": "Toko Elektra", "body": "Video sudah kami terima, kami cek ke kurir dulu.", "created_at": "2026-10-13T09:05:00+07:00"}]
}
```

`PATCH /claims/{id}` body `{"status": "diterima", "reply": "Kami ganti unit baru."}` → bentuk sama dengan `GET /claims/{id}`.

`POST /files` (multipart: `file`, `category`, `package_id`) → 201 dengan satu objek file seperti di `GET /files`.

Angka di contoh hanya ilustrasi bentuk, bukan hasil ukur. Error memakai bentuk `{"detail": "pesan untuk user"}` dengan status 400, 401, 404, atau 413.

## Desain visual

Tampilan mengikuti struktur dashboard **Supabase** (halaman "Idea Dump" di [file Figma](https://www.figma.com/design/hE8Oo6WJlXG3gXBmG1mVXo/Brankas-Unboxing-%E2%80%94-Foundations?node-id=19-1629)), dengan **tema terang** dan **warna langit** menggantikan hijau Supabase. Ini tidak dinilai, jadi cukup konsisten dan rapi.

| Elemen | Ketentuan |
| --- | --- |
| Font | Manrope SemiBold untuk judul (halaman 22, bagian 18); Inter Medium 13/12 untuk teks UI; Source Code Pro untuk label kapital dan data teknis |
| Layout | Top bar 48 px, icon rail kiri 48 px, konten maks. 1120 px di tengah |
| Panel | Putih, border 1 px, radius 8, baris label kiri dan kontrol kanan, footer Batal/Simpan |
| Tombol | Tinggi 26 atau 32, radius 6, Inter Medium 12; primary biru tua `#004CBC` |
| Warna brand | `#004CBC` → `#1A66C6` → `#3986D6` → `#5BACE4` → `#A9DCF9` → `#DEF1FF` |
| Netral | Latar `#F7F9FB`, panel `#FFFFFF`, border `#E3E8EE`, teks `#11181F`, muted `#6B7684` |
| Gradasi langit | Hanya di panel kiri Masuk/Daftar dan thumbnail video |
| Maskot | Awan bermata dengan gembok, di top bar, halaman masuk, dan empty state |

Acuan per halaman: Brankas → frame Project home (`19:1630`); Profil dan Simpan unboxing → Organization Settings (`19:4120`); daftar kartu → Organizations (`19:8091`).

## Pembagian tugas dan alur kerja

FE dan BE dikerjakan **paralel** di repo yang sama, dipisah oleh kontrak JSON di bagian API. FE memakai mock dengan bentuk persis kontrak, lalu cukup ganti URL saat BE siap.

| Anggota | Peran | Yang dikerjakan |
| --- | --- | --- |
| Yae | Backend | Struktur project, database, auth, semua endpoint, integrasi modul enkripsi |
| Anggota 2 | Modul enkripsi | Encrypt/decrypt AES, RC4, DES versi streaming, penurunan key, unit test |
| Dzaky | Frontend | Halaman Jinja2 + `fetch` ke API, mock JSON sesuai kontrak, state umpan balik |
| Anggota 4 | Dokumentasi dan pengujian | Kajian UU PDP dan GDPR, skenario uji R1–R7, pengukuran performa, laporan, slide demo |

Urutan kerja:

1. **Sepakati kontrak** (15 menit): endpoint, contoh JSON, folder FE (`app/templates/`, `app/static/`).
2. **Kerja paralel**: BE + enkripsi di satu sisi, FE dengan mock di sisi lain, dokumentasi mulai kajian hukum.
3. **Sambung FE ke API** pada jam yang disepakati (usulan 13.00).
4. **Uji R1–R7 bersama**, ukur performa tiga algoritma dengan file 1, 10, dan 50 MB.
5. **Laporan dan latihan demo** mengikuti skenario di bagian Sudut pandang user.

## Yang perlu disepakati

- [ ] Tafsir "encrypted with all of these algorithms": tiga ciphertext terpisah (usulan dokumen ini) atau berlapis AES → RC4 → DES? Tanyakan ke dosen.
- [ ] Boleh pakai library kriptografi, atau algoritma harus diimplementasikan sendiri?
- [ ] Sumber key: master secret di server (usulan) atau turunan password user?
- [ ] Tabel `packages` dan tiga endpoint paket, plus peran toko, tabel klaim, dan tabel file\_keys: Yae setuju menambahkannya? Pakai desain kunci file terbungkus per penerima, atau fallback cek izin saja?
- [ ] Contoh JSON di bagian API sudah final untuk dipakai FE sebagai mock?
- [ ] Jam sambung FE ke API (usulan 13.00)
- [ ] Deadline dan bentuk pengumpulan: source code, laporan, atau demo langsung?
- [ ] Batas video 100 MB cukup?
- [ ] Siapa Anggota 2 dan Anggota 4?
