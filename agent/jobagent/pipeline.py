"""One discovery cycle: search -> pick companies -> find email -> draft -> store as 'pending'."""
import json
import logging

from . import db
from .config import CFG
from .contacts import clean_emails, domain_of, find_website, is_blocked, is_directory, scrape_site
from .llm import compose_email, extract_companies
from .search import search, with_page_text

log = logging.getLogger(__name__)


def queries():
    s = CFG["search"]
    for q in s["queries"]:
        for city in s["cities_for_queries"] if "{city}" in q else [None]:
            yield q.format(city=city) if city else q


def in_target_city(city):
    return bool(city) and any(c.lower() in city.lower() for c in CFG["search"]["cities"])


def run_cycle():
    """Returns the ids of new leads that now have a draft waiting for approval."""
    new_ids = []
    for q in queries():
        results = [r for r in search(q, CFG["search"]["results_per_query"]) if r["url"] and not db.url_seen(r["url"])]
        db.mark_urls([r["url"] for r in results])
        results = with_page_text(results)
        log.info("%r -> %d new results", q, len(results))
        search_text = " ".join(r["title"] + " " + r["snippet"] for r in results).lower()
        for c in extract_companies(results):
            lead_id = process_company(c, search_text)
            if lead_id:
                new_ids.append(lead_id)
    return new_ids


def process_company(c, search_text=""):
    name = (c.get("company") or "").strip()
    f = CFG["filters"]
    if not name or is_blocked(name) or not c.get("is_ai_company") or not in_target_city(c.get("city")):
        return None
    if not c.get("est_employees") or c["est_employees"] > f["max_employees"]:
        return None

    domain = domain_of(c.get("website"))
    if not domain or is_directory(domain):
        domain = find_website(name, c.get("city"))
    if not domain or is_blocked(domain) or db.domain_known(domain):
        return None

    site_text, emails, sources = scrape_site(domain)
    listed = (c.get("contact_email") or "").strip().lower()
    if listed and listed in search_text and listed not in sources:  # never trust an address the LLM may have invented
        sources[listed] = c.get("job_url") or "search result"
        emails = clean_emails(sources, domain)
    fields = dict(domain=domain, company=name, website=f"https://{domain}", city=c.get("city"),
                  what_they_do=c.get("what_they_do"), hiring_role=c.get("hiring_role"), job_url=c.get("job_url"),
                  why=c.get("why"), est_employees=c.get("est_employees"), all_emails=json.dumps(emails))
    if not emails:
        db.add_lead(**fields, status="no_contact")
        log.info("no email found for %s (%s)", name, domain)
        return None

    lead_id = db.add_lead(**fields, email=emails[0], email_source=sources.get(emails[0]))
    if not lead_id:
        return None
    try:
        subject, body = compose_email(db.get_lead(lead_id), site_text)
        db.update_lead(lead_id, subject=subject, body=body, status="pending")
        db.kv_set(f"site_text:{lead_id}", site_text[:2500])
        log.info("draft ready: %s <%s>", name, emails[0])
        return lead_id
    except Exception as e:
        db.update_lead(lead_id, status="failed", error=f"compose: {e}")
        log.warning("compose failed for %s: %s", name, e)
        return None


def redraft(lead_id, instruction=""):
    lead = db.get_lead(lead_id)
    subject, body = compose_email(lead, db.kv_get(f"site_text:{lead_id}", ""), instruction)
    db.update_lead(lead_id, subject=subject, body=body)
    return db.get_lead(lead_id)
