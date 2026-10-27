"""Benchmark AES vs RC4 vs DES memakai kelas enkripsi yang sama dengan aplikasi.

Yang diukur: waktu enkripsi dan dekripsi per MB, untuk data acak 1, 10, dan 50 MB.
Cara ukur (supaya hasilnya bisa dipercaya):
  - data diproses per potongan 64 KB, persis seperti saat upload di aplikasi
  - 1 kali pemanasan (warm-up) yang hasilnya dibuang
  - 5 kali ulang, lalu diambil rata-rata dan standar deviasi
  - setiap ulangan dicek: hasil dekripsi harus sama persis dengan data asli
Disk, database, dan jaringan sengaja tidak ikut diukur, supaya yang terlihat hanya biaya cipher.

Cara pakai (dari folder utama repo):
    python scripts/benchmark.py                 # default: 1, 10, 50 MB, 5 ulangan
    python scripts/benchmark.py --sizes 1 10 --repeat 3
Hasil disimpan ke results/benchmark-<waktu>.json dan .csv, ringkasannya dicetak di layar.
"""

import argparse
import csv
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import Crypto  # noqa: E402

from app.crypto.keys import ALGORITHMS, new_file_keys  # noqa: E402
from app.crypto.vault import StreamDecryptor, StreamEncryptor  # noqa: E402

CHUNK = 64 * 1024
MB = 1024 * 1024


def chunks(data: bytes):
    for i in range(0, len(data), CHUNK):
        yield data[i : i + CHUNK]


def encrypt(alg, key, data):
    enc = StreamEncryptor(alg, key)
    parts = [enc.update(c) for c in chunks(data)]
    parts.append(enc.finalize())
    return enc.iv, b"".join(parts)


def decrypt(alg, key, iv, ct):
    dec = StreamDecryptor(alg, key, iv)
    parts = [dec.update(c) for c in chunks(ct)]
    parts.append(dec.finalize())
    return b"".join(parts)


def one_run(alg, key, data):
    t0 = time.perf_counter()
    iv, ct = encrypt(alg, key, data)
    t1 = time.perf_counter()
    pt = decrypt(alg, key, iv, ct)
    t2 = time.perf_counter()
    if pt != data:
        raise SystemExit(f"GAGAL: hasil dekripsi {alg} tidak sama dengan data asli")
    return (t1 - t0) * 1000, (t2 - t1) * 1000, len(ct) - len(data)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sizes", type=int, nargs="+", default=[1, 10, 50], help="ukuran data dalam MB")
    p.add_argument("--repeat", type=int, default=5)
    args = p.parse_args()

    keys = new_file_keys()
    rows = []
    for size in args.sizes:
        data = os.urandom(size * MB)
        for alg in ALGORITHMS:
            one_run(alg, keys[alg], data)  # warm-up, dibuang
            enc_ms, dec_ms = [], []
            overhead = 0
            for _ in range(args.repeat):
                e, d, overhead = one_run(alg, keys[alg], data)
                enc_ms.append(e / size)
                dec_ms.append(d / size)
            row = {
                "size_mb": size,
                "cipher": alg,
                "enc_ms_per_mb": round(statistics.mean(enc_ms), 3),
                "enc_sd": round(statistics.stdev(enc_ms), 3) if len(enc_ms) > 1 else 0.0,
                "dec_ms_per_mb": round(statistics.mean(dec_ms), 3),
                "dec_sd": round(statistics.stdev(dec_ms), 3) if len(dec_ms) > 1 else 0.0,
                "enc_mb_per_s": round(1000 / statistics.mean(enc_ms), 1),
                "overhead_bytes": overhead,
            }
            rows.append(row)
            print(
                f"{size:>3} MB  {alg:<3}  enc {row['enc_ms_per_mb']:7.2f} ± {row['enc_sd']:.2f} ms/MB"
                f"  dec {row['dec_ms_per_mb']:7.2f} ± {row['dec_sd']:.2f} ms/MB"
                f"  ({row['enc_mb_per_s']} MB/s, +{overhead} byte)"
            )

    print("\nRata-rata semua ukuran (ms/MB, makin kecil makin cepat):")
    aes_enc = statistics.mean(r["enc_ms_per_mb"] for r in rows if r["cipher"] == "aes")
    for alg in ALGORITHMS:
        mine = [r for r in rows if r["cipher"] == alg]
        enc = statistics.mean(r["enc_ms_per_mb"] for r in mine)
        dec = statistics.mean(r["dec_ms_per_mb"] for r in mine)
        print(f"  {alg:<3}  enc {enc:6.2f}  dec {dec:6.2f}  ({enc / aes_enc:.2f}x AES)")

    env = {
        "waktu": datetime.now().isoformat(timespec="seconds"),
        "cpu": platform.processor() or platform.machine(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "pycryptodome": Crypto.__version__,
        "repeat": args.repeat,
        "chunk_bytes": CHUNK,
    }
    out = Path("results")
    out.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (out / f"benchmark-{stamp}.json").write_text(json.dumps({"env": env, "rows": rows}, indent=2))
    with open(out / f"benchmark-{stamp}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"\nTersimpan: results/benchmark-{stamp}.json dan .csv")
    print(f"Mesin: {env['cpu']} | {env['os']} | Python {env['python']} | PyCryptodome {env['pycryptodome']}")


if __name__ == "__main__":
    main()