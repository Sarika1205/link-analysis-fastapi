import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.analyzer import analyze_url
from app.models import LinkAnalysisRequest, LinkAnalysisResponse

app = FastAPI(
    title="Dxora Link Analysis API",
    description="High-performance FastAPI service for extracting, classifying, and auditing webpage hyperlinks & SEO link health.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Link Analysis Studio | FastAPI</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
  <div class="max-w-6xl mx-auto px-4 py-10">
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6 mb-8">
      <div>
        <span class="text-xs font-semibold uppercase tracking-widest text-indigo-400">Python 3 &bull; FastAPI Practical</span>
        <h1 class="text-3xl font-bold text-white mt-1">Webpage Link Analysis Engine</h1>
        <p class="text-slate-400 text-sm mt-1">Extract internal/external links, inspect anchor hygiene, check HTTP status, and score SEO health.</p>
      </div>
      <div class="flex gap-3">
        <a href="/docs" class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm font-medium text-indigo-300 border border-slate-700 transition">Swagger API Docs &rarr;</a>
      </div>
    </header>

    <form id="analyzeForm" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-8">
      <div class="flex flex-col md:flex-row gap-4">
        <input
          id="urlInput"
          type="url"
          required
          placeholder="https://example.com"
          value="https://example.com"
          class="flex-1 px-4 py-3 rounded-xl bg-slate-950 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
        <label class="flex items-center gap-2 text-sm text-slate-300 px-2 cursor-pointer select-none">
          <input id="checkStatus" type="checkbox" class="w-4 h-4 rounded accent-indigo-500" />
          <span>Verify Link Status (HTTP HEAD)</span>
        </label>
        <button
          id="submitBtn"
          type="submit"
          class="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-white transition cursor-pointer"
        >
          Analyze Links
        </button>
      </div>
    </form>

    <div id="errorBox" class="hidden bg-red-950/60 border border-red-700 text-red-200 px-5 py-4 rounded-xl mb-6"></div>

    <div id="results" class="hidden space-y-6">
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <p class="text-xs text-slate-400 uppercase">SEO Health Score</p>
          <p id="statScore" class="text-3xl font-bold text-emerald-400 mt-1">--</p>
        </div>
        <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <p class="text-xs text-slate-400 uppercase">Total Links</p>
          <p id="statTotal" class="text-3xl font-bold text-white mt-1">--</p>
        </div>
        <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <p class="text-xs text-slate-400 uppercase">Internal</p>
          <p id="statInternal" class="text-3xl font-bold text-sky-400 mt-1">--</p>
        </div>
        <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <p class="text-xs text-slate-400 uppercase">External</p>
          <p id="statExternal" class="text-3xl font-bold text-amber-400 mt-1">--</p>
        </div>
        <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <p class="text-xs text-slate-400 uppercase">Nofollow</p>
          <p id="statNofollow" class="text-3xl font-bold text-purple-400 mt-1">--</p>
        </div>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div class="flex flex-wrap justify-between items-center gap-2 mb-3">
          <h2 class="text-lg font-semibold text-white" id="pageTitle">Page Audit</h2>
          <span id="metaInfo" class="text-xs text-slate-400"></span>
        </div>
        <ul id="recList" class="list-disc list-inside text-sm text-slate-300 space-y-1"></ul>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div class="p-4 border-b border-slate-800 flex flex-wrap justify-between items-center gap-3">
          <h3 class="font-semibold text-white">Extracted Hyperlinks</h3>
          <select id="categoryFilter" class="bg-slate-950 border border-slate-700 text-sm rounded-lg px-3 py-1.5 text-slate-200">
            <option value="all">All Categories</option>
            <option value="internal">Internal</option>
            <option value="external">External</option>
            <option value="anchor">Anchor (#)</option>
            <option value="mailto">Mailto</option>
            <option value="tel">Tel</option>
          </select>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-slate-950 text-slate-400 uppercase text-xs">
              <tr>
                <th class="px-4 py-3">Category</th>
                <th class="px-4 py-3">Anchor Text</th>
                <th class="px-4 py-3">Resolved URL</th>
                <th class="px-4 py-3">Attributes</th>
                <th class="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody id="linksTable" class="divide-y divide-slate-800"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentLinks = [];
    const form = document.getElementById('analyzeForm');
    const errorBox = document.getElementById('errorBox');
    const results = document.getElementById('results');
    const submitBtn = document.getElementById('submitBtn');
    const categoryFilter = document.getElementById('categoryFilter');

    function renderTable() {
      const filter = categoryFilter.value;
      const filtered = filter === 'all' ? currentLinks : currentLinks.filter(l => l.category === filter);
      const tbody = document.getElementById('linksTable');
      tbody.innerHTML = filtered.map(link => `
        <tr class="hover:bg-slate-800/50">
          <td class="px-4 py-3">
            <span class="px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-indigo-300 border border-slate-700">${link.category}</span>
          </td>
          <td class="px-4 py-3 text-slate-200 max-w-xs truncate">${link.text || '<span class="text-slate-500 italic">(empty)</span>'}</td>
          <td class="px-4 py-3 max-w-md truncate">
            <a href="${link.resolved_url}" target="_blank" class="text-sky-400 hover:underline">${link.resolved_url}</a>
          </td>
          <td class="px-4 py-3 text-xs text-slate-400">
            ${link.is_nofollow ? '<span class="text-amber-400 mr-1">nofollow</span>' : ''}
            ${link.target ? `<span>target=${link.target}</span>` : ''}
          </td>
          <td class="px-4 py-3 text-xs">
            ${link.status_code ? `<span class="${link.is_broken ? 'text-red-400' : 'text-emerald-400'} font-semibold">${link.status_code}</span>` : '<span class="text-slate-600">-</span>'}
          </td>
        </tr>
      `).join('');
    }

    categoryFilter.addEventListener('change', renderTable);

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorBox.classList.add('hidden');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Analyzing...';

      try {
        const res = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: document.getElementById('urlInput').value,
            check_status: document.getElementById('checkStatus').checked
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Analysis failed');

        document.getElementById('statScore').textContent = `${data.seo_health_score}/100`;
        document.getElementById('statTotal').textContent = data.summary.total_links;
        document.getElementById('statInternal').textContent = data.summary.internal_links;
        document.getElementById('statExternal').textContent = data.summary.external_links;
        document.getElementById('statNofollow').textContent = data.summary.nofollow_links;
        document.getElementById('pageTitle').textContent = data.page_title || data.final_url;
        document.getElementById('metaInfo').textContent = `HTTP ${data.http_status} • ${data.response_time_ms} ms • ${data.summary.unique_urls} unique URLs`;

        document.getElementById('recList').innerHTML = data.seo_recommendations.map(r => `<li>${r}</li>`).join('');
        currentLinks = data.links;
        renderTable();
        results.classList.remove('hidden');
      } catch (err) {
        errorBox.textContent = err.message;
        errorBox.classList.remove('hidden');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Analyze Links';
      }
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    """Interactive UI Dashboard for testing Link Analysis directly in the browser."""
    return DASHBOARD_HTML


@app.get("/health", tags=["System"])
async def health_check():
    """Service health check endpoint."""
    return {"status": "healthy", "service": "link-analysis-api"}


@app.post("/api/analyze", response_model=LinkAnalysisResponse, tags=["Link Analysis"])
async def analyze_links_post(payload: LinkAnalysisRequest):
    """Analyze all hyperlinks on a target URL (JSON POST body)."""
    try:
        return await analyze_url(str(payload.url), check_status=payload.check_status)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Target URL returned HTTP {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to reach target URL: {str(exc)}",
        )


@app.get("/api/analyze", response_model=LinkAnalysisResponse, tags=["Link Analysis"])
async def analyze_links_get(
    url: str = Query(..., description="Target webpage URL (e.g., https://example.com)"),
    check_status: bool = Query(False, description="Verify HTTP reachability of extracted links"),
):
    """Analyze all hyperlinks on a target URL (Query parameters)."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        return await analyze_url(url, check_status=check_status)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Target URL returned HTTP {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to reach target URL: {str(exc)}",
        )
