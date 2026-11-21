from typing import List, Optional, Dict
from pydantic import BaseModel, HttpUrl, Field


class LinkAnalysisRequest(BaseModel):
    url: HttpUrl = Field(..., description="Target webpage URL to analyze")
    check_status: bool = Field(
        default=False,
        description="Whether to asynchronously verify HTTP reachability of extracted links (capped at 15 links for speed)"
    )


class LinkItem(BaseModel):
    text: str
    href: str
    resolved_url: str
    category: str  # internal, external, mailto, tel, anchor, javascript, other
    rel: List[str] = []
    target: Optional[str] = None
    is_nofollow: bool = False
    is_https: bool = False
    status_code: Optional[int] = None
    is_broken: Optional[bool] = None


class DomainCount(BaseModel):
    domain: str
    count: int


class LinkSummary(BaseModel):
    total_links: int
    unique_urls: int
    internal_links: int
    external_links: int
    anchor_links: int
    mailto_links: int
    tel_links: int
    other_links: int
    nofollow_links: int
    insecure_http_links: int
    empty_anchor_text_links: int
    broken_links_checked: int
    broken_links_found: int


class LinkAnalysisResponse(BaseModel):
    target_url: str
    final_url: str
    page_title: Optional[str]
    http_status: int
    response_time_ms: float
    seo_health_score: int = Field(..., ge=0, le=100, description="Heuristic SEO & Link Health Score (0-100)")
    seo_recommendations: List[str]
    summary: LinkSummary
    top_external_domains: List[DomainCount]
    links: List[LinkItem]
