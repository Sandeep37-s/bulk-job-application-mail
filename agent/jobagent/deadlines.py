"""Source-backed deadlines, earliest-deadline ordering and capacity estimates."""
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from . import db
from .config import CFG

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


CLOSED_RE = re.compile(r'(?i)no longer accepting|not accepting|applications? (?:are |is |have |has )?(?:now )?closed'
                       r'|hiring (?:is )?closed|position (?:has been |is )?filled|vacancy (?:has been |is )?filled'
                       r'|(?:job|posting|role|opening) (?:has )?(?:expired|closed)')
DATE_PATTERNS = [(r'\b\d{4}-\d{2}-\d{2}\b', ['%Y-%m-%d']),
                 (r'\b\d{1,2} [A-Za-z]{3,9},? \d{4}\b', ['%d %B %Y', '%d %b %Y']),
                 (r'\b[A-Za-z]{3,9} \d{1,2},? \d{4}\b', ['%B %d %Y', '%b %d %Y'])]


def quote_dates(quote):
    """Every full date written in the quote, as end of that day in IST."""
    out = []
    for pattern, formats in DATE_PATTERNS:
        for match in re.findall(pattern, quote or ''):
            for fmt in formats:
                try:
                    day = datetime.strptime(match.replace(',', ''), fmt)
                    out.append(day.replace(hour=23, minute=59, second=59, tzinfo=IST))
                    break
                except ValueError:
                    pass
    return out


def expired(lead_id):
    now = datetime.now(timezone.utc)
    deadline = deadline_for(lead_id)
    if deadline is not None:
        return deadline <= now
    # No verified deadline: still never send to a post that says it is closed,
    # or whose every date (e.g. a walk-in day) has already passed.
    quote = metadata(lead_id).get('quote') or ''
    dates = quote_dates(quote)
    return bool(CLOSED_RE.search(quote)) or (bool(dates) and max(dates) <= now)


DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


def _window():
    """(start, end, weekdays) in IST from config, or None to allow any time."""
    s = CFG['sending']
    if not s.get('send_hours'):
        return None
    start, end = (datetime.strptime(x.strip(), '%H:%M').time() for x in s['send_hours'].split('-'))
    days = {DAYS.index(d[:3].lower()) for d in s.get('send_days') or DAYS}
    return start, end, days


def next_window_open(at):
    """`at` itself if inside sending hours, otherwise the next opening (UTC)."""
    w = _window()
    if not w:
        return at
    start, end, days = w
    local = at.astimezone(IST)
    for offset in range(8):
        day = (local + timedelta(days=offset)).date()
        if day.weekday() not in days:
            continue
        opens = datetime.combine(day, start, IST)
        closes = datetime.combine(day, end, IST)
        if local < closes:
            return max(local, opens).astimezone(timezone.utc)
    return at


def in_window(at):
    return next_window_open(at) == at


def projected_slots(leads, limit, gap, now=None):
    """Estimated send time per lead: `gap` apart, inside sending hours, at most `limit` per IST day."""
    now = now or datetime.now(timezone.utc)
    stamp = lambda key: datetime.fromtimestamp(float(db.kv_get(key, 0)), timezone.utc)
    slot = max(now, stamp('last_send_ts') + timedelta(seconds=gap), stamp('next_send_ts'))
    day, count = db.day_start(now), db.used_today(at=now)
    out = []
    for lead in leads:
        while True:
            slot = next_window_open(slot)
            if db.day_start(slot) != day:
                day, count = db.day_start(slot), 0
            if count < limit:
                break
            slot = day + timedelta(days=1)
        out.append((lead, slot))
        count += 1
        slot += timedelta(seconds=gap)
    return out


def refresh_pending_deadlines():
    """Bounded refresh also covers drafts created before deadline support."""
    from .search import with_page_text
    from .llm import extract_companies
    from .screening import save_experience, scam_reason
    now = datetime.now(timezone.utc).timestamp()
    # Only drafts the sender can actually use: refreshing the rest is AI cost for nothing.
    candidates = [l for l in db.leads_with_status('pending') if l.get('hiring_role') and l.get('job_url')
                  and db.kv_get(f'auto_eligible:{l["id"]}') == '1']
    # Never-checked drafts first (they block sending), then the stalest.
    candidates.sort(key=lambda l: (db.kv_get(f'deadline_scanned:{l["id"]}') == '1',
                                   float(db.kv_get(f'deadline_checked:{l["id"]}', 0))))
    for lead in candidates[:5]:
        scanned = db.kv_get(f'deadline_scanned:{lead["id"]}') == '1'
        # Re-reading a page already checked once rarely changes anything: once a day is enough.
        if scanned and now - float(db.kv_get(f'deadline_checked:{lead["id"]}', 0)) < 86400:
            continue
        results = with_page_text([dict(url=lead['job_url'], title='', snippet='')], chars=10000)
        try:
            companies = extract_companies(results) if results[0]['snippet'] else []
        except Exception:
            # Leave it unscanned for a later retry, but rotate so it cannot block the others.
            logging.getLogger(__name__).exception('Deadline refresh failed for lead %s', lead['id'])
            db.kv_set(f'deadline_checked:{lead["id"]}', now)
            continue
        if companies:
            for company in companies:
                if (company.get('company') or '').casefold() == lead['company'].casefold() and (company.get('hiring_role') or '').casefold() == lead['hiring_role'].casefold():
                    save_evidence(lead['id'], company, results)
                    save_experience(lead['id'], company, results)
                    reason = scam_reason(company, results)
                    if reason:
                        db.update_lead(lead['id'], status='rejected_scam', error=reason)
        # Checked once, even if the page was blocked or unchanged: an unknown deadline
        # is allowed, but waiting forever for an unreadable page would stall the queue.
        db.kv_set(f'deadline_scanned:{lead["id"]}', '1')
        db.kv_set(f'deadline_checked:{lead["id"]}', now)
