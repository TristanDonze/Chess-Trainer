// chess-crawler.js
// Purpose: Discover, crawl, and intelligently extract chess knowledge into a tidy RAG-ready repo.
//
// Folders created:
// chess-knowledge-base/
// ├── openings/       # Complete opening theory
// ├── middlegame/     # Strategic concepts
// ├── endgame/        # Endgame theory
// ├── tactics/        # Tactical patterns
// ├── games/          # Annotated games
// ├── principles/     # General wisdom
// └── index.json      # Searchable index
//
// Requirements:
//   npm i openai puppeteer-core serpapi dotenv jsdom turndown slugify sanitize-filename p-queue
//
// Notes & references:
// - OpenAI Structured Outputs with JSON Schema (strict): the model must return valid JSON.
// - We connect Puppeteer to Lightpanda over CDP (browserWSEndpoint).
// - SERPAPI is used for discovery so the crawler starts smartly instead of a single seed URL.
// - Depth-limited BFS crawl with link filters specific to chess.
// - Each extracted item becomes a Markdown file with YAML front matter.
// - index.json aggregates metadata across all items for RAG indexing.
//
// Sources consulted:
// - OpenAI structured outputs & Responses/Chat APIs (response_format: json_schema, strict)
// - Lightpanda usage to connect Puppeteer via browserWSEndpoint
// - SerpAPI Node quickstart

import 'dotenv/config';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import url from 'url';
import puppeteer from 'puppeteer-core';
import { getJson } from 'serpapi';
import OpenAI from 'openai';
import TurndownService from 'turndown';
import { JSDOM } from 'jsdom';
import slugify from 'slugify';
import sanitize from 'sanitize-filename';

// ---------- CONFIG ----------
const OUT_DIR = path.resolve('chess-knowledge-base');
const BROWSER_WS_ENDPOINT = process.env.BROWSER_WS_ENDPOINT || 'ws://127.0.0.1:9222';
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const SERPAPI_KEY = process.env.SERPAPI_KEY;

const MAX_DEPTH = Number(process.env.MAX_DEPTH || 1);          // crawl depth (reduced for Lightpanda)
const MAX_PAGES = Number(process.env.MAX_PAGES || 5);          // global page budget (very reduced for stability)
const CONCURRENCY = Number(process.env.CONCURRENCY || 1);      // strict sequential for Lightpanda
const REQUEST_DELAY_MS = 5000;                                 // much longer delay for Lightpanda
const BROWSER_RETRY_DELAY_MS = 3000;                          // delay between connection retries
const PAGE_TIMEOUT_MS = 30000;                                // shorter timeout for faster failure

// Strong chess-keyword filters to reduce noise
const CHESS_KEYWORDS = [
  'chess', 'opening', 'middlegame', 'endgame', 'tactics', 'strategy',
  'annotated game', 'pgn', 'eco code', 'sicilian', 'ruy lopez', 'caro-kann',
  'french defense', 'nimzo', 'grunfeld', 'kings indian', 'queens gambit',
  'london system', 'benoni', 'slav', 'scotch', 'italian game', 'scandinavian',
  'zugzwang', 'opposition', 'triangulation', 'pawn endgame', 'rook endgame',
  'fork', 'pin', 'skewer', 'discovered attack', 'zwischenzug', 'sacrifice'
];

const ALLOWED_CONTENT_TYPES = ['text/html'];

// Where we save content by class
const CLASS_TO_DIR = {
  openings: 'openings',
  middlegame: 'middlegame',
  endgame: 'endgame',
  tactics: 'tactics',
  games: 'games',
  principles: 'principles'
};

// ---------- OPENAI CLIENT ----------
if (!OPENAI_API_KEY) {
  console.error('Missing OPENAI_API_KEY');
  process.exit(1);
}
const openai = new OpenAI({ apiKey: OPENAI_API_KEY });

// ---------- UTIL ----------
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Browser connection utilities for Lightpanda
const validateBrowserConnection = async (browser) => {
  try {
    const version = await browser.version();
    console.log('🔍 Browser version:', version);
    return true;
  } catch (error) {
    console.warn('⚠️  Browser validation failed:', error.message);
    return false;
  }
};

const validateContextConnection = async (context) => {
  try {
    const pages = await context.pages();
    console.log('🔍 Context validation successful, pages:', pages.length);
    return true;
  } catch (error) {
    console.warn('⚠️  Context validation failed:', error.message);
    return false;
  }
};

