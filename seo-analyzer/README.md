# SEO Analyzer - Full-Stack Web Application

A comprehensive SEO analysis platform built with React (frontend), Python FastAPI (backend), and LangGraph (AI-powered analysis orchestration).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                    │
│  Dashboard → Audit Results → History → Reports               │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API + WebSocket (live progress)
┌─────────────────────▼───────────────────────────────────────┐
│                 BACKEND (FastAPI + LangGraph)                 │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ API Routes   │  │ LangGraph    │  │ Analysis Nodes    │  │
│  │ /api/audit   │→ │ Orchestrator │→ │ (parallel exec)   │  │
│  │ /api/history │  │ (workflow)   │  │                    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
│  Nodes:                                                      │
│  ├── technical_analyzer   (robots, redirects, HTTPS)         │
│  ├── content_analyzer     (E-E-A-T, readability, depth)      │
│  ├── schema_analyzer      (JSON-LD, microdata, RDFa)         │
│  ├── performance_analyzer (Core Web Vitals via PSI API)      │
│  ├── onpage_analyzer      (title, meta, headings, links)     │
│  ├── security_analyzer    (headers, HTTPS, mixed content)    │
│  └── scorer               (weighted health score)            │
└─────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              DATABASE (SQLite → PostgreSQL)                   │
│  audit_results, audit_history, drift_baselines               │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React 18 + Vite + TailwindCSS | Fast dev, modern UI |
| Backend | Python 3.11+ + FastAPI | Async, typed, fast |
| AI Orchestration | LangGraph | Parallel node execution, state management |
| Database | SQLite (dev) / PostgreSQL (prod) | Simple start, easy migration |
| HTTP Client | httpx + BeautifulSoup4 | Async fetching + HTML parsing |
| Task Queue | Built into LangGraph | No extra infra needed |

## Getting Started

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Features

- Full SEO audit with 6 parallel analyzers
- Core Web Vitals (LCP, INP, CLS) via PageSpeed Insights
- Technical SEO: robots.txt, sitemaps, canonicals, redirects
- Content quality: E-E-A-T signals, readability, word count
- Schema markup: JSON-LD detection, validation, suggestions
- On-page SEO: titles, meta descriptions, headings, internal links
- Security: HTTPS, security headers, mixed content
- Weighted health score (0-100)
- Audit history with drift comparison
- PDF report generation
