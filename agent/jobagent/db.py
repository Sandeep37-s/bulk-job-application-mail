"""SQLite store. One row per company (keyed by domain) so nobody is emailed twice."""
import sqlite3
from datetime import datetime, timedelta, timezone

from .config import CFG

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
CREATE TABLE IF NOT EXISTS send_attempts (lead_id INTEGER PRIMARY KEY, attempted_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS extraction_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_usage (
    day TEXT PRIMARY KEY, calls INTEGER DEFAULT 0, input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0, cache_hits INTEGER DEFAULT 0
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    if "email_source" not in {r[1] for r in c.execute("PRAGMA table_info(leads)")}:
        c.execute("ALTER TABLE leads ADD COLUMN email_source TEXT")
    return c


def url_seen(url):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=CFG["search"].get("revisit_days", 3))).isoformat(timespec="seconds")
    with conn() as c:
        return c.execute("SELECT 1 FROM seen_urls WHERE url=? AND ts >= ?", (url, cutoff)).fetchone() is not None


def mark_urls(urls):
    with conn() as c:
        c.executemany("INSERT OR REPLACE INTO seen_urls VALUES (?, ?)", [(u, now()) for u in urls])


def domain_known(domain):
    with conn() as c:
        row = c.execute("SELECT * FROM leads WHERE domain=?", (domain,)).fetchone()
    if row is None:
        return False
    retryable = not row['sent_at'] and (row['status'] in ('no_contact', 'new') or
                (row['status'] == 'failed' and (row['error'] or '').startswith('compose:')))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=CFG["search"].get("retry_days", 3))).isoformat(timespec="seconds")
    return not retryable or (row['updated'] or row['created'] or '') >= cutoff


def add_lead(**f):
    f.setdefault("status", "new")
    f["created"] = f["updated"] = now()
    cols = ",".join(f)
    with conn() as c:
        cur = c.execute(f"INSERT OR IGNORE INTO leads ({cols}) VALUES ({','.join('?' * len(f))})", list(f.values()))
        if cur.rowcount:
            return cur.lastrowid
        # Recover discovery/drafting failures only; never reset sent, skipped,
        # pending, blocked, or send-failed records.
        f.pop('created')
        f.setdefault('status', 'new')
        f['error'] = None
        cur = c.execute(f"UPDATE leads SET {','.join(k + '=?' for k in f)} "
                        "WHERE domain=? AND sent_at IS NULL AND "
                        "(status IN ('no_contact', 'new') OR (status='failed' AND error LIKE 'compose:%'))",
                        [*f.values(), f['domain']])
        if cur.rowcount:
            return c.execute('SELECT id FROM leads WHERE domain=?', (f['domain'],)).fetchone()[0]
        return None


def retry_candidates(limit=5):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=CFG['search'].get('retry_days', 3))).isoformat(timespec='seconds')
    with conn() as c:
        return [dict(row) for row in c.execute(
            "SELECT * FROM leads WHERE sent_at IS NULL AND updated < ? AND "
            "(status IN ('no_contact', 'new') OR (status='failed' AND error LIKE 'compose:%')) "
            "ORDER BY updated LIMIT ?", (cutoff, limit))]


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


IST = timezone(timedelta(hours=5, minutes=30))


def day_start(at=None):
    """Start of the IST calendar day containing `at`, in UTC. The daily cap resets here."""
    at = at or datetime.now(timezone.utc)
    return at.astimezone(IST).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def used_today(c=None, at=None):
    """Send attempts (including uncertain deliveries) since IST midnight."""
    cutoff = day_start(at).isoformat(timespec='seconds')
    sql = 'SELECT COUNT(*) FROM leads WHERE sent_at>=? OR id IN (SELECT lead_id FROM send_attempts WHERE attempted_at>=?)'
    if c is not None:
        return c.execute(sql, (cutoff, cutoff)).fetchone()[0]
    with conn() as c:
        return c.execute(sql, (cutoff, cutoff)).fetchone()[0]


def sent_today():
    with conn() as c:
        return c.execute("SELECT COUNT(*) FROM leads WHERE status='sent' AND sent_at >= ?",
                         (day_start().isoformat(timespec='seconds'),)).fetchone()[0]


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


def extraction_cache_get(key):
    with conn() as c:
        row = c.execute('SELECT value FROM extraction_cache WHERE key=? AND expires>?', (key, now())).fetchone()
    return row[0] if row else None


def extraction_cache_put(key, value, days=7):
    expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec='seconds')
    with conn() as c:
        c.execute('DELETE FROM extraction_cache WHERE expires<=?', (now(),))
        c.execute('INSERT OR REPLACE INTO extraction_cache VALUES (?, ?, ?)', (key, value, expires))


def record_ai_usage(calls=0, input_tokens=0, output_tokens=0, cache_hits=0):
    day = datetime.now(timezone.utc).date().isoformat()
    with conn() as c:
        c.execute('INSERT INTO ai_usage VALUES (?, ?, ?, ?, ?) ON CONFLICT(day) DO UPDATE SET '
                  'calls=calls+excluded.calls, input_tokens=input_tokens+excluded.input_tokens, '
                  'output_tokens=output_tokens+excluded.output_tokens, cache_hits=cache_hits+excluded.cache_hits',
                  (day, calls, input_tokens, output_tokens, cache_hits))


def ai_usage_today():
    with conn() as c:
        row = c.execute('SELECT * FROM ai_usage WHERE day=?',
                        (datetime.now(timezone.utc).date().isoformat(),)).fetchone()
    return dict(row) if row else dict(calls=0, input_tokens=0, output_tokens=0, cache_hits=0)
