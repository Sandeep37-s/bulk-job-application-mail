"""SQLite store. One row per company (keyed by domain) so nobody is emailed twice."""
import sqlite3
from datetime import datetime, timezone

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY, ts TEXT);
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE,
    company TEXT, website TEXT, city TEXT, what_they_do TEXT,
    hiring_role TEXT, job_url TEXT, why TEXT, est_employees INTEGER,
    email TEXT, all_emails TEXT, email_source TEXT,
    subject TEXT, body TEXT,
    -- new | no_contact | pending | sent | skipped | blocked | failed
    status TEXT DEFAULT 'new',
    error TEXT,
    created TEXT, updated TEXT, sent_at TEXT
);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    if "email_source" not in {r[1] for r in c.execute("PRAGMA table_info(leads)")}:
        c.execute("ALTER TABLE leads ADD COLUMN email_source TEXT")
    return c


def url_seen(url):
    with conn() as c:
        return c.execute("SELECT 1 FROM seen_urls WHERE url=?", (url,)).fetchone() is not None


def mark_urls(urls):
    with conn() as c:
        c.executemany("INSERT OR IGNORE INTO seen_urls VALUES (?, ?)", [(u, now()) for u in urls])


def domain_known(domain):
    with conn() as c:
        return c.execute("SELECT 1 FROM leads WHERE domain=?", (domain,)).fetchone() is not None


def add_lead(**f):
    f.setdefault("status", "new")
    f["created"] = f["updated"] = now()
    cols = ",".join(f)
    with conn() as c:
        cur = c.execute(f"INSERT OR IGNORE INTO leads ({cols}) VALUES ({','.join('?' * len(f))})", list(f.values()))
        return cur.lastrowid if cur.rowcount else None


def update_lead(lead_id, **f):
    f["updated"] = now()
    with conn() as c:
        c.execute(f"UPDATE leads SET {','.join(k + '=?' for k in f)} WHERE id=?", [*f.values(), lead_id])


def get_lead(lead_id):
    with conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        return dict(row) if row else None


def leads_with_status(status):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM leads WHERE status=? ORDER BY id", (status,))]


def sent_today():
    today = datetime.now(timezone.utc).date().isoformat()
    with conn() as c:
        return c.execute("SELECT COUNT(*) FROM leads WHERE status='sent' AND sent_at >= ?", (today,)).fetchone()[0]


def stats():
    with conn() as c:
        return dict(c.execute("SELECT status, COUNT(*) FROM leads GROUP BY status").fetchall())


def kv_get(k, default=None):
    with conn() as c:
        row = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return row[0] if row else default


def kv_set(k, v):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (k, str(v)))
