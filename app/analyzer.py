import asyncio
import time
from collections import Counter
from typing import List, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.models import (
    DomainCount,
    LinkAnalysisResponse,
    LinkItem,
    LinkSummary,
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; DxoraLinkAnalyzer/1.0; +https://github.com)"
)


def _normalize_domain(netloc: str) -> str:
    netloc = netloc.lower().strip()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _classify_link(raw_href: str, resolved_url: str, base_domain: str) -> str:
    stripped = raw_href.strip().lower()
    if not stripped or stripped.startswith("#"):
        return "anchor"
    if stripped.startswith("mailto:"):
        return "mailto"
    if stripped.startswith("tel:"):
        return "tel"
    if stripped.startswith("javascript:"):
        return "javascript"

    parsed = urlparse(resolved_url)
    if parsed.scheme in ("http", "https"):
        link_domain = _normalize_domain(parsed.netloc)
        if link_domain == base_domain:
            return "internal"
        return "external"

    return "other"


async def _check_single_url(client: httpx.AsyncClient, url: str) -> Tuple[str, int | None]:
    try:
        resp = await client.head(url, follow_redirects=True, timeout=5.0)
        if resp.status_code in (405, 403):
            resp = await client.get(url, follow_redirects=True, timeout=5.0)
        return url, resp.status_code
    except Exception:
        return url, None


async def _verify_links_health(urls: List[str]) -> dict[str, int | None]:
    unique_http_urls = list(dict.fromkeys(urls))[:15]
    if not unique_http_urls:
        return {}

    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        tasks = [_check_single_url(client, u) for u in unique_http_urls]
        results = await asyncio.gather(*tasks)
    return dict(results)


def _compute_seo_score(summary: LinkSummary, items: List[LinkItem]) -> Tuple[int, List[str]]:
    score = 100
    recommendations: List[str] = []

    if summary.total_links == 0:
        return 40, ["No hyperlinks found on the page. Add internal navigation links to improve crawlability."]

    if summary.internal_links == 0:
        score -= 20
        recommendations.append("No internal links detected. Add internal links to strengthen site architecture.")

    if summary.empty_anchor_text_links > 0:
        penalty = min(15, summary.empty_anchor_text_links * 2)
        score -= penalty
        recommendations.append(
            f"{summary.empty_anchor_text_links} link(s) lack descriptive anchor text or aria-label/title attributes."
        )

    if summary.insecure_http_links > 0:
        penalty = min(15, summary.insecure_http_links * 3)
        score -= penalty
        recommendations.append(
            f"{summary.insecure_http_links} link(s) use insecure HTTP instead of HTTPS."
        )

    if summary.broken_links_found > 0:
        penalty = min(25, summary.broken_links_found * 8)
        score -= penalty
        recommendations.append(
            f"{summary.broken_links_found} broken link(s) (HTTP 4xx/5xx or unreachable) detected during status check."
        )

    unsafe_blank = sum(
        1
        for item in items
        if item.category == "external"
        and item.target == "_blank"
        and "noopener" not in item.rel
        and "noreferrer" not in item.rel
    )
    if unsafe_blank > 0:
        score -= min(10, unsafe_blank * 2)
        recommendations.append(
            f"{unsafe_blank} external target='_blank' link(s) missing rel='noopener' security attribute."
        )

    if not recommendations:
        recommendations.append("Great link hygiene! Internal structure, HTTPS usage, and anchor attributes look solid.")

    return max(0, score), recommendations


async def analyze_url(target_url: str, check_status: bool = False) -> LinkAnalysisResponse:
    start_time = time.perf_counter()
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=12.0) as client:
        response = await client.get(target_url)
        response.raise_for_status()

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    final_url = str(response.url)
    base_domain = _normalize_domain(urlparse(final_url).netloc)

    soup = BeautifulSoup(response.text, "html.parser")
    page_title = soup.title.string.strip() if soup.title and soup.title.string else None

    raw_anchors = soup.find_all("a")
    parsed_items: List[LinkItem] = []
    http_urls_to_check: List[str] = []
    external_domains: Counter = Counter()

    for tag in raw_anchors:
        raw_href = tag.get("href", "")
        resolved = urljoin(final_url, raw_href) if raw_href else final_url
        category = _classify_link(raw_href, resolved, base_domain)

        # Extract meaningful anchor text (fallback to aria-label or title)
        anchor_text = " ".join(tag.get_text(strip=True).split())
        if not anchor_text:
            anchor_text = (tag.get("aria-label") or tag.get("title") or "").strip()

        rel_attr = tag.get("rel") or []
        if isinstance(rel_attr, str):
            rel_list = [r.lower() for r in rel_attr.split()]
        else:
            rel_list = [str(r).lower() for r in rel_attr]

        target_attr = tag.get("target")
        parsed_resolved = urlparse(resolved)
        is_https = parsed_resolved.scheme == "https"

        if category == "external" and parsed_resolved.netloc:
            external_domains[_normalize_domain(parsed_resolved.netloc)] += 1

        if category in ("internal", "external") and parsed_resolved.scheme in ("http", "https"):
            http_urls_to_check.append(resolved)

        parsed_items.append(
            LinkItem(
                text=anchor_text,
                href=raw_href,
                resolved_url=resolved,
                category=category,
                rel=rel_list,
                target=target_attr,
                is_nofollow="nofollow" in rel_list,
                is_https=is_https,
            )
        )

    status_map: dict[str, int | None] = {}
    if check_status and http_urls_to_check:
        status_map = await _verify_links_health(http_urls_to_check)
        for item in parsed_items:
            if item.resolved_url in status_map:
                code = status_map[item.resolved_url]
                item.status_code = code
                item.is_broken = code is None or code >= 400

    unique_urls = len({item.resolved_url for item in parsed_items})
    broken_checked = sum(1 for item in parsed_items if item.status_code is not None or item.is_broken is True)
    broken_found = sum(1 for item in parsed_items if item.is_broken is True)

    summary = LinkSummary(
        total_links=len(parsed_items),
        unique_urls=unique_urls,
        internal_links=sum(1 for i in parsed_items if i.category == "internal"),
        external_links=sum(1 for i in parsed_items if i.category == "external"),
        anchor_links=sum(1 for i in parsed_items if i.category == "anchor"),
        mailto_links=sum(1 for i in parsed_items if i.category == "mailto"),
        tel_links=sum(1 for i in parsed_items if i.category == "tel"),
        other_links=sum(1 for i in parsed_items if i.category in ("javascript", "other")),
        nofollow_links=sum(1 for i in parsed_items if i.is_nofollow),
        insecure_http_links=sum(
            1 for i in parsed_items if i.category in ("internal", "external") and not i.is_https
        ),
        empty_anchor_text_links=sum(1 for i in parsed_items if not i.text),
        broken_links_checked=broken_checked,
        broken_links_found=broken_found,
    )

    seo_score, recommendations = _compute_seo_score(summary, parsed_items)
    top_domains = [
        DomainCount(domain=dom, count=cnt)
        for dom, cnt in external_domains.most_common(10)
    ]

    return LinkAnalysisResponse(
        target_url=target_url,
        final_url=final_url,
        page_title=page_title,
        http_status=response.status_code,
        response_time_ms=elapsed_ms,
        seo_health_score=seo_score,
        seo_recommendations=recommendations,
        summary=summary,
        top_external_domains=top_domains,
        links=parsed_items,
    )
