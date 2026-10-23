"""One discovery cycle: search -> pick companies -> find email -> draft -> store as 'pending'."""
import json
import logging

from . import db
from .config import CFG
from .contacts import clean_emails, domain_of, find_website, is_blocked, is_directory, listed_contact, scrape_site, search_email_fallback
from .llm import compose_email, extract_companies
from .search import search, with_page_text
from .sending import outreach_kind
from .deadlines import save_evidence, expired
from .screening import experience_reason, is_free_mail, save_experience, scam_reason, verified_experience

log = logging.getLogger(__name__)


def queries(cycle_number=0):
    s = CFG["search"]
    # Rotate combinations so each cycle explores a different role and source.
    variants = [f'"{role}" {city} {suffix}'
                for role in CFG['profile']['target_roles']
                for city in s['cities_for_queries']
                for suffix in ('startup hiring', 'site:linkedin.com/posts hiring email',
                               'site:linkedin.com/feed/update hiring')]
    count = min(s.get('rotating_queries', 9), len(variants))
    for i in range(count):
        yield variants[(cycle_number * count + i) % len(variants)]
    for q in s["queries"]:
        for city in s["cities_for_queries"] if "{city}" in q else [None]:
            yield q.format(city=city) if city else q


def in_target_city(city):
    if not city:
        return False
    c_low = city.lower()
    return any(c.lower() in c_low for c in CFG["search"]["cities"]) or "ncr" in c_low or "remote" in c_low


def run_cycle():
    """Returns the ids of new leads that now have a draft waiting for approval."""
    new_ids = []
    n_results = CFG["search"].get("results_per_query", 20)
    cycle_number = int(db.kv_get('discovery_cycle', '0'))
    db.kv_set('discovery_cycle', cycle_number + 1)
    for candidate in db.retry_candidates():
        try:
            candidate['is_ai_company'] = True  # already passed discovery filters
            lead_id = process_company(candidate)
            if lead_id:
                new_ids.append(lead_id)
        except Exception:
            log.exception('Retry failed for lead %s', candidate['id'])
    for q in queries(cycle_number):
        results = [r for r in search(q, n_results) if r.get("url") and not db.url_seen(r["url"])]
        # If top results are already exhausted from previous days, search with freshness timelimit="m" (past month)
        if len(results) < 3:
            fresh = search(q, n_results, timelimit="w")
            fresh += search(q, n_results, page=2 + cycle_number % 3)
            fresh = [r for r in fresh if r.get("url") and not db.url_seen(r["url"])]
            seen = {r["url"] for r in results}
            for r in fresh:
                if r["url"] not in seen:
                    results.append(r)
                    seen.add(r["url"])

        if not results:
            continue

        results = with_page_text(results)
        log.info("%r -> %d new results", q, len(results))
        # Small batches avoid burying individual posts in oversized LLM input.
        for start in range(0, len(results), 5):
            batch = results[start:start + 5]
            try:
                companies = extract_companies(batch)
                for c in companies:
                    lead_id = process_company(c, batch)
                    if lead_id:
                        new_ids.append(lead_id)
                db.mark_urls([r['url'] for r in batch])
            except Exception:
                log.exception('Discovery batch failed; leaving its URLs available for retry')
    return new_ids


def process_company(c, results=None):
    kind = outreach_kind(c, results or [])
    if not kind:
        return None
    # Checked before scraping or drafting, so rejected posts cost no further AI calls.
    reason = scam_reason(c, results or []) or (
        kind == 'hiring' and experience_reason(c.get('hiring_role'), verified_experience(c, results or [])))
    if reason:
        log.info('skipped %s (%s): %s', c.get('company'), c.get('hiring_role'), reason)
        return None
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
    listed, listed_source = listed_contact(c, results or [])
    if listed:
        sources[listed] = listed_source
        # Use the application address explicitly given in the hiring source first.
        emails = [listed] + [e for e in clean_emails(sources, domain) if e != listed]
    if emails and is_free_mail(emails[0]):
        # A personal address in a post is a common impersonation trick: prefer the company's own domain.
        emails = [e for e in emails if not is_free_mail(e)] + [e for e in emails if is_free_mail(e)]
    if not emails:
        fallback_emails, fallback_sources = search_email_fallback(domain, name)
        if fallback_emails:
            emails = fallback_emails
            sources.update(fallback_sources)
            log.info("found email via search fallback for %s: %s", name, emails[0])

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
    save_evidence(lead_id, c, results or [])
    save_experience(lead_id, c, results or [])
    if expired(lead_id):
        db.update_lead(lead_id, status='expired')
        return None
    try:
        subject, body = compose_email(db.get_lead(lead_id), site_text)
        db.update_lead(lead_id, subject=subject, body=body, status="pending")
        db.kv_set(f"outreach_kind:{lead_id}", kind)
        held = is_free_mail(emails[0])
        db.kv_set(f"auto_eligible:{lead_id}", '0' if held else '1')
        if held:
            db.kv_set(f"hold:{lead_id}", 'Only a personal email address (not the company domain) was found. Check the post is genuine before sending.')
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
