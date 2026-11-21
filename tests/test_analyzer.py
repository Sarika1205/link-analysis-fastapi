from fastapi.testclient import TestClient
from app.main import app
from app.analyzer import _classify_link, _normalize_domain

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_domain_normalization():
    assert _normalize_domain("WWW.Example.COM") == "example.com"


def test_link_classification():
    assert _classify_link("/about", "https://example.com/about", "example.com") == "internal"
    assert _classify_link("https://google.com", "https://google.com", "example.com") == "external"
    assert _classify_link("#section", "https://example.com/#section", "example.com") == "anchor"
    assert _classify_link("mailto:hi@example.com", "mailto:hi@example.com", "example.com") == "mailto"
    assert _classify_link("tel:+12345", "tel:+12345", "example.com") == "tel"