const createBrowserConnection = async (maxRetries = 3) => {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`🌐 Connecting to Lightpanda (attempt ${attempt}/${maxRetries})...`);
      const browser = await puppeteer.connect({ 
        browserWSEndpoint: BROWSER_WS_ENDPOINT,
        defaultViewport: { width: 1440, height: 900 },
        ignoreHTTPSErrors: true,
        protocolTimeout: 30000
      });
      
      const isValid = await validateBrowserConnection(browser);
      if (isValid) {
        console.log('✅ Lightpanda browser connected successfully');
        return browser;
      } else {
        await browser.disconnect().catch(() => {});
        throw new Error('Browser validation failed');
      }
    } catch (error) {
      console.error(`❌ Connection attempt ${attempt} failed:`, error.message);
      if (attempt === maxRetries) {
        console.error('💥 All connection attempts failed. Please ensure Lightpanda Docker is running.');
        console.log('💡 Start Lightpanda with: docker run -p 9222:3000 lightpanda/lightpanda');
        throw error;
      }
      console.log(`⏳ Waiting ${BROWSER_RETRY_DELAY_MS}ms before retry...`);
      await sleep(BROWSER_RETRY_DELAY_MS);
    }
  }
};

const ensureDirs = async () => {
  await fsp.mkdir(OUT_DIR, { recursive: true });
  for (const dir of Object.values(CLASS_TO_DIR)) {
    await fsp.mkdir(path.join(OUT_DIR, dir), { recursive: true });
  }
};

const makeSlug = (s, fallback = 'untitled') => {
  const cleaned = (s || '').toString().trim() || fallback;
  return sanitize(
    slugify(cleaned, { lower: true, strict: true }).slice(0, 120) || fallback
  );
};

const isLikelyChessUrl = (href) => {
  if (!href) return false;
  try {
    const u = new URL(href);
    // Quick filters: ignore binaries and trackers
    if (/\.(pdf|jpg|jpeg|png|gif|webp|svg|mp4|zip|rar|7z|exe|dmg|gz|tgz)$/i.test(u.pathname)) return false;
    const badHosts = ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'tiktok.com', 'reddit.com', 'pinterest.com'];
    if (badHosts.some(h => u.hostname.endsWith(h))) return false;

    // Positive host hints
    const goodHosts = [
      'chess.com', 'lichess.org', 'chesstempo.com', 'chessable.com',
      'chesspathways.com', 'thechessworld.com', 'chessable', 'chesstactics.org',
      'en.wikipedia.org', 'chessgames.com', 'chessopenings.net', 'newinchess',
      'chessable', 'ultrachess', 'chessable.blog'
    ];
    if (goodHosts.some(h => u.hostname.includes(h))) return true;

    // Keyword heuristic
    return CHESS_KEYWORDS.some(k => (u.href + ' ' + u.pathname).toLowerCase().includes(k));
  } catch {
    return false;
  }
};

// Pull visible-ish text, PGN/code, headings, lists
const extractReadableHtml = async (page) => {
  const html = await page.content();
  const dom = new JSDOM(html);
  const { document } = dom.window;

  // Remove scripts/styles/nav/ads
  document.querySelectorAll('script, style, noscript, iframe, header, footer, nav, aside, [role="banner"], [role="navigation"]').forEach(el => el.remove());

  // Promote article/main if present
  const root =
    document.querySelector('article') ||
    document.querySelector('main') ||
    document.body;

  // Keep code/PGN/pre tags because they may hold PGN/FEN or lines
  // Convert to Markdown later with Turndown
  return root.outerHTML;
};

const htmlToMarkdown = (html) => {
  const td = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced' });
  // Preserve code blocks
  td.addRule('pre-code', {
    filter: (node) => node.nodeName === 'PRE' || node.nodeName === 'CODE',
    replacement: (content, node) => {
      const text = node.textContent || '';
      return `\n\`\`\`\n${text.trim()}\n\`\`\`\n`;
    }
  });
  return td.turndown(html);
};

// ---------- SERP DISCOVERY ----------
if (!SERPAPI_KEY) {
  console.error('Missing SERPAPI_KEY');
  process.exit(1);
}

const DISCOVERY_QUERIES = [
  'site:chess.com opening theory guide',
  'site:lichess.org opening study',
  'site:en.wikipedia.org chess openings ECO',
  'chess middlegame strategy explained',
  'rook endgame technique triangulation opposition',
  'chess tactics patterns list with examples PGN',
  'annotated chess games lessons PGN',
  'universal chess principles rules beginners advanced'
];

