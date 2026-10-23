"""Conservative automatic sending with persistent quota and delivery state."""
import random
import re
import time
from datetime import datetime, timedelta, timezone

from . import db
from .config import CFG
from .mailer import send_email
from .deadlines import deadline_for, expired, in_window, metadata
from .screening import experience_reason, is_agency, is_free_mail


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


def outreach_kind(company, results):
    if evidence_matches(company, results):
        return 'hiring'
    # An unrelated advertised role must never become a fallback application.
    if company.get('hiring_role') or not company.get('is_ai_company'):
        return None
    source = company.get('source_url') or company.get('website')
    name = (company.get('company') or '').strip().lower()
    for result in results:
        text = (result.get('title', '') + ' ' + result.get('snippet', '')).lower()
        if name and result.get('url') == source and name in text and re.search(
                r'\b(ai|ml|artificial intelligence|machine learning|generative ai|llm)\b', text):
            return 'company'
    return None


def pending_queue():
    """Hiring applications first; oldest first within each priority."""
    leads = [lead for lead in db.leads_with_status('pending')
             if db.kv_get(f"auto_eligible:{lead['id']}") == '1']
    active = []
    for lead in leads:
        if expired(lead['id']):
            db.update_lead(lead['id'], status='expired')
        else:
            active.append(lead)
    far_future = datetime.max.replace(tzinfo=timezone.utc)
    return sorted(active, key=lambda lead: (not bool(lead.get('hiring_role')), deadline_for(lead['id']) or far_future, lead['id']))


def sendable(lead):
    """Queued drafts that can go out without manual review."""
    return not (metadata(lead['id']).get('quote') and not deadline_for(lead['id']))


def sleep_state(limit):
    """'full': today's cap is used, so no searching or AI work until midnight IST.
    'queued': enough sendable drafts already wait to fill today's cap, so skip new searches.
    None: keep working."""
    used = db.used_today()
    if used >= limit:
        return 'full'
    if used + sum(sendable(lead) for lead in pending_queue()) >= limit:
        return 'queued'
    return None


def send_one(lead_id):
    """Reserve before SMTP; uncertain/failed deliveries are never auto-retried."""
    settings = CFG['sending']
    lead = db.get_lead(lead_id)
    if not lead or lead['status'] != 'pending':
        return 'Not pending.'
    if expired(lead_id):
        db.update_lead(lead_id, status='expired')
        return 'Expired: application deadline has passed.'
    reason = experience_reason(lead.get('hiring_role'), db.kv_get(f'experience:{lead_id}'))
    if reason:
        db.update_lead(lead_id, status='skipped_experience', error=reason)
        return f'Skipped: {reason}.'
    if is_agency(lead.get('company')):
        db.update_lead(lead_id, status='skipped_agency', error='recruitment agency or job portal')
        return 'Skipped: recruitment agency or job portal.'
    if is_free_mail(lead.get('email')) and db.kv_get(f'approved:{lead_id}') != '1':
        db.kv_set(f'auto_eligible:{lead_id}', '0')
        db.kv_set(f'hold:{lead_id}', 'Only a personal email address (not the company domain) was found. Check the post is genuine before sending.')
        return 'Held for review: personal email address.'
    if lead.get('hiring_role') and db.kv_get(f'deadline_scanned:{lead_id}') != '1':
        return 'Missing deadline check: waiting for source refresh.'
    if metadata(lead_id).get('quote') and not deadline_for(lead_id):
        return 'Missing verified deadline: manual review required.'
    fallback = not lead.get('hiring_role') and db.kv_get(f'outreach_kind:{lead_id}') == 'company'
    if (not relevant_role(lead.get('hiring_role')) and not fallback) or db.kv_get(f'auto_eligible:{lead_id}') != '1':
        db.kv_set(f'auto_eligible:{lead_id}', '0')  # leave the queue instead of being retried every minute
        return 'Not eligible: requires a verified advertised AI/ML role.'
    if not lead.get('email_source') or not lead.get('subject') or not lead.get('body'):
        db.kv_set(f'auto_eligible:{lead_id}', '0')
        return 'Missing verified contact or draft.'
    if not in_window(datetime.now(timezone.utc)):
        return 'Outside sending hours.'
    with db.conn() as c:
        c.execute('BEGIN IMMEDIATE')
        values = dict(c.execute("SELECT k,v FROM kv WHERE k IN ('paused','sending_paused','last_send_ts','next_send_ts')"))
        if values.get('paused') == '1' or values.get('sending_paused') == '1':
            return 'Sending paused.'
        ready_at = max(float(values.get('last_send_ts', 0)) + settings['min_gap_seconds'], float(values.get('next_send_ts', 0)))
        if time.time() < ready_at:
            return 'Waiting for the next send slot.'
        if db.used_today(c) >= settings['daily_limit']:
            return 'Daily sending limit reached; resumes at midnight IST.'
        if c.execute("SELECT 1 FROM leads WHERE lower(email)=lower(?) AND status IN ('sent','sending','send_uncertain')", (lead['email'],)).fetchone():
            c.execute("UPDATE leads SET status='duplicate' WHERE id=?", (lead_id,))
            return 'This recipient has already been contacted or has an unresolved delivery.'
        changed = c.execute("UPDATE leads SET status='sending' WHERE id=? AND status='pending'", (lead_id,)).rowcount
        if not changed:
            return 'Already being handled.'
        c.execute('INSERT INTO send_attempts VALUES (?, ?)', (lead_id, db.now()))
        c.execute('INSERT OR REPLACE INTO kv VALUES (?, ?)', ('last_send_ts', str(time.time())))
        # A random extra wait keeps sends from landing on a fixed, machine-like rhythm.
        jitter = random.uniform(0, settings.get('gap_jitter_seconds', 0))
        c.execute('INSERT OR REPLACE INTO kv VALUES (?, ?)', ('next_send_ts', str(time.time() + settings['min_gap_seconds'] + jitter)))
    try:
        send_email(lead['email'], lead['subject'], lead['body'])
    except Exception as exc:
        db.update_lead(lead_id, status='send_uncertain', error=str(exc))
        db.kv_set('sending_paused', '1')
        return 'Sending paused after an SMTP error. Check Gmail Sent before retrying.'
    db.update_lead(lead_id, status='sent', sent_at=db.now(), error=None)
    target = lead.get('hiring_role') or 'AI/ML opportunities (company outreach)'
    return f"Sent to {lead['email']} for {target}."
