"""100% Free, permanent web search with multi-layer fallback.
No API keys, no subscriptions, and no trial limits that expire.
"""
import logging
import time
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from .config import env

log = logging.getLogger(__name__)
logging.getLogger("primp").setLevel(logging.WARNING)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}


def unwrap_ddg_url(raw_url):
    """Unwrap DuckDuckGo redirect link to its actual target URL."""
    if not raw_url:
        return ""
    if "uddg=" in raw_url:
        parsed = parse_qs(urlparse(raw_url).query)
        return parsed.get("uddg", [raw_url])[0]
    if raw_url.startswith("//"):
        return "https:" + raw_url
    return raw_url


def _search_ddgs(query, n=15, timelimit=None, page=1):
    """Layer 1: ddgs multi-engine Python aggregator."""
    from ddgs import DDGS
    for attempt in range(2):
        if attempt > 0:
            time.sleep(2)
        try:
            kwargs = {"region": "in-en", "max_results": n, "page": page}
            if timelimit:
                kwargs["timelimit"] = timelimit
            raw = DDGS().text(query, **kwargs)
            results = []
            for x in raw:
                href = unwrap_ddg_url(x.get("href", ""))
                if href and href.startswith("http"):
                    results.append({"title": x.get("title", ""), "url": href, "snippet": x.get("body", "")})
            if results:
                return results
        except Exception:
            pass
    return []


def _search_html(query, n=15, page=1, timelimit=None):
    """Layer 2: Direct DuckDuckGo HTML endpoint (no JS/tokens needed, supports pagination)."""
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query, "s": str((page - 1) * 30)}
    if timelimit:
        data["df"] = timelimit
    try:
        r = httpx.post(url, data=data, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for body in soup.select(".result__body"):
            t_el = body.select_one(".result__title a")
            s_el = body.select_one(".result__snippet")
            if not t_el:
                continue
            href = unwrap_ddg_url(t_el.get("href", ""))
            if not href or not href.startswith("http"):
                continue
            title = t_el.get_text(strip=True)
            snippet = s_el.get_text(strip=True) if s_el else ""
            results.append({"title": title, "url": href, "snippet": snippet})
            if len(results) >= n:
                break
        return results
    except Exception as e:
        log.debug("html search error: %s", e)
        return []


def _search_lite(query, n=15):
    """Layer 3: DuckDuckGo Lite endpoint (ultra-light, extreme uptime)."""
    url = "https://lite.duckduckgo.com/lite/"
    try:
        r = httpx.post(url, data={"q": query}, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for a in soup.select("a.result-link"):
            href = unwrap_ddg_url(a.get("href", ""))
            if not href or not href.startswith("http"):
                continue
            title = a.get_text(strip=True)
            tr = a.find_parent("tr")
            nxt = tr.find_next_sibling("tr") if tr else None
            snippet = nxt.get_text(strip=True) if nxt else ""
            results.append({"title": title, "url": href, "snippet": snippet})
            if len(results) >= n:
                break
        return results
    except Exception as e:
        log.debug("lite search error: %s", e)
        return []


def search(query, n=15, timelimit=None, page=1):
    """Searches using optional Tavily or 3 cascading free layers. Never runs out of credits or expires."""
    # Optional Tavily (from original code, used only if key is set)
    if env("TAVILY_API_KEY") and page == 1 and not timelimit:
        try:
            r = httpx.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {env('TAVILY_API_KEY')}"},
                json={"query": query, "max_results": n, "country": "india"},
                timeout=25,
            )
            if r.status_code == 200:
                results = [{"title": x["title"], "url": x["url"], "snippet": x.get("content", "")[:600]}
                           for x in r.json().get("results", []) if x.get("url")]
                if results:
                    return results
        except Exception:
            pass

    # 1. Try DDGS library
    results = _search_ddgs(query, n=n, timelimit=timelimit, page=page)
    if results:
        return results

    # 2. Fall back to Direct HTML endpoint with pagination
    results = _search_html(query, n=n, page=page, timelimit=timelimit)
    if results:
        return results

    # 3. Fall back to Lite endpoint
    results = _search_lite(query, n=n) if page == 1 and not timelimit else []
    if results:
        return results

    log.warning("all free search layers returned 0 results for %r", query)
    return []


def with_page_text(results, chars=2500):
    """Replace each snippet with the start of the page itself, so list articles and job pages
    show the company names. Falls back to the snippet when the site blocks us."""
    with httpx.Client(headers=HEADERS, timeout=10, follow_redirects=True) as client:
        for r in results:
            try:
                resp = client.get(r["url"])
                if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
                        tag.decompose()
                    text = " ".join(soup.get_text(" ").split())
                    if len(text) > len(r.get("snippet", "")):
                        # Indexed post snippets can contain an email missing from
                        # LinkedIn's public/login page. Keep that evidence intact.
                        r["snippet"] = r.get("snippet", "") + "\n" + text[:chars]
            except httpx.HTTPError:
                pass
    return results
