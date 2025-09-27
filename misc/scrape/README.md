# Chess Crawler — RAG-Ready Chess Knowledge Extractor

**Discover → Crawl → Extract → Save.**
This scraper builds a tidy, local **chess knowledge base** ready for Retrieval-Augmented Generation (RAG). It finds high-quality chess pages, loads them in a controlled headless browser (Lightpanda), **extracts structured chess knowledge with OpenAI (strict JSON schema)**, and writes clean Markdown files with YAML front matter plus a searchable `index.json`.

---

## ✨ What you get

```
chess-knowledge-base/
├── openings/       # Complete opening theory (ECO, ideas, traps, model games)
├── middlegame/     # Strategic concepts & examples
├── endgame/        # Endgame themes, positions, techniques
├── tactics/        # Tactical patterns (motifs + example PGNs)
├── games/          # Annotated/model games with metadata + PGN
├── principles/     # General chess wisdom with caveats
└── index.json      # Searchable RAG index across all items
```

Each item is a Markdown file with YAML front matter (tags, source URL, timestamps, metadata like ECO codes), designed to be easily indexed and embedded.

---

## 🧱 Tech Stack

* **Discovery:** Google via **SerpAPI**
* **Crawling/Rendering:** **Puppeteer Core** connected to **Lightpanda** (Chromium over CDP)
* **DOM Cleaning & Conversion:** **JSDOM** → **Turndown** (HTML → Markdown; preserves `pre`/`code`/PGN)
* **Extraction:** **OpenAI** Responses API with **Structured Outputs (JSON Schema, strict)**
* **FS Management:** Node.js + `fs/promises`, `slugify`, `sanitize-filename`

---

## ⚡ Quickstart

1. **Prereqs**

* Node.js **18+** and npm
* Docker (for Lightpanda)
* API keys for **OpenAI** and **SerpAPI**

2. **Start Lightpanda (headless Chromium)**

```bash
docker run -d --name lightpanda -p 9222:9222 lightpanda/browser:nightly
```

3. **Install deps**

```bash
npm i openai puppeteer-core serpapi dotenv jsdom turndown slugify sanitize-filename p-queue
```

4. **Create `.env`**

```bash
# .env
OPENAI_API_KEY=sk-...
SERPAPI_KEY=your_serpapi_key
BROWSER_WS_ENDPOINT=ws://127.0.0.1:9222

# Optional tuning (defaults shown)
MAX_DEPTH=1
MAX_PAGES=5
CONCURRENCY=1
```

5. **Run**

```bash
node chess-crawler.js
```

You’ll see logs for discovery, browser connection, per-page extraction, saved items, and a final stats summary.

---

## 🔧 Configuration

Environment variables:

| Variable              | Purpose                                                                      | Default               |
| --------------------- | ---------------------------------------------------------------------------- | --------------------- |
| `OPENAI_API_KEY`      | Auth for OpenAI Responses API                                                | **required**          |
| `SERPAPI_KEY`         | Auth for Google search (SerpAPI)                                             | **required**          |
| `BROWSER_WS_ENDPOINT` | CDP WS endpoint for Lightpanda/Chromium                                      | `ws://127.0.0.1:9222` |
| `MAX_DEPTH`           | Crawl depth (future-proofing; current run processes seed pages sequentially) | `1`                   |
| `MAX_PAGES`           | Global page budget                                                           | `5`                   |
| `CONCURRENCY`         | Parallel pages (keep **1** for Lightpanda stability)                         | `1`                   |

Runtime constants (tuned for remote browsers):

* `REQUEST_DELAY_MS = 5000` (gentle pacing between pages)
* `PAGE_TIMEOUT_MS = 30000` (navigation timeout)
* `BROWSER_RETRY_DELAY_MS = 3000` (retry spacing)

Content filters:

