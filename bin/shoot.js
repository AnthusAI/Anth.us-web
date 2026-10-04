#!/usr/bin/env node
/*
 * shoot.js -- reusable Puppeteer screenshot harness.
 *
 * Captures a full-page PNG plus a small JSON "fingerprint" for every
 * (page x viewport width) combination, so that two runs against two
 * different servers (e.g. old build vs. new build) can be diffed later
 * with bin/compare.py.
 *
 * USAGE
 *   node bin/shoot.js --base http://localhost:8081 \
 *                     --out  /tmp/shots/old \
 *                     --pages pages.json \
 *                     --widths 1440,390
 *
 * pages.json is a JSON array of objects:
 *   [ {"name": "home", "path": "/"},
 *     {"name": "about", "path": "/about/"} ]
 *
 * OUTPUT (per page, per width), written into --out:
 *   <name>@<width>.png    full-page screenshot
 *   <name>@<width>.json   { url, status, classNames, docHeight, title }
 *                         classNames = sorted unique list of every token
 *                         found in every element's class attribute.
 *
 * OPTIONS
 *   --base    <url>     required. Origin that page paths are resolved against.
 *   --out     <dir>     required. Created if missing.
 *   --pages   <file>    required. JSON array of {name, path}.
 *   --widths  <list>    comma separated viewport widths. Default 1440,390.
 *   --height  <px>      viewport height. Default 1000.
 *   --timeout <ms>      navigation timeout. Default 30000.
 *   --font-cap <ms>     cap on waiting for document.fonts.ready. Default 5000.
 *   --scroll-cap <ms>   cap on the lazy-load scroll sweep. Default 15000.
 *   --decode-cap <ms>   cap on waiting for pending images to decode.
 *                       Default 3000. A stalled image's decode() promise
 *                       never settles, so this cap is load-bearing.
 *   --chrome  <path>    explicit Chrome/Chromium executable.
 *                       Also honours $PUPPETEER_EXECUTABLE_PATH.
 *   --puppeteer <path>  explicit puppeteer module directory.
 *                       Also honours $PUPPETEER_MODULE_PATH.
 *   --headful           run with a visible browser window (debugging).
 *   -h, --help          print this help.
 *
 * EXIT CODE
 *   0  every shot succeeded with a 2xx/3xx status
 *   1  at least one page threw or returned a non-2xx/3xx status
 *      (all other pages are still attempted; a summary is printed)
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Module + browser resolution
//
// Puppeteer is intentionally NOT a dependency of this directory; we borrow an
// install from a sibling project by absolute path. Candidates are tried in
// order and the first one that requires cleanly wins.
// ---------------------------------------------------------------------------

const PUPPETEER_CANDIDATES = [
  process.env.PUPPETEER_MODULE_PATH,
  '/Users/home/Projects/Anth.us/node_modules/puppeteer',
  '/Users/home/Projects/Pilobol.us/node_modules/puppeteer',
].filter(Boolean);

// Chrome binaries to fall back on when the puppeteer-managed download is
// absent (`npx puppeteer browsers install chrome` was never run).
const CHROME_CANDIDATES = [
  process.env.PUPPETEER_EXECUTABLE_PATH,
  '/Users/home/Library/Caches/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-mac-arm64/chrome-headless-shell',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);

function loadPuppeteer(explicit) {
  const tried = [];
  const list = explicit ? [explicit, ...PUPPETEER_CANDIDATES] : PUPPETEER_CANDIDATES;
  for (const candidate of list) {
    try {
      const mod = require(candidate);
      return { mod, from: candidate };
    } catch (err) {
      tried.push(`${candidate}  (${err.code || err.message})`);
    }
  }
  throw new Error(
    'Could not require puppeteer from any known location:\n  ' + tried.join('\n  ')
  );
}

async function resolveExecutablePath(puppeteer, explicit) {
  if (explicit) return explicit;

  // Prefer puppeteer's own managed browser when it is actually on disk.
  try {
    let own = puppeteer.executablePath();
    if (own && typeof own.then === 'function') own = await own;
    if (own && fs.existsSync(own)) return own;
  } catch (_) {
    /* puppeteer could not even compute a path; fall through to candidates */
  }

  for (const candidate of CHROME_CANDIDATES) {
    if (fs.existsSync(candidate)) return candidate;
  }
  // Let puppeteer produce its own (informative) error.
  return undefined;
}

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

function printHelp() {
  const src = fs.readFileSync(__filename, 'utf8');
  const block = src.slice(src.indexOf('/*'), src.indexOf('*/') + 2);
  process.stdout.write(
    block.replace(/^\/\*+\n?/, '').replace(/\n? \*\/$/, '').replace(/^ \* ?/gm, '').replace(/^ \*$/gm, '') + '\n'
  );
}

