"""Fetches a single job posting URL the user gave us and extracts readable
text from it. This only ever fetches a specific page a person explicitly
provided — it is not a crawler and does not enumerate a site's listings."""
from __future__ import annotations

import requests
import trafilatura
from bs4 import BeautifulSoup

from app.config import settings
from app.models import JobPosting

_HEADERS = {
    "User-Agent": f"Mozilla/5.0 (compatible; personal-career-agent/1.0; +mailto:{settings.contact_email})"
}


def fetch(url: str) -> JobPosting:
    resp = requests.get(url, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    html = resp.text

    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    soup = BeautifulSoup(html, "html.parser")

    title = _meta(soup, "og:title") or (soup.title.string.strip() if soup.title and soup.title.string else "")
    company = _meta(soup, "og:site_name") or ""

    if not text.strip():
        # Fall back to a blunt full-page text extraction if trafilatura came up empty
        # (some ATS pages render content in ways it doesn't recognize).
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

    return JobPosting(
        title=title,
        company=company,
        url=url,
        source="direct_link",
        full_text=text.strip(),
        snippet=text.strip()[:600],
    )


def _meta(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
    return tag["content"].strip() if tag and tag.get("content") else ""
