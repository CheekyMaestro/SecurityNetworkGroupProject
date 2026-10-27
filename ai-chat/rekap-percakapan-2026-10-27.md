# Rekap percakapan Claude Code: demo, pemeriksaan, dan laporan Awan

Sesi: 26 sampai 27 Oktober 2026, Claude Code di VS Code (model Opus 5.5 dan Sonnet 5.5).
Rekap ini adalah ringkasan. Transkrip lengkap ada di `chat-ki-2026-10-27.md` di folder yang sama.

## 1. Tujuan sesi

Menyiapkan demo dan pengumpulan Assignment 1 (Symmetric Encryption, kelompok 11): memahami alur aplikasi, melihat data terenkripsi, memeriksa kesesuaian dengan ketentuan tugas, dan merapikan laporan serta repo.

## 2. Yang dibahas dan hasilnya

| Topik | Hasil |
| --- | --- |
| Kesesuaian dengan assignment | Semua syarat teknis terpenuhi: skenario spesifik, data pribadi, KTP, dokumen, video, AES/RC4/DES, mode non-ECB, login username dan password, data kembali utuh. Test backend: 306 lolos, 1 dilewati dengan sengaja |
| Alur utama user | Daftar atau masuk, isi profil dan upload foto KTP, simpan unboxing (video dan dokumen), buka detail paket, ajukan klaim ke toko, lihat statistik |
| Kapan enkripsi terjadi | Saat upload, sekali saja. File asli tidak disimpan; yang tersimpan tiga file `.bin` (AES, RC4, DES). Klaim ke toko hanya membungkus ulang kunci, tidak mengenkripsi ulang file |
| Cara melihat ciphertext | Bukan lewat log backend (log sengaja tanpa isi data). Lewat folder `storage/`, tabel di `awan.db`, dan skrip `cipher_viewer/lihat_cipher.py` yang menampilkan isi dalam hex |
| Data demo | Pakai data dummy. Dibuatkan prompt untuk GPT membuat kartu identitas fiktif (NIK `9900011205040001`, nama fiktif, watermark SPECIMEN) yang selaras dengan form Profil |
| Asal angka di halaman `/statistik` | Diukur dari upload dan unduhan sungguhan, dihitung di `app/services/stats.py` (total ms dibagi total MB). Sudah dicocokkan dengan output skrip |
| Angka dashboard vs laporan | Berbeda karena metodenya berbeda: dashboard dari file kecil di satu laptop, laporan dari benchmark terkontrol. Kesimpulan sama: DES paling lambat, AES dan RC4 jauh lebih cepat |

## 3. Pemeriksaan laporan

- Laporan awal (`AES_RC4_DES_Performance_Report`) dinilai bagus. Disarankan menambah pernyataan penggunaan AI dan meng-commit skrip benchmark.
- Diagram alur kerja (PRD ke brief FE dan BE, sampai web app dan laporan) ditambahkan sebagai bagian "5. How we built it". Layout dipadatkan supaya tetap 2 halaman A4 (dicek dengan Microsoft Word).
- Laporan terbaru `Awan_Report_Group11.docx`: 2 halaman, hitungan di bagian analisis benar, Tabel 1 cocok dengan CSV di `results/` (selisih pembulatan: DES enkripsi run 2 tertulis 12,64, hitungan 12,65). Metode di laporan cocok dengan `scripts/benchmark.py`.
- Catatan yang perlu dikonfirmasi tim: tipe CPU "i9-13900H" tidak tercatat di file hasil benchmark; gambar Figure 1 di laporan berbeda gaya (font) dari keluaran `fig.py`, tetapi datanya sama.

## 4. Perubahan pada repo

| Perubahan | Keterangan |
| --- | --- |
| `cipher_viewer/lihat_cipher.py` | Skrip baca-saja untuk menampilkan ciphertext (hex). Sudah di-push ke `main` (commit `71b1e0c`) |
| `README.md` | Ditambah tautan video demo lengkap di Google Drive. Perubahan lokal, perlu di-commit |
| `ai-chat/` | Ditambah transkrip lengkap dan rekap ini. Perlu di-commit |
| `main` lokal | Di-reset ke `origin/main` supaya sama dengan GitHub. Cadangan versi sebelumnya ada di branch lokal `backup-main-sebelum-reset` |
| `scripts/benchmark.py` dan `results/` | Ditemukan di branch `dzaky/testing`, lalu digabung ke `main` lewat PR #3 oleh Dzaky |

Semua perintah git dijalankan sendiri oleh pengguna; Claude hanya membuatkan perintahnya dan memverifikasi hasilnya.

## 5. Hal yang tidak dibantu

Permintaan untuk menyembunyikan nama Claude dari daftar contributor dan history commit ditolak. Alasannya: ketentuan assignment mewajibkan keterbukaan penggunaan AI (link dan screenshot percakapan) dan history commit dipakai untuk penilaian. Penulisan ulang history juga berisiko merusak pekerjaan anggota lain. Penggunaan AI dicantumkan di bagian "5. How we built it" pada laporan.

## 6. Yang masih perlu dilakukan sebelum deadline (Rabu, 28 Oktober 2026, 00:00)

- [ ] Commit dan push `README.md` dan folder `ai-chat/` ke GitHub
- [ ] Pastikan link Google Drive demo bisa dibuka tanpa login (uji di jendela Incognito)
- [ ] Konfirmasi tipe CPU benchmark, dan (opsional) ganti Figure 1 di laporan dengan `results/figure1-benchmark.png`
- [ ] Lampirkan link dan screenshot percakapan AI di submission, termasuk percakapan lain milik anggota kelompok
- [ ] Ekspor laporan final ke PDF dan cek tetap 2 halaman A4

## 7. Keterbatasan sistem yang diakui di laporan dan dokumentasi

RC4 dan DES tidak aman untuk sistem nyata (dipakai karena syarat tugas); server memegang `MASTER_SECRET` sehingga bukan enkripsi end-to-end; belum ada MAC pada ciphertext file; tidak ada pembatasan percobaan login; video belum bisa di-seek.