const serpDiscover = async (limitPerQuery = 8) => {
  console.log('🔍 Starting SERP discovery with', DISCOVERY_QUERIES.length, 'queries...');
  const urls = new Set();
  for (let i = 0; i < DISCOVERY_QUERIES.length; i++) {
    const q = DISCOVERY_QUERIES[i];
    console.log(`📊 Query ${i + 1}/${DISCOVERY_QUERIES.length}: "${q}"`);
    try {
      const res = await getJson({
        engine: 'google',
        q,
        api_key: SERPAPI_KEY,
        num: limitPerQuery,
        hl: 'en'
      });
      const organic = (res.organic_results || []).map(r => r.link).filter(Boolean);
      let added = 0;
      for (const link of organic) {
        if (isLikelyChessUrl(link) && !urls.has(link)) {
          urls.add(link);
          added++;
        }
      }
      console.log(`  ✅ Found ${organic.length} results, added ${added} chess URLs (total: ${urls.size})`);
    } catch (e) {
      console.warn(`  ❌ SERPAPI error on query "${q}":`, e?.message || e);
    }
    await sleep(200);
  }
  console.log(`🎯 Discovery complete: ${urls.size} unique chess URLs found`);
  return Array.from(urls);
};

// ---------- OPENAI SCHEMA ----------
const extractionSchema = {
  name: 'ChessKnowledgeBundle',
  strict: true,
  schema: {
    type: 'object',
    additionalProperties: false,
    properties: {
      source: {
        type: 'object',
        additionalProperties: false,
        properties: {
          url: { type: 'string' },
          title: { type: 'string' },
          scraped_at: { type: 'string' }
        },
        required: ['url', 'title', 'scraped_at']
      },
      // Each array may contain multiple items the model identifies on the page
      openings: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            name: { type: 'string' },
            eco: { type: 'string', nullable: true },
            side: { type: 'string', enum: ['White', 'Black', 'Both'], nullable: true },
            overview: { type: 'string', nullable: true },
            main_line: { type: 'string', nullable: true },        // SAN moves or PGN snippet
            key_variations: {
              type: 'array',
              items: {
                type: 'object',
                additionalProperties: false,
                properties: {
                  name: { type: 'string', nullable: true },
                  line: { type: 'string', nullable: true }        // SAN/PGN
                },
                required: ['name', 'line']
              }
            },
            ideas: { type: 'array', items: { type: 'string' } },
            traps: { type: 'array', items: { type: 'string' } },
            model_games: {
              type: 'array',
              items: {
                type: 'object',
                additionalProperties: false,
                properties: {
                  event: { type: 'string', nullable: true },
                  white: { type: 'string', nullable: true },
                  black: { type: 'string', nullable: true },
                  year: { type: 'string', nullable: true },
                  result: { type: 'string', nullable: true },
                  pgn: { type: 'string', nullable: true }
                },
                required: ['event', 'white', 'black', 'year', 'result', 'pgn']
              }
            },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['name', 'eco', 'side', 'overview', 'main_line', 'key_variations', 'ideas', 'traps', 'model_games', 'tags']
        }
      },
      middlegame: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            concept: { type: 'string' },
            explanation: { type: 'string', nullable: true },
            examples: { type: 'array', items: { type: 'string' } },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['concept', 'explanation', 'examples', 'tags']
        }
      },
      endgame: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            theme: { type: 'string' },
            technique: { type: 'string', nullable: true },
            key_positions: { type: 'array', items: { type: 'string' } }, // FEN/description
            steps: { type: 'array', items: { type: 'string' } },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['theme', 'technique', 'key_positions', 'steps', 'tags']
        }
      },
      tactics: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            pattern: { type: 'string' },
            description: { type: 'string', nullable: true },
            motifs: { type: 'array', items: { type: 'string' } },
            example_pgn: { type: 'string', nullable: true },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['pattern', 'description', 'motifs', 'example_pgn', 'tags']
        }
      },
      games: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            title: { type: 'string', nullable: true },
            white: { type: 'string', nullable: true },
            black: { type: 'string', nullable: true },
            event: { type: 'string', nullable: true },
            year: { type: 'string', nullable: true },
            result: { type: 'string', nullable: true },
            lesson: { type: 'string', nullable: true },
            pgn: { type: 'string', nullable: true },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['title', 'white', 'black', 'event', 'year', 'result', 'lesson', 'pgn', 'tags']
        }
      },
      principles: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            principle: { type: 'string' },
            rationale: { type: 'string', nullable: true },
            caveats: { type: 'array', items: { type: 'string' } },
            tags: { type: 'array', items: { type: 'string' } }
          },
          required: ['principle', 'rationale', 'caveats', 'tags']
        }
      }
    },
    required: ['source', 'openings', 'middlegame', 'endgame', 'tactics', 'games', 'principles']
  }
};

