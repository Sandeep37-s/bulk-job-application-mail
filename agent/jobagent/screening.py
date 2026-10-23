"""Experience-level and fake-job screening for hiring posts (LinkedIn posts included)."""
import re

from . import db

MAX_YEARS = 2  # 0-2 years or fresher/junior is sent; 3+ years is skipped
SENIOR_TITLE = re.compile(r'\b(senior|sr|lead|principal|staff|manager)\b', re.I)
ENTRY = re.compile(r'\b(fresher|freshers|entry[- ]level|junior|jr|graduate|new grad|no experience)\b', re.I)
YEARS = re.compile(r'(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*\d+(?:\.\d+)?\s*\+?\s*)?(?:years?|yrs?)\b', re.I)

FREE_MAIL = ('gmail.com', 'yahoo.com', 'yahoo.in', 'outlook.com', 'hotmail.com', 'live.com', 'rediffmail.com',
             'proton.me', 'protonmail.com', 'icloud.com', 'aol.com', 'zoho.com', 'yandex.com', 'gmx.com')
# Patterns that real employers do not use; any one means the post is not emailed.
SCAM = [
    (r'\b(registration|joining|training|security|processing|onboarding|verification|documentation|kit|interview)\s+'
     r'(fee|fees|charge|charges|deposit|amount)\b', 'asks the candidate to pay a fee'),
    (r'\brefundable\b.{0,30}\b(deposit|fee|amount)\b', 'asks for a refundable deposit'),
    (r'\bpay\b.{0,40}\b(to (apply|join|register)|before (joining|the interview)|for (the )?(training|offer letter))\b',
     'asks the candidate to pay'),
    (r'\b(guaranteed|100\s*%)\s+(job|placement|selection|joining)\b', 'promises a guaranteed job'),
    (r'\bno interview\b', 'offers a job without an interview'),
    (r'\bearn\b.{0,25}(?:rs\.?|₹|inr|\$)?\s*[\d,]+\s*k?\s*(?:per|/|a|every)\s*(?:day|week)\b', 'promises quick daily/weekly earnings'),
    (r'\b(whatsapp|telegram)\b.{0,30}\b(only|to apply|for (the )?(job|interview|joining))\b', 'applications only via WhatsApp/Telegram'),
    (r'\b(task|like|review)[- ]based (job|work|income)\b|\bdata entry\b.{0,30}\bearn\b', 'task/earning scheme, not a real role'),
]


def min_years(text):
    """Smallest experience requirement in a quote; 0 for fresher/junior; None if not stated."""
    if not text:
        return None
    found = [float(m) for m in YEARS.findall(text)]
    if found:
        return min(found)
    return 0.0 if ENTRY.search(text) else None


def experience_reason(role, experience_text):
    """None when the role suits 0-2 years of experience; otherwise why it is skipped.
    Fresher/junior in the title wins over a senior word ("Junior ML Engineer, Lead team")."""
    if role and SENIOR_TITLE.search(role) and not ENTRY.search(role):
        return f'senior title: {role}'
    years = min_years(experience_text)
    if years is not None and years > MAX_YEARS:
        return f'needs {years:g}+ years: "{experience_text}"'
    return None


def source_text(company, results):
    source = company.get('source_url') or company.get('job_url')
    return ' '.join(r.get('title', '') + ' ' + r.get('snippet', '') for r in results if r.get('url') == source)


def verified_experience(company, results):
    """The model's experience quote, only if it appears in the supporting source."""
    quote = (company.get('experience_text') or '').strip()
    if not quote or len(quote) > 200 or quote.lower() not in source_text(company, results).lower():
        return None
    return quote


def scam_reason(company, results):
    text = source_text(company, results) + ' ' + (company.get('contact_email') or '')
    for pattern, reason in SCAM:
        if re.search(pattern, text, re.I):
            return reason
    return None


def is_free_mail(email):
    return (email or '').lower().rpartition('@')[2] in FREE_MAIL


def save_experience(lead_id, company, results):
    quote = verified_experience(company, results)
    if quote:
        db.kv_set(f'experience:{lead_id}', quote)
