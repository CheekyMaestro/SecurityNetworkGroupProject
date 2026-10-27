# Hasil pengujian backend

Diuji 14 Oktober 2026 di branch `be`, Windows 11, Python 3.12.

- `pytest -q`: **306 lolos, 1 dilewati** (lihat catatan RC4 1 byte di bawah)
- `python scripts/demo_e2e.py`: **54/54 langkah lolos** dengan video 10, 50, dan 99 MB

## Cara menjalankan ulang

```
pytest -q                                  # semua test otomatis (sekitar 2 menit)
python scripts/demo_e2e.py                 # skenario demo PRD lewat server sungguhan, video 10 MB
python scripts/demo_e2e.py --video-mb 50   # ukuran video lain
```

`demo_e2e.py` memakai database, storage, dan secret sementara, jadi tidak mengganggu `.env` dan data demo.

## Requirement R1–R7

| ID | Requirement | Bukti otomatis |
| --- | --- | --- |
| R1 | Data pribadi di database | `test_profile.py`: `test_get_tiap_algoritma_kembali_asli`, `test_tersimpan_tiga_ciphertext_terpisah`, `test_tidak_ada_plaintext_di_file_database` |
| R2 | Foto KTP | `test_files.py`: `test_ktp_muncul_di_profil`, `test_melebihi_batas_413_tanpa_file_parsial[id_card…]`; demo langkah "R2" |
| R3 | PDF/DOC/XLS | `test_files.py`: `test_upload_tiga_ciphertext_tiga_file_tiga_kunci`, `test_mkv_dan_doc_lama_diterima`, `test_daftar_file_dengan_filter_kategori` |
| R4 | Video | `test_files.py`: `test_unduh_tiap_algoritma_identik`; demo dengan video 99 MB |
| R5 | AES, RC4, DES | `test_crypto.py` (127 test, 1 dilewati), `test_tersimpan_tiga_ciphertext_terpisah` (tiga ciphertext terpisah, bukan berlapis) |
| R6 | Ambil data terdekripsi | `test_unduh_tiap_algoritma_identik` (3 algoritma × 4 ukuran, byte per byte), `test_get_tiap_algoritma_kembali_asli` |
| R7 | Username dan password | `test_auth.py` (53 test): register, login, sesi, 401, 403 |

## Test wajib dari CLAUDE.md

| Test wajib | Nama test |
| --- | --- |
| Round-trip 0, 1, 15, 16, 17 byte, 64 KB, 64 KB+1, 1 MB per algoritma | `test_crypto.py::test_roundtrip_bytes`, `test_roundtrip_streaming` |
| Ciphertext ≠ plaintext; dua enkripsi data sama → hasil beda | `test_ciphertext_beda_dari_plaintext`, `test_dua_enkripsi_data_sama_hasil_beda` |
| Upload → 3 baris `file_ciphertexts`, 3 file di disk, 3 baris `file_keys` pemilik | `test_files.py::test_upload_tiga_ciphertext_tiga_file_tiga_kunci` |
| Unduh `aes`/`rc4`/`des` sama dengan asli | `test_files.py::test_unduh_tiap_algoritma_identik` |
| User lain akses file, paket, klaim → 404 | `test_user_lain_tidak_bisa_akses_file`, `test_paket_user_lain_404`, `test_toko_lain_dan_pembeli_lain_404` |
| Toko tanpa klaim → 404; setelah klaim ke Elektra: Elektra 200, Gadgetin 404 | `test_claims.py::test_akses_file_sebelum_dan_sesudah_klaim` |
| Klaim tidak membuat `file_keys` untuk `id_card` | `test_claims.py::test_klaim_tidak_pernah_membagikan_id_card` |
| File lewat batas → 413, tidak ada file parsial | `test_files.py::test_melebihi_batas_413_tanpa_file_parsial` |
| Tanpa cookie → 401; login salah → 401 pesan generik | `test_auth.py::test_endpoint_tanpa_cookie_401` (18 endpoint), `test_login_salah_401_pesan_generik` |
| Tidak ada plaintext di `storage/` maupun database | `test_files.py::test_tidak_ada_plaintext_di_storage_maupun_database`; demo memeriksa 8 penanda (isi file, nama file, NIK, rekening, nama barang, pesan klaim) |

## Performa (laptop pengembang, video 99 MB, satu kali ukur)

> **Note:** the numbers below are an early single measurement. The final numbers used in the report come from `scripts/benchmark.py` (two runs, five repetitions per size); raw output is in `results/`.

| Algoritma | Enkripsi (ms/MB) | Dekripsi (ms/MB) | Ukuran ciphertext |
| --- | --- | --- | --- |
| AES-256-CBC | 2,7 | 2,5 | asli + 1..16 byte padding |
| RC4 | 3,7 | 4,5 | sama dengan asli |
| DES-CBC | 17,1 | 20,1 | asli + 1..8 byte padding |

- AES lebih cepat dari RC4 kemungkinan karena instruksi AES-NI di CPU; RC4 tidak dibantu hardware.
- DES 6–8× lebih lambat dari AES.
- Upload video 99 MB (tiga enkripsi sekaligus): 3,4 detik. Unduh: AES 1,3 s, RC4 1,7 s, DES 3,5 s.
- Angka bergeser antar run; untuk laporan ukur beberapa kali dengan file 1, 10, 50 MB lalu ambil rata-rata.

## Keterbatasan (untuk ditulis jujur di laporan)

1. **RC4 dan DES tidak aman** untuk sistem nyata; dipakai karena syarat tugas. RC4 dipakai tanpa "drop" byte awal keystream.
2. **Server memegang `MASTER_SECRET`**, jadi secara teori server bisa menurunkan semua kunci user. Akses toko dibuktikan dengan kunci terbungkus (`file_keys`, `claim_keys`), tapi bukan enkripsi end-to-end.
3. **Belum ada pemeriksaan integritas** (HMAC) pada ciphertext file. Perubahan ciphertext di disk tidak terdeteksi, kecuali pada kunci terbungkus (AES-GCM) yang menolak perubahan.
4. **Video tidak bisa di-seek** (belum mendukung HTTP Range); bisa diputar dari awal.
5. **Tidak ada pembatasan percobaan login** (rate limit).
6. **Logout menghapus cookie**, tapi token JWT yang sudah dicuri tetap berlaku sampai kedaluwarsa (60 menit).
7. **Klaim yang ditolak tidak mencabut akses toko** ke file yang sudah dibagikan.
8. **Belum ada migrasi database**: perubahan skema butuh hapus `awan.db` dan `storage/`.
9. Satu test dilewati dengan sengaja: ciphertext RC4 untuk data 1 byte punya peluang 1/256 sama dengan plaintext-nya. Ini sifat stream cipher, bukan bug.