// ---------- OPENAI EXTRACTOR ----------
const extractWithOpenAI = async ({ url, title, markdown, scrapedAt }) => {
  console.log(`🧠 Extracting chess knowledge from "${title}" (${Math.round(markdown.length / 1024)}KB)`);
  // We'll use Chat Completions with structured outputs (json_schema, strict).
  // In strict mode, the model must return a JSON object matching the schema.
  const sys = `
You are an **Intelligent Chess Content Recognizer**. 
Classify and extract **only chess knowledge** from the provided page content into the given JSON schema with 100% compliance.
Prefer canonical names (e.g., "Ruy Lopez", "Sicilian Defense").
Extract PGN/SAN lines when present. Summarize lightly while preserving key ideas.
If a section does not exist on the page, return an empty array for it.
Avoid duplicates; dedupe items by name/title when possible.
`;
  const user = `
SOURCE_URL: ${url}
SOURCE_TITLE: ${title || '(no title)'}
SCRAPED_AT: ${scrapedAt}

PAGE_MARKDOWN:
---
${markdown.slice(0, 200000)}  // safety cap to keep tokens in check
---
`;

  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-2024-08-06',
      messages: [
        { role: 'system', content: sys },
        { role: 'user', content: user }
      ],
      temperature: 0.2,
      response_format: {
        type: 'json_schema',
        json_schema: extractionSchema
      }
    });

    const raw = completion.choices?.[0]?.message?.content;
    if (!raw) throw new Error('No content from OpenAI.');
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (e) {
      // If the SDK returns parsed content in future versions, try to read it.
      if (completion.choices?.[0]?.message?.parsed) {
        parsed = completion.choices[0].message.parsed;
      } else {
        throw new Error('Failed to parse JSON from model.');
      }
    }
    
    // Log extraction results
    const counts = Object.entries(parsed)
      .filter(([key]) => key !== 'source')
      .map(([key, arr]) => `${key}: ${Array.isArray(arr) ? arr.length : 0}`)
      .join(', ');
    console.log(`  ✨ Extracted: ${counts}`);
    
    return parsed;
  } catch (error) {
    console.error(`  ❌ OpenAI extraction failed: ${error.message}`);
    throw error;
  }
};

