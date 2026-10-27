"""Tampilkan ciphertext yang tersimpan, untuk demo. Hanya membaca; tidak mendekripsi apa pun.

    python scripts/lihat_cipher.py                       # semua file + profil
    python scripts/lihat_cipher.py --file 1 --asli video.mp4   # bandingkan dengan file asli
"""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402


def hexline(data: bytes, n: int = 32) -> str:
    head = data[:n]
    hx = " ".join(f"{b:02x}" for b in head)
    txt = "".join(chr(b) if 32 <= b < 127 else "." for b in head)
    return f"{hx}  |{txt}|"


def db_path() -> Path:
    url = get_settings().database_url
    return (ROOT / url.split("sqlite:///", 1)[1]).resolve()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=int, help="id file tertentu")
    ap.add_argument("--asli", type=Path, help="file asli di komputermu, untuk dibandingkan")
    ap.add_argument("--bytes", type=int, default=32)
    args = ap.parse_args()

    storage = (ROOT / get_settings().storage_dir).resolve()
    con = sqlite3.connect(db_path())

    if args.asli:
        data = args.asli.read_bytes()[: args.bytes]
        print(f"ASLI  {args.asli.name}  ({args.asli.stat().st_size} byte)")
        print(f"      {hexline(data, args.bytes)}\n")

    q = ("select f.id, u.username, f.category, f.size_bytes, fc.algorithm, fc.storage_path, fc.enc_time_ms "
         "from files f join users u on u.id = f.user_id join file_ciphertexts fc on fc.file_id = f.id")
    rows = con.execute(q + (" where f.id = ?" if args.file else "") + " order by f.id, fc.algorithm",
                       (args.file,) if args.file else ()).fetchall()
    last = None
    for fid, user, cat, size, alg, path, ms in rows:
        if fid != last:
            print(f"FILE #{fid}  {cat}  milik {user}  ukuran asli {size} byte")
            last = fid
        p = storage / path
        with open(p, "rb") as fh:
            head = fh.read(args.bytes)
        print(f"  {alg.upper():3}  {p.stat().st_size:>10} byte  enc {ms:8.1f} ms  storage/{path}")
        print(f"       {hexline(head, args.bytes)}")

    if not args.file:
        print("\nPROFIL (tabel profile_ciphertexts)")
        for user, alg, iv, ct in con.execute(
            "select u.username, p.algorithm, p.iv, p.ciphertext from profile_ciphertexts p "
            "join users u on u.id = p.user_id order by u.username, p.algorithm"
        ):
            print(f"  {user:10} {alg.upper():3}  iv={iv.hex()}  {len(ct)} byte")
            print(f"       {hexline(ct, args.bytes)}")


if __name__ == "__main__":
    main()