function parseArgs(argv) {
  const opts = {
    base: null,
    out: null,
    pages: null,
    widths: [1440, 390],
    height: 1000,
    timeout: 30000,
    fontCap: 5000,
    scrollCap: 15000,
    decodeCap: 3000,
    chrome: null,
    puppeteer: null,
    headful: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    const next = () => {
      const v = argv[++i];
      if (v === undefined) throw new Error(`Missing value for ${arg}`);
      return v;
    };
    switch (arg) {
      case '--base': opts.base = next().replace(/\/+$/, ''); break;
      case '--out': opts.out = next(); break;
      case '--pages': opts.pages = next(); break;
      case '--widths':
        opts.widths = next()
          .split(',')
          .map((s) => parseInt(s.trim(), 10))
          .filter((n) => Number.isFinite(n) && n > 0);
        break;
      case '--height': opts.height = parseInt(next(), 10); break;
      case '--timeout': opts.timeout = parseInt(next(), 10); break;
      case '--font-cap': opts.fontCap = parseInt(next(), 10); break;
      case '--scroll-cap': opts.scrollCap = parseInt(next(), 10); break;
      case '--decode-cap': opts.decodeCap = parseInt(next(), 10); break;
      case '--chrome': opts.chrome = next(); break;
      case '--puppeteer': opts.puppeteer = next(); break;
      case '--headful': opts.headful = true; break;
      case '-h':
      case '--help': printHelp(); process.exit(0); break;
      default:
        throw new Error(`Unknown argument: ${arg} (try --help)`);
    }
  }

  const missing = ['base', 'out', 'pages'].filter((k) => !opts[k]);
  if (missing.length) {
    throw new Error(`Missing required option(s): ${missing.map((m) => '--' + m).join(', ')} (try --help)`);
  }
  if (!opts.widths.length) throw new Error('--widths produced no usable widths');
  return opts;
}

function loadPages(file) {
  const raw = fs.readFileSync(file, 'utf8');
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new Error(`${file} is not valid JSON: ${err.message}`);
  }
  if (!Array.isArray(parsed)) throw new Error(`${file} must contain a JSON array of {name, path}`);
  parsed.forEach((p, idx) => {
    if (!p || typeof p.name !== 'string' || typeof p.path !== 'string') {
      throw new Error(`${file}[${idx}] must be an object with string "name" and "path"`);
    }
    if (/[/\\]/.test(p.name)) throw new Error(`${file}[${idx}].name must not contain path separators`);
  });
  return parsed;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// ---------------------------------------------------------------------------
// In-page helpers (serialised into the browser)
// ---------------------------------------------------------------------------

/** Resolve once webfonts are ready. Hard-capped and never rejects, so a
 *  font that never loads cannot stall or abort the run. */
async function waitForFonts(page, capMs) {
  try {
    await page.evaluate(async (cap) => {
      if (!document.fonts) return true;
      const timeout = new Promise((resolve) => setTimeout(resolve, cap));
      await Promise.race([document.fonts.ready, timeout]);
      return true;
    }, capMs);
  } catch (_) {
    /* ignore */
  }
}

/** Nudge lazy-loading content into existence: pause, walk to the bottom in
 *  viewport-sized steps, come back to the top, give pending images a chance
 *  to decode, pause again.
 *
 *  Every phase is hard-capped. In particular HTMLImageElement.decode() on an
 *  image whose network request has stalled returns a promise that never
 *  settles -- without the race below a single such image can hang a shot for
 *  minutes.
 */
async function settleLazyContent(page, viewportHeight, caps) {
  await sleep(600);

  try {
    await page.evaluate(
      async (step, cap) => {
        const pause = (ms) => new Promise((r) => setTimeout(r, ms));
        const deadline = Date.now() + cap;
        const maxSteps = 400; // guards against infinitely growing documents
        let y = 0;
        for (let i = 0; i < maxSteps; i++) {
          y += step;
          window.scrollTo(0, y);
          await pause(60);
          if (y >= document.documentElement.scrollHeight) break;
          if (Date.now() > deadline) break;
        }
        window.scrollTo(0, 0);
        await pause(60);
      },
      Math.max(200, Math.floor(viewportHeight * 0.8)),
      caps.scrollMs
    );
  } catch (_) {
    /* ignore */
  }

  try {
    await page.evaluate(async (cap) => {
      const pending = Array.from(document.images).filter((img) => !img.complete && img.decode);
      if (!pending.length) return true;
      const work = Promise.all(pending.map((img) => img.decode().catch(() => null)));
      const timeout = new Promise((resolve) => setTimeout(resolve, cap));
      await Promise.race([work, timeout]);
      return true;
    }, caps.decodeMs);
  } catch (_) {
    /* ignore */
  }

  await sleep(400);
}

