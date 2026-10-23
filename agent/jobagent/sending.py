"""Conservative automatic sending with persistent quota and delivery state."""
import re
import time
from datetime import datetime, timedelta, timezone

from . import db
from .config import CFG
from .mailer import send_email


def relevant_role(role):
    text = (role or '').lower()
    if re.search(r'\b(hr|recruiter|recruitment|sales|marketing|office|admin|accountant|assistant|support|business development)\b', text):
        return False
    return bool(re.search(r'\b(ai|ml|genai|llm|nlp|mlops|artificial intelligence|machine learning|deep learning|computer vision|data scien\w*|generative ai)\b', text)
                and re.search(r'\b(engineer|developer|scientist|researcher|research|intern|specialist|architect)\b', text))


def evidence_matches(company, results):
    role = company.get('hiring_role')
    if not relevant_role(role):
        return False
    normalize = lambda s: ' '.join(re.findall(r'\w+', s.lower()))
    source = company.get('source_url') or company.get('job_url')
    return any(r.get('url') == source and normalize(role) in normalize(r.get('title', '') + ' ' + r.get('snippet', '')) for r in results)


def send_one(lead_id):
    """Reserve before SMTP; uncertain/failed deliveries are never auto-retried."""
    settings = CFG['sending']
    lead = db.get_lead(lead_id)
    if not lead or lead['status'] != 'pending':
        return 'Not pending.'
    if not relevant_role(lead.get('hiring_role')) or db.kv_get(f'auto_eligible:{lead_id}') != '1':
        return 'Not eligible: requires a verified advertised AI/ML role.'
    if not lead.get('email_source') or not lead.get('subject') or not lead.get('body'):
        return 'Missing verified contact or draft.'
    now = datetime.now(timezone.utc)
    ist = timezone(timedelta(hours=5, minutes=30))
    midnight = now.astimezone(ist).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    cutoff = min(midnight, now - timedelta(hours=24)).isoformat(timespec='seconds')
    with db.conn() as c:
        c.execute('BEGIN IMMEDIATE')
        values = dict(c.execute("SELECT k,v FROM kv WHERE k IN ('paused','sending_paused','last_send_ts')"))
        if values.get('paused') == '1' or values.get('sending_paused') == '1':
            return 'Sending paused.'
        if time.time() - float(values.get('last_send_ts', 0)) < settings['min_gap_seconds']:
            return 'Waiting for the next send slot.'
        count = c.execute('SELECT COUNT(*) FROM leads WHERE sent_at>=? OR id IN (SELECT lead_id FROM send_attempts WHERE attempted_at>=?)', (cutoff, cutoff)).fetchone()[0]
        if count >= settings['daily_limit']:
            return 'Daily/24-hour sending limit reached.'
        if c.execute("SELECT 1 FROM leads WHERE lower(email)=lower(?) AND status IN ('sent','sending','send_uncertain')", (lead['email'],)).fetchone():
            return 'This recipient has already been contacted or has an unresolved delivery.'
        changed = c.execute("UPDATE leads SET status='sending' WHERE id=? AND status='pending'", (lead_id,)).rowcount
        if not changed:
            return 'Already being handled.'
        c.execute('INSERT INTO send_attempts VALUES (?, ?)', (lead_id, db.now()))
        c.execute('INSERT OR REPLACE INTO kv VALUES (?, ?)', ('last_send_ts', str(time.time())))
    try:
        send_email(lead['email'], lead['subject'], lead['body'])
    except Exception as exc:
        db.update_lead(lead_id, status='send_uncertain', error=str(exc))
        db.kv_set('sending_paused', '1')
        return 'Sending paused after an SMTP error. Check Gmail Sent before retrying.'
    db.update_lead(lead_id, status='sent', sent_at=db.now(), error=None)
    return f"Sent to {lead['email']} for {lead['hiring_role']}."