* `CHESS_KEYWORDS` aggressively narrows scope to chess-relevant URLs.
* `ALLOWED_CONTENT_TYPES = ['text/html']` to avoid binaries.

Host filtering:

* Ignores social networks/trackers
* Positively biases domains like `chess.com`, `lichess.org`, `en.wikipedia.org`, etc.

---

## 🔎 Discovery

The crawler **doesn’t start from a single seed**—it discovers seeds smartly using SerpAPI with targeted queries like:

* `site:chess.com opening theory guide`
* `site:lichess.org opening study`
* `rook endgame technique triangulation opposition`
* `chess tactics patterns list with examples PGN`
* …

Organic results are filtered by `isLikelyChessUrl()`:

* Rejects binaries/media
* Excludes social platforms
* Checks host allow-list and **chess keyword heuristics**

---

## 🌐 Crawling with Lightpanda

We connect Puppeteer Core to a Chromium instance running in Docker (Lightpanda):

```bash
docker run -d --name lightpanda -p 9222:9222 lightpanda/browser:nightly
# .env → BROWSER_WS_ENDPOINT=ws://127.0.0.1:9222
```

Connection flow:

* Validate browser (`browser.version()`)
* Open a **fresh page per URL**
* `page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 })`
* Extract content with **JSDOM**, stripping scripts/ads/nav/footers, promoting `article/main`
* Keep `pre`/`code` blocks intact (PGN/FEN snippets)
* Convert to Markdown via **Turndown**

> Pacing and strict sequential processing (`CONCURRENCY=1`) are deliberate for remote CDP setups.

---

## 🧠 Extraction (OpenAI Structured Outputs)

We pass the page Markdown + metadata to the OpenAI Responses/Chat API with **`response_format: json_schema`** in **strict mode**. The model must return **valid JSON** matching this schema:

Top-level (abridged):

* `source` → `{ url, title, scraped_at }`
* `openings[]` → `{ name, eco, side, overview, main_line, key_variations[], ideas[], traps[], model_games[], tags[] }`
* `middlegame[]` → `{ concept, explanation, examples[], tags[] }`
* `endgame[]` → `{ theme, technique, key_positions[], steps[], tags[] }`
* `tactics[]` → `{ pattern, description, motifs[], example_pgn, tags[] }`
* `games[]` → `{ title, white, black, event, year, result, lesson, pgn, tags[] }`
* `principles[]` → `{ principle, rationale, caveats[], tags[] }`

**Notes**

* Canonical opening names preferred (e.g., “Ruy Lopez”, “Sicilian Defense”).
* Extract PGN/SAN when present.
* If a section doesn’t exist on the page → return an **empty array**.
* Deduplicate by name/title where possible.

---

## 🗂️ Writing Files

For each extracted item:

* Compute a **slug** (`slugify` + `sanitize-filename`, 120 chars)
* Write a Markdown file under its class directory with YAML front matter:

````yaml
---
title: "Ruy Lopez"
type: openings
source_url: "https://example.com/ruy-lopez"
scraped_at: "2025-09-27T12:00:00Z"
tags: ["Spanish Opening", "ECO C60"]
meta:
  eco: "C60"
  side: "White"
  year: null
  event: null
  result: null
---
# Ruy Lopez

## Overview
...

## Main Line
```pgn
1. e4 e5 2. Nf3 Nc6 3. Bb5
````

## Key Variations

* **Berlin Defence**

```pgn
3...Nf6 4. O-O Nxe4 ...
```

````

PGN/code blocks are fenced, ready for downstream tooling.

### `index.json`
- De-duplicated, sorted list of all items with minimal metadata:
```json
{
  "items": [
    {
      "path": "chess-knowledge-base/openings/ruy-lopez.md",
      "title": "Ruy Lopez",
      "class": "openings",
      "source": "https://example.com/ruy-lopez",
      "scraped_at": "2025-09-27T12:00:00Z",
      "tags": ["Spanish Opening", "ECO C60"]
    }
  ]
}
````

