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
const MAX_PAGES = Number(process.env.MAX_PAGES || 20);         // increased for 1-hour runs
const CONCURRENCY = Number(process.env.CONCURRENCY || 1);      // strict sequential for Lightpanda
const REQUEST_DELAY_MS = 10000;                               // 10 seconds between pages for rate limits
const OPENAI_DELAY_MS = 10000;                               // 10 seconds between OpenAI calls for rate limits
const BROWSER_RETRY_DELAY_MS = 1000;                          // delay between connection retries
const PAGE_TIMEOUT_MS = 10000;                                // shorter timeout for faster failure

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

const isBrowserAlive = async (browser) => {
  try {
    await browser.version();
    return true;
  } catch {
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
        protocolTimeout: 10000
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

  // Endgame / technique
  'rook endgame technique triangulation opposition',
  'king and pawn endgame theory classical guide',
  'minor piece endgames bishop vs knight strategy',
  'queen endgames principles and examples PGN',
  'practical endgame strategies chess PDF',
  'endgame theory fundamental positions database',

  
  // Middlegame / strategy
  'chess middlegame strategy explained',
  'middlegame planning in chess examples',
  'positional concepts chess middlegame PDF',
  'pawn structure imbalances in middlegame',
  'maneuvering piece coordination in middlegame',
  'strategic themes in chess middlegame',
  'weak squares outposts and prophylaxis chess',

  // Tactics / patterns
  'chess tactics patterns list with examples PGN',
  'common tactical motifs in chess explained',
  'fork pin skewer discovered attack examples PGN',
  'tactical theme catalog chess',
  'combination puzzles motifs list',

    // Opening / opening theory
  'site:chess.com opening theory guide',
  'site:lichess.org opening study',
  'site:en.wikipedia.org chess openings ECO',
  'chess opening theory advanced survey PDF',
  'common opening traps explained PGN',
  'novel opening ideas chess blog',
  'opening repertoires for club players PDF',
  'transposition in chess opening strategy',



  // Game annotations / lessons / models
  'annotated chess games lessons PGN',
  'model games with commentary PGN',
  'classic chess games annotated analysis',
  'grandmaster game annotations instructive',
  'chess master games commentary PDF',

  // Universal / meta principles
  'universal chess principles rules beginners advanced',
  'chess heuristics strategy rules list',
  'principles vs calculation in chess theory',
  'how to think in chess strategy guide',
  'philosophy of chess strategy and planning',
  
  // Hybrid / databases / references
  'chess opening database with evaluation statistics',
  'chess master theory repository PDF',
  'survey of chess theory research article PDF',
  'chess theory blog site:*.edu OR site:*.ac.jp',
  'openings middlegame endgame unified guide'
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
    await sleep(100);
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
const extractWithOpenAI = async ({ url, title, markdown, scrapedAt, existingContent = [] }) => {
  const isUpdate = existingContent.length > 0;
  console.log(`🧠 ${isUpdate ? 'Updating' : 'Extracting'} chess knowledge from "${title}" (${Math.round(markdown.length / 1024)}KB)`);
  
  if (isUpdate) {
    console.log(`  📚 Found ${existingContent.length} existing files to enhance`);
  }
  
  // We'll use Chat Completions with structured outputs (json_schema, strict).
  // In strict mode, the model must return a JSON object matching the schema.
  const sys = isUpdate ? `
You are an **Intelligent Chess Content Enhancer**. 
You are provided with EXISTING chess content files that were previously extracted, plus NEW page content from the same URL.
Your task is to MERGE, ENHANCE, and IMPROVE the existing content with any new information from the page.

INSTRUCTIONS:
1. Review the existing content files and the new page content
2. Merge information to create more comprehensive and accurate chess knowledge
3. Add any new details, examples, variations, or insights from the new page
4. Correct any errors or incomplete information in existing files
5. Maintain the same high-quality structure and formatting
6. If the new page has significantly different or better content, prioritize it
7. Always output ALL categories (even if empty) to maintain schema compliance

Prefer canonical names (e.g., "Ruy Lopez", "Sicilian Defense").
Extract PGN/SAN lines when present. Preserve and enhance existing PGN/analysis.
Avoid duplicates; dedupe items by name/title when possible.
` : `
You are an **Intelligent Chess Content Recognizer**. 
Classify and extract **only chess knowledge** from the provided page content into the given JSON schema with 100% compliance.
Prefer canonical names (e.g., "Ruy Lopez", "Sicilian Defense").
Extract PGN/SAN lines when present. Summarize lightly while preserving key ideas.
If a section does not exist on the page, return an empty array for it.
Avoid duplicates; dedupe items by name/title when possible.
`;

  let user = `
SOURCE_URL: ${url}
SOURCE_TITLE: ${title || '(no title)'}
SCRAPED_AT: ${scrapedAt}
`;

  if (isUpdate) {
    user += `
EXISTING_CONTENT_FILES:
`;
    for (const existing of existingContent) {
      user += `
--- ${existing.class.toUpperCase()}: ${existing.title} ---
${existing.content}

`;
    }
  }

  user += `
${isUpdate ? 'NEW_' : ''}PAGE_MARKDOWN:
---
${markdown.slice(0, 150000)}  // reduced cap when we have existing content
---
`;

  try {
    // Add delay before OpenAI call to respect rate limits
    console.log(`  ⏳ Waiting ${OPENAI_DELAY_MS / 1000}s before OpenAI call...`);
    await sleep(OPENAI_DELAY_MS);
    
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
    console.log(`  ✨ ${isUpdate ? 'Enhanced' : 'Extracted'}: ${counts}`);
    
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

// ---------- EXISTING CONTENT MANAGEMENT ----------
const findExistingFiles = async (url) => {
  const idxPath = path.join(OUT_DIR, 'index.json');
  try {
    const data = await fsp.readFile(idxPath, 'utf8');
    const index = JSON.parse(data);
    return index.items.filter(item => item.source === url);
  } catch {
    return [];
  }
};

const readExistingContent = async (filePath) => {
  try {
    const content = await fsp.readFile(filePath, 'utf8');
    // Extract the markdown content (everything after the front matter)
    const yamlEndIndex = content.indexOf('---', 3);
    if (yamlEndIndex !== -1) {
      return content.slice(yamlEndIndex + 3).trim();
    }
    return content;
  } catch {
    return null;
  }
};

const getExistingContentForUrl = async (url) => {
  const existingFiles = await findExistingFiles(url);
  const existingContent = [];
  
  for (const file of existingFiles) {
    const content = await readExistingContent(file.path);
    if (content) {
      existingContent.push({
        class: file.class,
        title: file.title,
        content: content,
        path: file.path
      });
    }
  }
  
  return existingContent;
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

  let browser = await createBrowserConnection();

  const visited = new Set();
  let processed = 0;
  let extracted = 0;
  let connectionFailures = 0;

  const processPageWithRecovery = async (pageUrl, depth) => {
    if (processed >= MAX_PAGES) {
      console.log(`🛑 Reached page limit (${MAX_PAGES}), skipping: ${pageUrl}`);
      return;
    }
    if (visited.has(pageUrl)) return;
    visited.add(pageUrl);

    let page;
    let success = false;
    let retries = 0;
    const maxRetries = 2;

    while (!success && retries <= maxRetries) {
      try {
        console.log(`\n🔗 [Depth ${depth}] Processing ${processed + 1}/${MAX_PAGES}: ${pageUrl}`);
        if (retries > 0) {
          console.log(`  🔄 Retry attempt ${retries}/${maxRetries}`);
        }
        
        // Check if browser is still alive, reconnect if needed
        const browserAlive = await isBrowserAlive(browser);
        if (!browserAlive) {
          console.log(`  🔌 Browser connection lost, reconnecting...`);
          try {
            await browser.disconnect().catch(() => {});
          } catch {}
          browser = await createBrowserConnection();
          connectionFailures++;
          console.log(`  ✅ Browser reconnected (failures: ${connectionFailures})`);
        }
        
        // Create page
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

        const title = await page.title();
        console.log(`  📖 Page title: "${title}"`);
        
        console.log(`  🔧 Extracting content...`);
        const html = await extractReadableHtml(page);
        const md = htmlToMarkdown(html);
        const scrapedAt = new Date().toISOString();
        console.log(`  📝 Content extracted: ${Math.round(md.length / 1024)}KB markdown`);

        // Check for existing content for this URL
        console.log(`  🔍 Checking for existing content...`);
        const existingContent = await getExistingContentForUrl(pageUrl);
        
        // Send to OpenAI for structured classification/extraction (or enhancement)
        const bundle = await extractWithOpenAI({ url: pageUrl, title, markdown: md, scrapedAt, existingContent });

        // Write markdown items (this will overwrite existing files if they exist)
        console.log(`  💾 Saving ${existingContent.length > 0 ? 'enhanced' : 'extracted'} items...`);
        const written = [];
        const classes = ['openings', 'middlegame', 'endgame', 'tactics', 'games', 'principles'];
        
        // If updating existing content, remove old files first to avoid duplicates
        if (existingContent.length > 0) {
          console.log(`  🗑️  Removing ${existingContent.length} existing files for update...`);
          for (const existing of existingContent) {
            try {
              await fsp.unlink(existing.path);
              console.log(`    ✅ Removed: ${path.basename(existing.path)}`);
            } catch (e) {
              console.warn(`    ⚠️  Could not remove ${existing.path}: ${e.message}`);
            }
          }
        }
        
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
          const action = existingContent.length > 0 ? 'Enhanced' : 'Saved';
          console.log(`  ✅ ${action} ${written.length} chess items (Total extracted: ${extracted})`);
          console.log(`    📊 Breakdown: ${classes.map(cls => `${cls}: ${(bundle[cls] || []).length}`).filter(s => !s.endsWith(': 0')).join(', ')}`);
        } else {
          console.log(`  ⚪ No chess content found on this page`);
        }

        success = true;
        processed += 1;
        
      } catch (e) {
        console.error(`  ❌ Error processing ${pageUrl}:`, e?.message || e);
        
        const isConnectionError = e.message?.includes('Target closed') || 
                                e.message?.includes('Session closed') || 
                                e.message?.includes('Connection closed') ||
                                e.message?.includes('Protocol error') ||
                                e.message?.includes('WebSocket');
        
        if (isConnectionError) {
          console.log(`  🔄 Browser connection error detected`);
          retries++;
          if (retries <= maxRetries) {
            console.log(`  ⏳ Waiting 5s before retry...`);
            await sleep(5000);
          } else {
            console.log(`  ❌ Max retries reached, skipping this page`);
          }
        } else if (e.message?.includes('Navigation timeout')) {
          console.log(`  ⏰ Page took too long to load - skipping`);
          break;
        } else {
          console.log(`  ❌ Non-recoverable error - skipping`);
          break;
        }
      } finally {
        // Simple cleanup
        if (page) {
          try {
            await page.close();
            console.log(`  🔒 Page closed`);
          } catch (closeError) {
            console.warn(`  ⚠️  Could not close page: ${closeError.message}`);
          }
          page = null;
        }
      }
    }
    
    if (!success) {
      processed += 1; // Still increment to avoid infinite loops
    }
    
    console.log(`  ⏳ Waiting ${REQUEST_DELAY_MS / 1000}s before next page...`);
    await sleep(REQUEST_DELAY_MS);
  };

  // Process pages sequentially like the working script
  const seedsToProcess = seedUrls.slice(0, Math.min(seedUrls.length, MAX_PAGES));
  console.log(`\n🌱 Processing ${seedsToProcess.length} seed URLs sequentially...`);
  console.log(`⏱️  Estimated time: ~${Math.round(seedsToProcess.length * (REQUEST_DELAY_MS + OPENAI_DELAY_MS + PAGE_TIMEOUT_MS) / 60000)} minutes`);
  console.log(`🐌 Rate limits: ${REQUEST_DELAY_MS / 1000}s between pages, ${OPENAI_DELAY_MS / 1000}s before OpenAI calls\n`);
  
  const startTime = Date.now();
  for (let i = 0; i < seedsToProcess.length; i++) {
    const url = seedsToProcess[i];
    console.log(`📈 Progress: ${i + 1}/${seedsToProcess.length} (${Math.round(((i + 1) / seedsToProcess.length) * 100)}%)`);
    if (i > 0) {
      const elapsed = Date.now() - startTime;
      const avgTimePerPage = elapsed / i;
      const remaining = (seedsToProcess.length - i) * avgTimePerPage;
      console.log(`⏱️  Estimated remaining: ${Math.round(remaining / 60000)} minutes`);
    }
    if (connectionFailures > 0) {
      console.log(`🔌 Connection recoveries so far: ${connectionFailures}`);
    }
    await processPageWithRecovery(url, 0);
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
