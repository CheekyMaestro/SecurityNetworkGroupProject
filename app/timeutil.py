from datetime import datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_wib_iso(dt: datetime | None) -> str | None:
    """Waktu di DB disimpan UTC; SQLite mengembalikan naive, jadi anggap UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB).isoformat(timespec="seconds")
