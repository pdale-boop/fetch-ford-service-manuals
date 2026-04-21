#!/usr/bin/env python3
"""
Download hotspot illustration SVGs from workshop HTML pages,
apply CSS patches, save locally, and rewrite HTML to use <object> tags.

Usage:
    python3 process_workshop_svgs.py [manual-output-dir]

Defaults to ./manual-output if no argument given.
Backs up the directory before making changes.
"""

import os
import re
import sys
import shutil
import html
import subprocess
import time
from pathlib import Path


def backup_dir(source):
    """Create a backup copy of the manual-output directory."""
    backup = source.parent / f"{source.name}-backup-svgs"
    if backup.exists():
        print(f"Backup already exists at {backup}, skipping backup.")
        return
    print(f"Backing up {source} -> {backup} ...")
    shutil.copytree(source, backup)
    print(f"Backup complete.")


def extract_svg_refs(html_content):
    """Find all hotspotillus divs with SVG URLs."""
    pattern = re.compile(
        r'<div\s[^>]*?data-type="hotspotillus"[^>]*?data-svg-path="([^"]+)"[^>]*?>(?:</div>)?',
        re.IGNORECASE,
    )
    results = []
    for m in pattern.finditer(html_content):
        results.append({
            "full_match": m.group(0),
            "raw_url": m.group(1),
        })
    return results


def extract_image_id(url):
    """Extract image ID from URL like ...?id=E361766_EUR&s=SVG"""
    m = re.search(r'[?&]id=([^&]+)', url)
    return m.group(1) if m else None


def patch_svg_css(svg_content):
    """Make .sttxt visible and .stcallout hidden."""
    svg_content = re.sub(
        r'\.sttxt\s*\{[^}]*\}',
        '.sttxt { visibility: visible; }',
        svg_content,
        flags=re.IGNORECASE,
    )
    svg_content = re.sub(
        r'\.stcallout\s*\{[^}]*\}',
        '.stcallout { visibility: hidden; }',
        svg_content,
        flags=re.IGNORECASE,
    )
    return svg_content


def download_svg(url, dest):
    """Download SVG via curl, apply CSS patch, save to dest."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-f", "--max-time", "30", url],
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"    ERROR: curl returned {result.returncode} for {url}")
            return False
        svg_content = result.stdout.decode("utf-8")
        svg_content = patch_svg_css(svg_content)
        dest.write_text(svg_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"    ERROR downloading {url}: {e}")
        return False


def process_file(html_path, downloaded_cache, stats):
    """Process a single HTML file."""
    content = html_path.read_text(encoding="utf-8")
    refs = extract_svg_refs(content)
    if not refs:
        return

    file_dir = html_path.parent
    updated = content

    for ref in refs:
        # Decode HTML entities
        url = html.unescape(ref["raw_url"])
        image_id = extract_image_id(url)
        if not image_id:
            print(f"    WARN: Could not extract ID from: {url}")
            stats["errors"] += 1
            continue

        svg_filename = f"{image_id}.svg"
        svg_path = file_dir / svg_filename

        if image_id not in downloaded_cache:
            if svg_path.exists():
                print(f"    Already exists: {svg_filename}")
                stats["skipped"] += 1
            else:
                if download_svg(url, svg_path):
                    print(f"    Downloaded: {svg_filename}")
                    stats["downloaded"] += 1
                    time.sleep(0.1)  # be gentle
                else:
                    stats["errors"] += 1
                    continue
            downloaded_cache[image_id] = svg_path

        # Rewrite div -> object
        object_tag = (
            f'<object data="{svg_filename}" type="image/svg+xml" '
            f'class="workshop-svg" style="width:100%; max-width:100%;"></object>'
        )
        updated = updated.replace(ref["full_match"], object_tag)
        stats["refs_rewritten"] += 1

    if updated != content:
        html_path.write_text(updated, encoding="utf-8")
        stats["files_modified"] += 1


def main():
    manual_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./manual-output")
    manual_dir = manual_dir.resolve()

    if not manual_dir.is_dir():
        print(f"ERROR: Directory not found: {manual_dir}")
        sys.exit(1)

    print(f"Manual directory: {manual_dir}")

    # Backup first
    backup_dir(manual_dir)

    # Find all HTML files with hotspotillus
    html_files = []
    for html_path in manual_dir.rglob("*.html"):
        if html_path.name == "index.html":
            continue
        content = html_path.read_text(encoding="utf-8")
        if 'data-type="hotspotillus"' in content:
            html_files.append(html_path)

    print(f"\nFound {len(html_files)} HTML files with hotspot SVGs.\n")

    if not html_files:
        print("Nothing to do.")
        return

    stats = {
        "downloaded": 0,
        "skipped": 0,
        "errors": 0,
        "refs_rewritten": 0,
        "files_modified": 0,
    }
    downloaded_cache = {}

    for i, html_path in enumerate(sorted(html_files), 1):
        rel = html_path.relative_to(manual_dir)
        print(f"[{i}/{len(html_files)}] {rel}")
        process_file(html_path, downloaded_cache, stats)

    print(f"\n--- Done ---")
    print(f"SVGs downloaded:    {stats['downloaded']}")
    print(f"SVGs already existed: {stats['skipped']}")
    print(f"Download errors:    {stats['errors']}")
    print(f"HTML refs rewritten: {stats['refs_rewritten']}")
    print(f"HTML files modified: {stats['files_modified']}")
    print(f"Unique SVGs cached: {len(downloaded_cache)}")


if __name__ == "__main__":
    main()
