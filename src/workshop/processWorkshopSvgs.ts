/**
 * Download hotspot illustration SVGs from workshop HTML pages,
 * apply CSS patches, save locally, and rewrite HTML to use <object> tags.
 *
 * Port of process_workshop_svgs.py — uses curl for downloads
 * to avoid Akamai TLS fingerprinting blocks.
 */

import { readFile, writeFile, readdir } from "fs/promises";
import { existsSync } from "fs";
import { join, relative, dirname } from "path";
import { execFile } from "child_process";
import { promisify } from "util";
/** Decode common HTML entities without external dependencies. */
function decodeHtmlEntities(str: string): string {
  return str
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) =>
      String.fromCharCode(parseInt(hex, 16))
    )
    .replace(/&#(\d+);/g, (_, dec) => String.fromCharCode(parseInt(dec, 10)))
    .replace(/&amp;/g, "&");
}

const execFileAsync = promisify(execFile);

interface SvgRef {
  fullMatch: string;
  rawUrl: string;
}

interface Stats {
  downloaded: number;
  skipped: number;
  errors: number;
  refsRewritten: number;
  filesModified: number;
}

const SVG_REF_PATTERN =
  /<div\s[^>]*?data-type="hotspotillus"[^>]*?data-svg-path="([^"]+)"[^>]*?>(?:<\/div>)?/gi;

const IMAGE_ID_PATTERN = /[?&]id=([^&]+)/;

function extractSvgRefs(htmlContent: string): SvgRef[] {
  const results: SvgRef[] = [];
  let match: RegExpExecArray | null;
  // Reset lastIndex since we reuse the global regex
  SVG_REF_PATTERN.lastIndex = 0;
  while ((match = SVG_REF_PATTERN.exec(htmlContent)) !== null) {
    results.push({
      fullMatch: match[0],
      rawUrl: match[1],
    });
  }
  return results;
}

function extractImageId(url: string): string | null {
  const m = url.match(IMAGE_ID_PATTERN);
  return m ? m[1] : null;
}

function patchSvgCss(svgContent: string): string {
  return svgContent
    .replace(
      /\.sttxt\s*\{[^}]*\}/gi,
      ".sttxt { visibility: visible; }"
    )
    .replace(
      /\.stcallout\s*\{[^}]*\}/gi,
      ".stcallout { visibility: hidden; }"
    );
}

async function downloadSvg(url: string, dest: string): Promise<boolean> {
  try {
    const { stdout, stderr } = await execFileAsync("curl", [
      "-s",
      "-f",
      "--max-time",
      "30",
      url,
    ]);
    const patched = patchSvgCss(stdout);
    await writeFile(dest, patched, "utf-8");
    return true;
  } catch (e: any) {
    console.error(`    ERROR downloading ${url}: ${e.message || e}`);
    return false;
  }
}

async function processFile(
  htmlPath: string,
  downloadedCache: Map<string, string>,
  stats: Stats
): Promise<void> {
  const content = await readFile(htmlPath, "utf-8");
  const refs = extractSvgRefs(content);
  if (refs.length === 0) return;

  const fileDir = dirname(htmlPath);
  let updated = content;

  for (const ref of refs) {
    const url = decodeHtmlEntities(ref.rawUrl);
    const imageId = extractImageId(url);
    if (!imageId) {
      console.log(`    WARN: Could not extract ID from: ${url}`);
      stats.errors++;
      continue;
    }

    const svgFilename = `${imageId}.svg`;
    const svgPath = join(fileDir, svgFilename);

    if (!downloadedCache.has(imageId)) {
      if (existsSync(svgPath)) {
        console.log(`    Already exists: ${svgFilename}`);
        stats.skipped++;
      } else {
        if (await downloadSvg(url, svgPath)) {
          console.log(`    Downloaded: ${svgFilename}`);
          stats.downloaded++;
          // be gentle
          await new Promise((r) => setTimeout(r, 100));
        } else {
          stats.errors++;
          continue;
        }
      }
      downloadedCache.set(imageId, svgPath);
    }

    const objectTag =
      `<object data="${svgFilename}" type="image/svg+xml" ` +
      `class="workshop-svg" style="width:100%; max-width:100%;"></object>`;
    updated = updated.replace(ref.fullMatch, objectTag);
    stats.refsRewritten++;
  }

  if (updated !== content) {
    await writeFile(htmlPath, updated, "utf-8");
    stats.filesModified++;
  }
}

/** Recursively find all .html files under dir (excluding index.html). */
async function findHtmlFiles(dir: string): Promise<string[]> {
  const results: string[] = [];

  async function walk(d: string) {
    const entries = await readdir(d, { withFileTypes: true });
    for (const entry of entries) {
      const full = join(d, entry.name);
      if (entry.isDirectory()) {
        await walk(full);
      } else if (
        entry.isFile() &&
        entry.name.endsWith(".html") &&
        entry.name !== "index.html"
      ) {
        results.push(full);
      }
    }
  }

  await walk(dir);
  return results.sort();
}

/**
 * Process all workshop HTML files in manualDir, downloading SVGs
 * and rewriting HTML references.
 *
 * Called automatically at the end of saveEntireManual, or standalone.
 */
export default async function processWorkshopSvgs(
  manualDir: string
): Promise<void> {
  console.log(`\n=== Processing workshop SVGs ===`);
  console.log(`Manual directory: ${manualDir}`);

  // Scan for HTML files containing hotspotillus references
  const allHtml = await findHtmlFiles(manualDir);
  const htmlFiles: string[] = [];
  for (const f of allHtml) {
    const content = await readFile(f, "utf-8");
    if (content.includes('data-type="hotspotillus"')) {
      htmlFiles.push(f);
    }
  }

  console.log(`Found ${htmlFiles.length} HTML files with hotspot SVGs.\n`);
  if (htmlFiles.length === 0) {
    console.log("Nothing to do.");
    return;
  }

  const stats: Stats = {
    downloaded: 0,
    skipped: 0,
    errors: 0,
    refsRewritten: 0,
    filesModified: 0,
  };
  const downloadedCache = new Map<string, string>();

  for (let i = 0; i < htmlFiles.length; i++) {
    const rel = relative(manualDir, htmlFiles[i]);
    console.log(`[${i + 1}/${htmlFiles.length}] ${rel}`);
    await processFile(htmlFiles[i], downloadedCache, stats);
  }

  console.log(`\n--- Workshop SVGs done ---`);
  console.log(`SVGs downloaded:      ${stats.downloaded}`);
  console.log(`SVGs already existed: ${stats.skipped}`);
  console.log(`Download errors:      ${stats.errors}`);
  console.log(`HTML refs rewritten:  ${stats.refsRewritten}`);
  console.log(`HTML files modified:  ${stats.filesModified}`);
  console.log(`Unique SVGs cached:   ${downloadedCache.size}`);
}
