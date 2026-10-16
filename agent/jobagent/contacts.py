"""Find a company's website, the text on it, and the best email address to write to."""
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .config import CFG
from .search import search

log = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PAGES = ["", "careers", "career", "jobs", "contact", "contact-us", "about", "about-us", "join-us"]
JUNK = ("noreply", "no-reply", "example.", "sentry", "wixpress", "domain.com", "email.com", "yourname",
        "privacy", "abuse", "support@", "billing", "sales@", "press@", "legal@")
JUNK_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
# Lower index = better person to receive a job application.
PRIORITY = [("hr", "career", "job", "talent", "hiring", "recruit", "people"),
            ("founder", "ceo", "cto"),
            ("hello", "contact", "info", "team", "connect", "hi@")]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/126 Safari/537.36"}


def domain_of(url):
    if not url:
        return None
    if "//" not in url:
        url = "https://" + url
    host = urlparse(url).netloc.lower().split(":")[0]
    return host.removeprefix("www.") or None


def is_blocked(text):
    t = (text or "").lower()
    if any(n in t for n in CFG["filters"].get("never_contact", [])):
        return True
    return any(re.search(rf"\b{re.escape(b)}\b", t) for b in CFG["filters"]["blocklist"])


DIRECTORY_SITES = ("wikipedia", "crunchbase", "tracxn", "zaubacorp", "justdial", "ambitionbox", "facebook",
                   "instagram", "twitter", "x.com", "youtube", "medium", "worldorgs", "f6s", "failory", "inc42",
                   "yourstory", "startupindia", "clutch", "goodfirms", "glassdoor", "naukri", "indeed",
                   "linkedin", "wellfound", "cutshort", "instahyre", "weekday", "myinternships", "builtin",
                   "seedtable", "growjo", "zoominfo", "rocketreach", "apollo.io", "pitchbook", "owler")


def is_directory(domain):
    return any(s in domain for s in DIRECTORY_SITES)


def find_website(company, city):
    """Search for the company's own homepage when the listing didn't give one."""
    for r in search(f"{company} {city or ''} official website", 5):
        d = domain_of(r["url"])
        if d and not is_blocked(d) and not is_directory(d):
            return d
    return None


def scrape_site(domain):
    """Returns (site_text, [emails], {email: page_url}) from the homepage and the usual careers/contact pages."""
    sources, texts = {}, []
    base = f"https://{domain}/"
    with httpx.Client(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        for page in PAGES:
            try:
                r = client.get(urljoin(base, page))
                if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
                    continue
            except httpx.HTTPError:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            found = [a["href"][7:].split("?")[0] for a in soup.select('a[href^="mailto:"]')]
            for tag in soup(["script", "style", "noscript", "svg"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ").split())
            for e in found + EMAIL_RE.findall(text):
                sources.setdefault(e.strip().strip(".").lower(), str(r.url))
            if page in ("", "about", "about-us", "careers"):
                texts.append(text[:1500])
    return " ".join(texts), clean_emails(sources, domain), sources


def clean_emails(emails, domain=None):
    out = []
    for e in {e.strip().strip(".").lower() for e in emails}:
        if any(j in e for j in JUNK) or e.endswith(JUNK_EXT) or len(e) > 60 or is_blocked(e):
            continue
        out.append(e)
    return sorted(out, key=lambda e: rank(e, domain))


def rank(email, domain):
    local, _, host = email.partition("@")
    same = 0 if domain and (host == domain or host.endswith("." + domain) or domain.endswith(host)) else 1
    tier = next((i for i, keys in enumerate(PRIORITY) if any(k in local or k in email for k in keys)), len(PRIORITY))
    return (same, tier, len(email))