/** Collect the structural fingerprint used for the non-pixel half of the diff. */
function collectFingerprint() {
  const tokens = new Set();
  for (const el of document.querySelectorAll('*')) {
    const attr = el.getAttribute && el.getAttribute('class');
    if (!attr || typeof attr !== 'string') continue;
    for (const token of attr.split(/\s+/)) {
      if (token) tokens.add(token);
    }
  }
  return {
    classNames: Array.from(tokens).sort(),
    docHeight: document.documentElement.scrollHeight,
    title: document.title,
  };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const pages = loadPages(opts.pages);
  fs.mkdirSync(opts.out, { recursive: true });

  const { mod: puppeteer, from: puppeteerPath } = loadPuppeteer(opts.puppeteer);
  const executablePath = await resolveExecutablePath(puppeteer, opts.chrome);

  console.log(`puppeteer : ${puppeteerPath}`);
  console.log(`chrome    : ${executablePath || '(puppeteer default)'}`);
  console.log(`base      : ${opts.base}`);
  console.log(`out       : ${opts.out}`);
  console.log(`pages     : ${pages.length}  widths: ${opts.widths.join(', ')}`);
  console.log('');

  const launchOpts = {
    headless: !opts.headful,
    args: ['--no-sandbox', '--font-render-hinting=none', '--hide-scrollbars'],
  };
  if (executablePath) launchOpts.executablePath = executablePath;

  const browser = await puppeteer.launch(launchOpts);
  const results = [];

  try {
    for (const spec of pages) {
      for (const width of opts.widths) {
        const label = `${spec.name}@${width}`;
        const url = `${opts.base}${spec.path}`;
        const started = Date.now();
        let page;
        try {
          page = await browser.newPage();
          await page.setViewport({ width, height: opts.height, deviceScaleFactor: 1 });

          const response = await page.goto(url, { waitUntil: 'networkidle2', timeout: opts.timeout });
          // A null response happens for same-document navigations; treat the
          // status as unknown (0) rather than crashing.
          const status = response ? response.status() : 0;

          await waitForFonts(page, opts.fontCap);
          await settleLazyContent(page, opts.height, {
            scrollMs: opts.scrollCap,
            decodeMs: opts.decodeCap,
          });

          const pngPath = path.join(opts.out, `${label}.png`);
          await page.screenshot({ path: pngPath, fullPage: true });

          const fingerprint = await page.evaluate(collectFingerprint);
          const meta = {
            url,
            status,
            classNames: fingerprint.classNames,
            docHeight: fingerprint.docHeight,
            title: fingerprint.title,
          };
          fs.writeFileSync(path.join(opts.out, `${label}.json`), JSON.stringify(meta, null, 2) + '\n');

          const ok = status >= 200 && status < 400;
          const bytes = fs.statSync(pngPath).size;
          console.log(
            `[${ok ? ' ok ' : 'FAIL'}] ${label.padEnd(28)} status=${String(status).padEnd(4)} ` +
            `h=${String(meta.docHeight).padEnd(6)} classes=${String(meta.classNames.length).padEnd(5)} ` +
            `${(bytes / 1024).toFixed(0)}KB  ${Date.now() - started}ms`
          );
          results.push({ label, url, status, ok, docHeight: meta.docHeight, error: ok ? null : `HTTP ${status}` });
        } catch (err) {
          console.log(`[FAIL] ${label.padEnd(28)} ${err.message.split('\n')[0]}`);
          results.push({ label, url, status: null, ok: false, docHeight: null, error: err.message.split('\n')[0] });
        } finally {
          if (page) {
            try { await page.close(); } catch (_) { /* ignore */ }
          }
        }
      }
    }
  } finally {
    try { await browser.close(); } catch (_) { /* ignore */ }
  }

  const failures = results.filter((r) => !r.ok);
  console.log('');
  console.log('='.repeat(72));
  console.log(`SUMMARY: ${results.length - failures.length}/${results.length} shots ok  ->  ${opts.out}`);
  if (failures.length) {
    console.log(`${failures.length} failure(s):`);
    for (const f of failures) console.log(`  - ${f.label}  ${f.url}  ${f.error}`);
  }
  console.log('='.repeat(72));

  process.exitCode = failures.length ? 1 : 0;
}

main().catch((err) => {
  console.error('fatal: ' + (err && err.stack ? err.stack : err));
  process.exit(1);
});
