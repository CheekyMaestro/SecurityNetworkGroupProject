# Catatan Frontend

Ringkasan untuk tim: cara menjalankan FE tanpa backend, daftar halaman, dan apa yang perlu dicek bersama saat FE disambung ke API.

## Menjalankan

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Buka http://localhost:8000/masuk?mock=1.

## Mode mock

| Aksi | Caranya |
| --- | --- |
| Nyalakan | Tambahkan `?mock=1` ke URL mana saja. Pilihan disimpan di `localStorage.awanMock`, jadi tetap aktif saat pindah halaman. |
| Matikan | Klik **Matikan mock** di banner kuning, buka URL dengan `?mock=0`, atau jalankan `api.disableMock()` di console. |
| Pindah peran | `?role=store` (akun Toko Elektra) atau `?role=buyer` (dzaky). Bisa juga lewat tombol di banner. |
| Reset data contoh | `?mock=0` lalu `?mock=1` lagi, atau `api.resetMock()` di console. |

Selama mock menyala, banner "Mode mock aktif" tampil di atas setiap halaman.

Perilaku mock:
- Data awal dibaca dari `app/static/mock/*.json` (bentuknya persis kontrak di PRD), dengan jeda 300 ms per panggilan.
- Perubahan (paket baru, upload, hapus file, klaim, keputusan toko, balasan, profil) disimpan di `sessionStorage`, jadi hilang kalau tab ditutup.
- Upload menyimulasikan progress. File yang baru diupload bisa dipratinjau di halaman yang sama; setelah pindah halaman, media diganti `sample.mp4` / `ktp-contoh.png` / dokumen contoh.
- Masuk: username yang mengandung `elektra` atau `toko` masuk sebagai toko, selain itu sebagai pembeli. Password `salah` memunculkan error login.
- Daftar: username `dzaky` sudah dipakai; password kurang dari 8 karakter ditolak.

Semua panggilan lewat `app/static/js/api.js`. Saat backend siap, cukup matikan mock; kode halaman tidak perlu diubah.

## Halaman

| Route | Halaman | Peran | Endpoint yang dipanggil |
| --- | --- | --- | --- |
| `/masuk` | Masuk | publik | `POST /auth/login` |
| `/daftar` | Daftar | publik | `POST /auth/register`, lalu `POST /auth/login` |
| `/brankas` | Brankas saya | pembeli | `GET /packages`, `GET /claims` |
| `/unboxing/baru` | Simpan unboxing | pembeli | `POST /packages`, `POST /files` (video, lalu tiap dokumen) |
| `/paket/{id}` | Detail paket | pembeli | `GET /packages/{id}`, `GET /claims/{id}`, `POST /claims/{id}/replies`, `DELETE /files/{id}`, `/files/{id}/download?alg=` |
| `/paket/{id}/klaim` | Ajukan klaim | pembeli | `GET /packages/{id}`, `GET /stores`, `POST /claims` |
| `/profil` | Profil & KTP | pembeli | `GET /profile?alg=`, `PUT /profile`, `POST /files` (`id_card`) |
| `/statistik` | Statistik enkripsi | pembeli | `GET /stats` |
| `/toko` | Klaim masuk | toko | `GET /claims` |
| `/toko/klaim/{id}` | Tinjau klaim | toko | `GET /claims/{id}`, `PATCH /claims/{id}`, `POST /claims/{id}/replies` |

Semua halaman pembeli dan toko memanggil `GET /auth/me` lebih dulu. Kalau belum masuk, halaman pindah ke `/masuk?next=…`. Kalau perannya salah, halaman pindah ke beranda peran itu (`/brankas` atau `/toko`).

## Struktur FE

```
app/main.py                 kerangka: static, templates, router pages, handler 404 HTML
app/routes/pages.py         route GET yang hanya me-render template
app/templates/base.html     font, app.css, Lucide, api.js, app.js
app/templates/layouts/      buyer (top bar + rail), store (top bar + tab), focus (tanpa rail), auth
app/templates/components/   macro Jinja: button, input, select, textarea, badge, panel, form_row, stat_tile,
                            nav_rail, top_bar, empty_state, toast, dialog, file_row, skeleton
app/templates/pages/        satu template per halaman + not_found.html
app/static/css/app.css      token warna/font dan semua gaya komponen
app/static/js/api.js        semua panggilan API + mode mock
app/static/js/app.js        toast, dialog konfirmasi, guard login, menu akun, banner mock, format angka/tanggal
app/static/js/pages/*.js    logika per halaman
app/static/mock/            JSON kontrak, sample.mp4, ktp-contoh.png (placeholder, bukan KTP asli), dokumen contoh
```

## Dicek bersama Yae saat sambung

1. `GET /auth/me` sudah ada dan mengembalikan 401 kalau belum masuk.
2. Matikan mock, lalu jalankan alurnya: daftar → profil → simpan unboxing (video + 2 dokumen) → detail paket → ajukan klaim → masuk sebagai toko → tinjau → terima.
3. Video bisa di-seek di `<video>`. Butuh dukungan `Range` / `206 Partial Content` di endpoint download.
4. Tombol Unduh menghasilkan nama file asli (`Content-Disposition`).
5. Mode demo di Detail paket dan Profil: ganti AES/RC4/DES, lalu pastikan file dan `decrypt_ms` berubah sesuai algoritma.
6. Pesan error dari BE (`detail`) terbaca wajar di UI. FE menampilkannya apa adanya.
7. Upload lebih dari batas (video > 100 MB, dokumen > 20 MB, KTP > 5 MB) ditolak BE dengan 413 dan `detail`.
8. Akun toko tidak bisa membuka file paket yang tidak diklaim (404).

Daftar kebutuhan FE yang lebih rinci ada di [`FE-NEEDS.md`](FE-NEEDS.md).

## Catatan desain

- Struktur mengikuti dashboard Supabase di Figma (Project home untuk Brankas, Organization Settings untuk form, Organizations untuk kartu klaim), dengan tema terang dan token warna langit dari `app.css`.
- Warna grafik mengikuti brief: AES `--brand-600`, RC4 `--brand-400`, DES `--brand-200`. `--brand-200` kontrasnya rendah terhadap latar putih (1,8:1), jadi batang diberi border tipis, nilai ditulis langsung di atas batang, dan ada tabel angka di bawah grafik.
- Tampilan mobile dan dark mode di luar scope.