---

## 🧭 Current Crawl Strategy

* **Sequential** seed processing (stable for remote browsers)
* **Depth-limited BFS** is scaffolded by config (`MAX_DEPTH`) but **link-following is currently disabled** for stability.
  *Future extension:* collect filtered internal links per page, queue BFS up to `MAX_DEPTH`, respect `MAX_PAGES`.

---

## 🛠️ Tuning & Customization

* **Keywords/Hosts:** edit `CHESS_KEYWORDS` and `isLikelyChessUrl()` to broaden/narrow scope.
* **Discovery Queries:** update `DISCOVERY_QUERIES` for different content focuses (e.g., “opposite-colored bishops endgames”).
* **Rate Limits:** adjust `REQUEST_DELAY_MS`, `MAX_PAGES`, and `CONCURRENCY`—start conservative for reliability.
* **Content Types:** expand `ALLOWED_CONTENT_TYPES` if you later add a PDF pipeline (be sure to implement PDF parsing).
* **Output Schema:** extend the JSON schema and corresponding Markdown rendering blocks to capture more metadata (e.g., FEN images, engine evals).

---

## 🧪 Example Run (What you’ll see)

* SERP discovery per query (`Found X results, added Y chess URLs`)
* Lightpanda connection + validation
* Per-page:

  * Page title
  * Extracted Markdown size
  * OpenAI extraction counts by class
  * Saved items + breakdown
* Final stats: processed pages, items extracted, output directory list

---

## 🧯 Troubleshooting

**Lightpanda won’t connect**

* Ensure container is running and port mapping is correct:

  ```bash
  docker ps
  docker logs lightpanda --tail 200
  ```
* Verify endpoint in `.env`:

  ```
  BROWSER_WS_ENDPOINT=ws://127.0.0.1:9222
  ```
* Try reconnecting:

  ```bash
  docker restart lightpanda
  ```

**Navigation timeouts / Target closed / Session closed**

* Increase `REQUEST_DELAY_MS`
* Keep `CONCURRENCY=1`
* Lower `MAX_PAGES`
* Some sites block headless browsers—discovery will still produce other candidates.

**No items extracted**

* Source might lack extractable chess content or be heavily scripted.
* Check logs for schema compliance errors (rare; strict mode ensures valid JSON or throws).

---

## 🔐 Compliance & Safety

* **Respect robots and site TOS.** This tool is for educational/research use; you are responsible for lawful use.
* **Rate limiting:** Defaults are conservative for remote CDP. Increase carefully.
* **PII:** The extractor ignores personal data; schema is chess-domain specific.
* **Costs:** OpenAI calls incur usage costs; set `MAX_PAGES` judiciously.

---

## 🗺️ Roadmap

* [ ] Enable BFS link-following with on-page filtering (respect `MAX_DEPTH`)
* [ ] Add site-specific extractors for `chess.com`/`lichess.org` studies
* [ ] Parse embedded boards into FEN diagrams
* [ ] Optional local LLM fallback for offline extraction
* [ ] CLI flags and progress UI
* [ ] Dockerize the scraper for one-line runs

---

## 📄 License


---

## 🙌 Acknowledgements

* **Lightpanda** for stable, CDP-exposed Chromium in Docker
* **SerpAPI** for discoverability
* **OpenAI Structured Outputs** for robust schema-first extraction
* **Turndown + JSDOM** for clean HTML→Markdown conversion

---

## 🧭 One-Liner Recap

```bash
# 1) Start headless Chromium over CDP
docker run -d --name lightpanda -p 9222:9222 lightpanda/browser:nightly

# 2) Install deps
npm i openai puppeteer-core serpapi dotenv jsdom turndown slugify sanitize-filename p-queue

# 3) Configure .env (OpenAI, SerpAPI, BROWSER_WS_ENDPOINT)

# 4) Run
node chess-crawler.js
```