// ---------- WRITE FILES ----------
const writeMarkdownItem = async (cls, item, source) => {
  const dir = CLASS_TO_DIR[cls];
  if (!dir) return null;

  const title =
    item.name ||
    item.concept ||
    item.theme ||
    item.pattern ||
    item.title ||
    item.principle ||
    'untitled';

  const slug = makeSlug(title);
  const dest = path.join(OUT_DIR, dir, `${slug}.md`);

  const frontMatter = {
    title,
    type: cls,
    source_url: source.url,
    scraped_at: source.scraped_at,
    tags: item.tags || [],
    meta: {
      eco: item.eco || null,
      side: item.side || null,
      year: item.year || null,
      event: item.event || null,
      result: item.result || null
    }
  };

  // Build body per class
  const lines = [];
  if (cls === 'openings') {
    if (item.overview) lines.push(`## Overview\n\n${item.overview}`);
    if (item.main_line) lines.push(`## Main Line\n\n\`\`\`pgn\n${item.main_line}\n\`\`\``);
    if (item.key_variations?.length) {
      lines.push(`## Key Variations`);
      for (const v of item.key_variations) {
        const nm = v.name ? `**${v.name}**` : '';
        const ln = v.line ? `\n\n\`\`\`pgn\n${v.line}\n\`\`\`` : '';
        lines.push(`- ${nm}${ln}`);
      }
    }
    if (item.ideas?.length) lines.push(`## Ideas\n\n${item.ideas.map(s => `- ${s}`).join('\n')}`);
    if (item.traps?.length) lines.push(`## Traps\n\n${item.traps.map(s => `- ${s}`).join('\n')}`);
    if (item.model_games?.length) {
      lines.push(`## Model Games`);
      for (const g of item.model_games) {
        const head = [g.white, g.black].filter(Boolean).join(' vs ');
        const meta = [g.event, g.year, g.result].filter(Boolean).join(' • ');
        const h = [head, meta].filter(Boolean).join(' — ');
        lines.push(`- ${h}`);
        if (g.pgn) lines.push(`\n\`\`\`pgn\n${g.pgn}\n\`\`\``);
      }
    }
  } else if (cls === 'middlegame') {
    if (item.explanation) lines.push(`## Explanation\n\n${item.explanation}`);
    if (item.examples?.length) lines.push(`## Examples\n\n${item.examples.map(s => `- ${s}`).join('\n')}`);
  } else if (cls === 'endgame') {
    if (item.technique) lines.push(`## Technique\n\n${item.technique}`);
    if (item.key_positions?.length) lines.push(`## Key Positions\n\n${item.key_positions.map(s => `- ${s}`).join('\n')}`);
    if (item.steps?.length) lines.push(`## Steps\n\n${item.steps.map(s => `1. ${s}`).join('\n')}`);
  } else if (cls === 'tactics') {
    if (item.description) lines.push(`## Description\n\n${item.description}`);
    if (item.motifs?.length) lines.push(`## Motifs\n\n${item.motifs.map(s => `- ${s}`).join('\n')}`);
    if (item.example_pgn) lines.push(`## Example PGN\n\n\`\`\`pgn\n${item.example_pgn}\n\`\`\``);
  } else if (cls === 'games') {
    const metaParts = [item.white && `White: ${item.white}`, item.black && `Black: ${item.black}`, item.result && `Result: ${item.result}`, item.event && `Event: ${item.event}`, item.year && `Year: ${item.year}`].filter(Boolean);
    if (metaParts.length) lines.push(`## Metadata\n\n${metaParts.map(s => `- ${s}`).join('\n')}`);
    if (item.lesson) lines.push(`## Lesson\n\n${item.lesson}`);
    if (item.pgn) lines.push(`## PGN\n\n\`\`\`pgn\n${item.pgn}\n\`\`\``);
  } else if (cls === 'principles') {
    if (item.rationale) lines.push(`## Rationale\n\n${item.rationale}`);
    if (item.caveats?.length) lines.push(`## Caveats\n\n${item.caveats.map(s => `- ${s}`).join('\n')}`);
  }

  const yaml = [
    '---',
    ...Object.entries(frontMatter).map(([k, v]) => {
      if (Array.isArray(v)) return `${k}: [${v.map(x => `"${String(x).replace(/"/g, '\\"')}"`).join(', ')}]`;
      if (v && typeof v === 'object') {
        return `${k}:\n${Object.entries(v).map(([kk, vv]) => `  ${kk}: ${vv === null ? 'null' : `"${String(vv).replace(/"/g, '\\"')}"`}`).join('\n')}`;
      }
      return `${k}: ${v === null ? 'null' : `"${String(v).replace(/"/g, '\\"')}"`}`;
    }),
    '---',
    '',
    `# ${title}`,
    '',
    ...lines
  ].join('\n');

  await fsp.writeFile(dest, yaml, 'utf8');
  return { path: dest, title, class: cls, source: source.url, scraped_at: source.scraped_at, tags: frontMatter.tags || [] };
};

const updateIndex = async (entries) => {
  const idxPath = path.join(OUT_DIR, 'index.json');
  let existing = { items: [] };
  try {
    const data = await fsp.readFile(idxPath, 'utf8');
    existing = JSON.parse(data);
  } catch {}
  const mapKey = (e) => `${e.class}:${e.title}:${e.source}`;
  const dedup = new Map(existing.items.map(i => [mapKey(i), i]));
  for (const e of entries) {
    dedup.set(mapKey(e), e);
  }
  const merged = { items: Array.from(dedup.values()).sort((a, b) => a.title.localeCompare(b.title)) };
  await fsp.writeFile(idxPath, JSON.stringify(merged, null, 2), 'utf8');
};

