# Webpage Link Analysis API (Python 3 & FastAPI)

A fast, asynchronous **Link Analysis & SEO Audit service** built with **Python 3** and **FastAPI**. It extracts all hyperlinks from any target webpage, resolves relative paths, classifies link types, checks HTTP status codes concurrently, and computes an actionable **SEO Link Health Score**.

## Features
- **Full Link Extraction & Resolution:** Resolves relative URLs against the final redirected URL using `urllib.parse.urljoin`.
- **Smart Link Classification:** Categorizes links into `internal`, `external`, `anchor`, `mailto`, `tel`, `javascript`, and `other`.
- **Concurrent Broken-Link Verification:** Optional asynchronous HTTP `HEAD`/`GET` reachability checks (`check_status=true`) via `httpx.AsyncClient`.
- **SEO & Security Hygiene Audit:** Flags missing anchor text, insecure `http://` links, `rel="nofollow"` attributes, and external `target="_blank"` links missing `rel="noopener"`, generating a `0–100` SEO Health Score.
- **Interactive Web Dashboard + OpenAPI Docs:** Built-in UI at `/` and interactive Swagger docs at `/docs`.

## Tech Stack
- **Python 3.10+**
- **FastAPI** & **Uvicorn**
- **HTTPX** (Async HTTP client)
- **BeautifulSoup4** (HTML parsing)
- **Pydantic v2** (Strict request/response validation)

## Quick Start (Local Setup)

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/link-analysis-fastapi.git
cd link-analysis-fastapi

# 2. Create & activate a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn app.main:app --reload
```

Open in your browser:
- **Interactive Dashboard:** `http://127.0.0.1:8000/`
- **Swagger API Docs:** `http://127.0.0.1:8000/docs`

## API Endpoints

### `POST /api/analyze`
**Request Body:**
```json
{
  "url": "https://example.com",
  "check_status": true
}
```

### `GET /api/analyze?url=https://example.com&check_status=false`
Returns structured JSON containing `seo_health_score`, `seo_recommendations`, `summary` metrics, `top_external_domains`, and detailed `links`.

## Running Tests
```bash
pytest
```
