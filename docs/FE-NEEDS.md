# Kebutuhan FE dari BE

Hal yang dibutuhkan halaman FE tapi belum tertulis jelas di kontrak PRD. Usulan di bawah sudah dipakai mock; kalau BE memilih bentuk lain, kabari supaya mock dan kontrak di PRD ikut diubah.

## Respons yang belum ada di kontrak

| Endpoint | Yang dipakai FE | Usulan |
| --- | --- | --- |
| `POST /packages` | Hanya `id` (untuk upload file lalu pindah ke `/paket/{id}`) | 201, bentuk sama dengan `GET /packages/{id}` (`files: []`, `claim: null`) |
| `POST /auth/register` | Tidak dipakai; FE langsung memanggil `POST /auth/login` setelahnya | 201 dengan bentuk `/auth/me`. Boleh juga langsung memasang cookie. |
| `POST /claims/{id}/replies` | Tidak dipakai; FE memuat ulang `GET /claims/{id}` | 201 dengan objek balasan `{id, author_role, author_name, body, created_at}` |
| `DELETE /files/{id}` | Hanya status 2xx | 204 tanpa body |
| `PUT /profile` | `updated_at` | Bentuk sama dengan `GET /profile` |
| `POST /auth/logout` | Hanya status 2xx | 200 atau 204 |

## Perilaku yang diharapkan

- **`GET /profile` untuk user baru**: 200 dengan semua field `data` bernilai `null`, `id_card_file_id: null`, dan `updated_at: null`, bukan 404. Halaman Profil langsung dibuka setelah daftar.
- **Status 401 hanya untuk "belum masuk / sesi habis"**: FE selalu mengarahkan 401 ke `/masuk`, kecuali di `/auth/login` dan `/auth/register`. Login gagal boleh 401 atau 400; FE selalu menampilkan "Username atau password salah." Peran yang salah (mis. pembeli memanggil `PATCH /claims/{id}`) sebaiknya 403 atau 404, bukan 401.
- **Format error**: `{"detail": "pesan untuk user"}` dalam bahasa Indonesia. FE menampilkan `detail` apa adanya. Error validasi FastAPI (422, `detail` berupa array) juga terbaca, tapi pesannya kurang ramah.
- **Download** (`/files/{id}/download?alg=`):
  - dipakai langsung sebagai `<video src>`, `<img src>`, dan link unduh, jadi auth harus lewat cookie, bukan header;
  - `Content-Type` sesuai `mime_type` asli;
  - `Content-Disposition: attachment; filename="<nama asli>"` untuk dokumen, `inline` untuk video dan gambar;
  - dukung header `Range` supaya video bisa di-seek.
- **`PATCH /claims/{id}`**: field `reply` bisa berupa string kosong saat toko memilih "Terima" tanpa pesan. BE sebaiknya tidak membuat balasan kosong.
- **`POST /files` dengan `category=id_card`**: FE menganggap foto baru menggantikan yang lama dan memperbarui `id_card_file_id` di profil. Tanpa `package_id`.
- **Batas ukuran dan jenis**: FE sudah memvalidasi di klien (video ≤ 100 MB MP4/MKV/MOV, dokumen ≤ 20 MB PDF/DOC/DOCX/XLS/XLSX, KTP ≤ 5 MB JPG/PNG). BE tetap perlu menolak dengan 413/400 dan `detail`.
- **`GET /claims` untuk pembeli** dipakai Brankas untuk badge status per paket (lewat `package_id`).
- **`GET /claims/{id}`** perlu `files[].category` supaya FE bisa memilih video untuk pemutar.
- **`GET /stats`**: FE menggambar kombinasi kategori × algoritma apa pun yang ada di `per_category`. Kalau BE hanya mengisi sebagian, grafiknya tetap jalan.

## Di `app/main.py` (kerangka dari FE)

- Ada exception handler: request `GET` 404 dengan header `Accept: text/html` (browser membuka URL) di-render sebagai halaman "Data tidak ditemukan". Panggilan `fetch` dari FE memakai `Accept: application/json`, jadi tetap menerima `{"detail": ...}`. Kalau handler ini mengganggu, silakan disesuaikan.
- Tempat include router API sudah ditandai `# BE: include router API di sini (auth, profile, packages, files, claims, stats)`.
- Router halaman memakai path `/masuk`, `/daftar`, `/brankas`, `/unboxing/baru`, `/paket/{id}`, `/paket/{id}/klaim`, `/profil`, `/statistik`, `/toko`, `/toko/klaim/{id}`, `/tidak-ditemukan`. Jangan sampai bentrok dengan path API.