// ---------- CRAWLER ----------
const crawl = async () => {
  console.log('🚀 Starting chess knowledge crawler...');
  await ensureDirs();
  console.log('📁 Output directories created');

  const seedUrls = await serpDiscover(8);
  console.log(`🌱 Discovered ${seedUrls.length} seed URLs from SERP.`);

  const browser = await createBrowserConnection();

  const visited = new Set();
  let processed = 0;
  let extracted = 0;

  const processPage = async (pageUrl, depth) => {
    if (processed >= MAX_PAGES) {
      console.log(`🛑 Reached page limit (${MAX_PAGES}), skipping: ${pageUrl}`);
      return;
    }
    if (visited.has(pageUrl)) return;
    visited.add(pageUrl);

    let page;
    try {
      console.log(`\n🔗 [Depth ${depth}] Processing ${processed + 1}/${MAX_PAGES}: ${pageUrl}`);
      
      // Create page directly like the working script
      console.log(`  📄 Creating new page...`);
      page = await browser.newPage();
      
      await page.setViewport({ width: 1920, height: 1080 });
      console.log(`  ✅ Page created successfully`);
        
      console.log(`  📄 Loading page with Lightpanda...`);
      
      // Use the working navigation pattern
      await page.goto(pageUrl, { 
        waitUntil: 'networkidle0',
        timeout: PAGE_TIMEOUT_MS
      });
      console.log(`  ✅ Page loaded successfully`);

        // Skip network API calls for Lightpanda compatibility

        const title = await page.title();
        console.log(`  📖 Page title: "${title}"`);
        
        console.log(`  🔧 Extracting content...`);
        const html = await extractReadableHtml(page);
        const md = htmlToMarkdown(html);
        const scrapedAt = new Date().toISOString();
        console.log(`  📝 Content extracted: ${Math.round(md.length / 1024)}KB markdown`);

        // Send to OpenAI for structured classification/extraction
        const bundle = await extractWithOpenAI({ url: pageUrl, title, markdown: md, scrapedAt });

        // Write markdown items
        console.log(`  💾 Saving extracted items...`);
        const written = [];
        const classes = ['openings', 'middlegame', 'endgame', 'tactics', 'games', 'principles'];
        for (const cls of classes) {
          const arr = bundle[cls] || [];
          for (const item of arr) {
            const info = await writeMarkdownItem(cls, item, bundle.source);
            if (info) written.push(info);
          }
        }
        if (written.length) {
          await updateIndex(written);
          extracted += written.length;
          console.log(`  ✅ Saved ${written.length} chess items (Total extracted: ${extracted})`);
          console.log(`    📊 Breakdown: ${classes.map(cls => `${cls}: ${(bundle[cls] || []).length}`).filter(s => !s.endsWith(': 0')).join(', ')}`);
        } else {
          console.log(`  ⚪ No chess content found on this page`);
        }

        processed += 1;

      // For now, we'll process one page at a time without following links
      // to ensure stable operation with Lightpanda
      
    } catch (e) {
      console.error(`  ❌ Error processing ${pageUrl}:`, e?.message || e);
      if (e.message?.includes('Target closed') || e.message?.includes('Session closed') || e.message?.includes('Connection closed')) {
        console.log(`  🔄 Browser connection lost - this page will be skipped`);
      } else if (e.message?.includes('Navigation timeout')) {
        console.log(`  ⏰ Page took too long to load - skipping`);
      }
    } finally {
      // Simple cleanup like the working script
      if (page) {
        try {
          await page.close();
          console.log(`  🔒 Page closed`);
        } catch (closeError) {
          console.warn(`  ⚠️  Could not close page: ${closeError.message}`);
        }
      }
      console.log(`  ⏳ Waiting ${REQUEST_DELAY_MS}ms before next page...`);
      await sleep(REQUEST_DELAY_MS);
    }
    
    processed += 1;
  };

  // Process pages sequentially like the working script
  const seedsToProcess = seedUrls.slice(0, Math.min(seedUrls.length, MAX_PAGES));
  console.log(`\n🌱 Processing ${seedsToProcess.length} seed URLs sequentially...`);
  
  for (const url of seedsToProcess) {
    await processPage(url, 0);
  }
  
  try {
    await browser.disconnect();
    console.log('🔌 Browser disconnected');
  } catch (e) {
    console.warn('⚠️  Browser cleanup error (this is usually fine):', e.message);
  }
  
  console.log(`\n🎉 Crawling complete!`);
  console.log(`📊 Final stats:`);
  console.log(`  - Pages processed: ${processed}`);
  console.log(`  - Chess items extracted: ${extracted}`);
  console.log(`  - Output directory: ${OUT_DIR}`);
  console.log(`\n📁 Check the following folders for extracted content:`);
  console.log(`  ${Object.values(CLASS_TO_DIR).map(d => `- ${path.join(OUT_DIR, d)}`).join('\n  ')}`);
};

// ---------- RUN ----------
crawl().catch((e) => {
  console.error('Fatal:', e);
  process.exit(1);
});
