"""Web search: Tavily when a key is set, otherwise free DuckDuckGo."""
import logging
import time

import httpx
from bs4 import BeautifulSoup

from .config import env

log = logging.getLogger(__name__)
logging.getLogger("primp").setLevel(logging.WARNING)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/126 Safari/537.36"}


def search(query, n=10):
    """Returns [{title, url, snippet}]."""
    try:
        if env("TAVILY_API_KEY"):
            r = httpx.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {env('TAVILY_API_KEY')}"},
                json={"query": query, "max_results": n, "country": "india"},
                timeout=30,
            )
            r.raise_for_status()
            return [{"title": x["title"], "url": x["url"], "snippet": x.get("content", "")[:600]}
                    for x in r.json().get("results", [])]

        from ddgs import DDGS
        for attempt in range(3):
            time.sleep(4 + attempt * 10)  # DuckDuckGo throttles rapid-fire queries
            try:
                return [{"title": x.get("title", ""), "url": x.get("href", ""), "snippet": x.get("body", "")}
                        for x in DDGS().text(query, region="in-en", max_results=n)]
            except Exception as e:
                if "No results" not in str(e) or attempt == 2:
                    raise
    except Exception as e:  # one failing query must not stop the cycle
        log.warning("search failed for %r: %s", query, e)
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
                    if len(text) > len(r["snippet"]):
                        r["snippet"] = text[:chars]
            except httpx.HTTPError:
                pass
    return results
