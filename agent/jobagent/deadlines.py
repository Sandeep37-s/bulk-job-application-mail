"""Source-backed deadlines, earliest-deadline ordering and capacity estimates."""
import json
import re
from datetime import datetime, timedelta, timezone
from . import db

IST = timezone(timedelta(hours=5, minutes=30))


def parse_deadline(quote):
    if not re.search(r'(?i)deadline|last date|apply by|applications? clos|closing date', quote or ''):
        return None
    patterns = [(r'\b\d{4}-\d{2}-\d{2}\b', ['%Y-%m-%d']),
                (r'\b\d{1,2} [A-Za-z]{3,9} \d{4}\b', ['%d %B %Y', '%d %b %Y']),
                (r'\b[A-Za-z]{3,9} \d{1,2},? \d{4}\b', ['%B %d %Y', '%b %d %Y'])]
    # Date-only sources use end-of-day IST. Explicit times are not guessed.
    if re.search(r'\d{1,2}:\d{2}|\b\d{1,2}\s*(?:am|pm)\b|\b(?:UTC|GMT|PST|PDT|EST|EDT|CET)\b', quote, re.I):
        return None
    for pattern, formats in patterns:
        match = re.search(pattern, quote)
        if match:
            for fmt in formats:
                try:
                    day = datetime.strptime(match[0].replace(',', ''), fmt)
                    return day.replace(hour=23, minute=59, second=59, tzinfo=IST).astimezone(timezone.utc)
                except ValueError:
                    pass
    return None


def save_evidence(lead_id, company, results):
    db.kv_set(f'deadline_scanned:{lead_id}', '1')
    quote = (company.get('deadline_text') or '').strip()
    source = company.get('source_url') or company.get('job_url')
    if not quote or len(quote) > 250:
        return
    if not any(r.get('url') == source and quote in (r.get('title', '') + ' ' + r.get('snippet', '')) for r in results):
        return
    deadline = parse_deadline(quote)
    db.kv_set(f'deadline:{lead_id}', json.dumps(dict(at=deadline.isoformat() if deadline else None,
                                                     quote=quote, source=source)))


def metadata(lead_id):
    raw = db.kv_get(f'deadline:{lead_id}', '{}')
    return json.loads(raw) if isinstance(raw, str) else {}


def deadline_for(lead_id):
    value = metadata(lead_id).get('at')
    return datetime.fromisoformat(value) if value else None


def expired(lead_id):
    deadline = deadline_for(lead_id)
    return deadline is not None and deadline <= datetime.now(timezone.utc)


def projected_slots(leads, limit, gap, now=None):
    now = now or datetime.now(timezone.utc)
    with db.conn() as c:
        rows = c.execute('SELECT id, sent_at FROM leads WHERE sent_at IS NOT NULL').fetchall()
        attempts = c.execute('SELECT lead_id, attempted_at FROM send_attempts').fetchall()
    history = {r[0]: datetime.fromisoformat(r[1]) for r in attempts}
    for row in rows:
        history[row[0]] = max(history.get(row[0], datetime.min.replace(tzinfo=timezone.utc)), datetime.fromisoformat(row[1]))
    stamps = sorted(t for t in history.values() if t > now - timedelta(hours=24))
    slot = max(now, datetime.fromtimestamp(float(db.kv_get('last_send_ts', 0)), timezone.utc) + timedelta(seconds=gap))
    out = []
    for lead in leads:
        while True:
            stamps = [t for t in stamps if t > slot - timedelta(hours=24)]
            if len(stamps) < limit:
                break
            slot = stamps[0] + timedelta(hours=24, seconds=1)
        out.append((lead, slot))
        stamps.append(slot)
        slot += timedelta(seconds=gap)
    return out


def refresh_pending_deadlines():
    """Bounded refresh also covers drafts created before deadline support."""
    from .search import with_page_text
    from .llm import extract_companies
    now = datetime.now(timezone.utc).timestamp()
    candidates = [l for l in db.leads_with_status('pending') if l.get('hiring_role') and l.get('job_url')]
    candidates.sort(key=lambda l: float(db.kv_get(f'deadline_checked:{l["id"]}', 0)))
    for lead in candidates[:5]:
        if now - float(db.kv_get(f'deadline_checked:{lead["id"]}', 0)) < 21600:
            continue
        results = with_page_text([dict(url=lead['job_url'], title='', snippet='')], chars=10000)
        if results[0]['snippet']:
            for company in extract_companies(results):
                if (company.get('company') or '').casefold() == lead['company'].casefold() and (company.get('hiring_role') or '').casefold() == lead['hiring_role'].casefold():
                    save_evidence(lead['id'], company, results)
        db.kv_set(f'deadline_checked:{lead["id"]}', now)
