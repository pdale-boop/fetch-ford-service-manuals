#!/usr/bin/env python3
"""
build_viewer.py — Prepare a scraped Ford manual output directory for viewing.

Usage:
    python3 build_viewer.py <output_dir>
What it does:
    1. Reports path length stats and illegal character warnings
    2. Shortens section folder names (depth 2) to their code only e.g. '307-01A'
    3. Hashes HTML filenames to 8-char MD5 to further shorten paths
    4. Writes path_mapping.json so the viewer can resolve hashed paths
    5. Copies index.html into the output directory
    6. Optionally launches the server via serve.py

Run this after scraping, before viewing.
"""

import os
import re
import sys
import json
import shutil
import hashlib
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
INDEX_SRC  = SCRIPT_DIR / 'index.html'
SECTION_RE = re.compile(r'^(\d{3}-\d{2}[A-Z]?)(\s+.*)?$')




def ask(prompt, default=True):
    suffix = ' [Y/n] ' if default else ' [y/N] '
    while True:
        ans = input(prompt + suffix).strip().lower()
        if ans == '': return default
        if ans in ('y', 'yes'): return True
        if ans in ('n', 'no'): return False
        print("  Please enter y or n.")


def hr():
    print('─' * 60)


def short(path, base):
    try: return str(path.relative_to(base))
    except ValueError: return str(path)


def md5_name(old_path):
    return hashlib.md5(old_path.encode('utf-8')).hexdigest()[:8] + '.html'


def short_section(name):
    m = SECTION_RE.match(name)
    return m.group(1) if m else None


def compute_new_path(old_path):
    """Compute shortened disk path from the original toc.json path."""
    parts = old_path.split('/')
    new_parts = []
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            new_parts.append(md5_name(old_path) if part.endswith('.html') else part)
        elif i == 2:
            short = short_section(part)
            new_parts.append(short if short else part)
        else:
            new_parts.append(part)
    return '/'.join(new_parts)


def build_mapping(toc):
    """Build mapping from original toc.json paths to shortened disk paths.
    Keys are raw toc.json paths — exactly what the viewer constructs and looks up.
    Values are the shortened paths (short folder + hashed filename)."""
    mapping = {}
    def walk(node, path_parts):
        for key, value in node.items():
            if isinstance(value, str):
                old_path = value if (value and '/' in value) else '/'.join(path_parts + [key + '.html'])
                mapping[old_path] = compute_new_path(old_path)
            elif isinstance(value, dict):
                walk(value, path_parts + [key])
    walk(toc, [])
    return mapping


def analyze(output_dir):
    hr()
    print("  Analyzing output directory...\n")
    html_files = [f for f in output_dir.rglob('*.html') if f.name != 'index.html']
    if not html_files:
        print("  WARNING: No HTML files found.")
        return
    base_len = len(str(output_dir)) + 1
    lengths  = [base_len + len(short(f, output_dir)) for f in html_files]
    max_len  = max(lengths)
    over_260 = sum(1 for l in lengths if l > 260)
    print(f"  HTML files:      {len(html_files):,}")
    print(f"  Longest path:    {max_len} chars" + ("  ⚠️  OVER Windows 260-char limit" if max_len > 260 else ""))
    print(f"  Paths > 260:     {over_260}" + ("  (will fail on Windows without fixes)" if over_260 else ""))
    print()




def shorten_paths(output_dir):
    hr()
    print("  Shortening paths...\n")

    with open(output_dir / 'toc.json', encoding='utf-8') as f:
        toc = json.load(f)

    mapping = build_mapping(toc)
    changed = {k: v for k, v in mapping.items() if k != v}
    print(f"  {len(mapping):,} total, {len(changed):,} will change")

    # Write path_mapping.json: key = raw toc.json path, value = shortened disk path
    # This is exactly what the viewer constructs and looks up via resolvePath()
    with open(output_dir / 'path_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"  Written path_mapping.json")

    errors = []
    renamed_dirs = 0
    renamed_files = 0

    # Step 1: Rename section folders (depth 2) FIRST
    dir_renames = {}
    for old_path, new_path in mapping.items():
        op = old_path.split('/')
        np = new_path.split('/')
        if len(op) >= 3 and op[2] != np[2]:
            old_dir = output_dir / op[0] / op[1] / op[2]
            new_dir = output_dir / np[0] / np[1] / np[2]
            dir_renames[str(old_dir)] = (old_dir, new_dir)

    print(f"  Renaming {len(dir_renames):,} section folders...")
    for _, (old_dir, new_dir) in dir_renames.items():
        if not old_dir.exists():
            errors.append(f"DIR MISSING: {old_dir.name}")
            continue
        if old_dir == new_dir:
            continue
        try:
            if new_dir.exists():
                # Merge: move contents into existing shortened dir, remove old
                for item in old_dir.iterdir():
                    dest = new_dir / item.name
                    if not dest.exists():
                        shutil.move(str(item), str(dest))
                if not any(old_dir.iterdir()):
                    old_dir.rmdir()
                renamed_dirs += 1
            else:
                old_dir.rename(new_dir)
                renamed_dirs += 1
        except Exception as e:
            errors.append(f"DIR {old_dir.name}: {e}")
    print(f"    Renamed {renamed_dirs:,} folders")

    # Step 2: Rename files — source path uses NEW folder name (already renamed)
    print(f"  Renaming files...")
    for old_path, new_path in mapping.items():
        if old_path == new_path:
            continue
        op = old_path.split('/')
        np = new_path.split('/')
        # Build source path: use new folder name since folder already renamed in step 1
        if len(op) >= 3 and op[2] != np[2]:
            source_parts = [op[0], op[1], np[2]] + op[3:]
        else:
            source_parts = op
        src = output_dir.joinpath(*source_parts)
        dst = output_dir.joinpath(*np)
        if not src.exists():
            if dst.exists():
                continue
            errors.append(f"MISSING: {src.name}")
            continue
        if src == dst:
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            renamed_files += 1
        except Exception as e:
            errors.append(f"FILE {src.name}: {e}")
    print(f"    Renamed {renamed_files:,} files")

    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors[:10]: print(f"    {e}")
        if len(errors) > 10: print(f"    ... and {len(errors)-10} more")
    else:
        print("  No errors.")
    print()


def copy_index(output_dir):
    hr()
    dst = output_dir / 'index.html'
    if not INDEX_SRC.exists():
        print(f"  ERROR: index.html not found at {INDEX_SRC}")
        return False

    content = INDEX_SRC.read_text(encoding='utf-8')
    book_title = 'Ford'

    # Inject vehicle branding if vehicle_info.json exists
    info_path = output_dir / 'vehicle_info.json'
    if info_path.exists():
        try:
            with open(info_path, encoding='utf-8') as f:
                info = json.load(f)
            book_title = info.get('bookTitle', 'Ford')
            # bookTitle is typically "2025 Maverick" — split for header styling
            parts = book_title.split(' ', 1)
            if len(parts) == 2 and parts[0].isdigit():
                header_logo = f'{parts[1]}<span>{parts[0]}</span> · Service Manual'
                welcome_logo = f'{parts[1]}<span>{parts[0]}</span> · Service Manual'
            else:
                header_logo = f'{book_title} · Service Manual'
                welcome_logo = f'{book_title} · Service Manual'
            page_title = f'{book_title} — Service Manual'

            content = re.sub(
                r'<!--VEHICLE_TITLE-->.*?<!--/VEHICLE_TITLE-->',
                header_logo, content
            )
            content = re.sub(
                r'<!--WELCOME_TITLE-->.*?<!--/WELCOME_TITLE-->',
                welcome_logo, content
            )
            content = re.sub(
                r'<!--PAGE_TITLE-->.*?<!--/PAGE_TITLE-->',
                page_title, content
            )
            print(f"  Branded as: {book_title}")
        except Exception as e:
            print(f"  WARNING: Could not read vehicle_info.json: {e}")

    # Inject cover image if cover.jpg exists
    cover_path = output_dir / 'cover.jpg'
    if cover_path.exists():
        try:
            import base64
            img_data = base64.b64encode(cover_path.read_bytes()).decode('ascii')
            img_tag = f'<img src="data:image/jpeg;base64,{img_data}" alt="{book_title}" class="welcome-truck">'
            content = re.sub(
                r'<!--COVER_IMAGE-->.*?<!--/COVER_IMAGE-->',
                img_tag, content
            )
            print(f"  Injected cover image.")
        except Exception as e:
            print(f"  WARNING: Could not inject cover image: {e}")

    dst.write_text(content, encoding='utf-8')
    print(f"  Copied index.html.")
    return True


def run(output_dir):
    print()
    print("  Ford Manual Viewer Setup")
    hr()
    print(f"  Output directory: {output_dir}")
    print()

    if not output_dir.exists():
        print(f"  ERROR: Directory not found: {output_dir}")
        sys.exit(1)
    if not (output_dir / 'toc.json').exists():
        print("  ERROR: toc.json not found.")
        sys.exit(1)

    if (output_dir / 'path_mapping.json').exists() and (output_dir / 'index.html').exists():
        print("  This directory appears to already be set up.")
        if not ask("  Re-run setup anyway?", default=False):
            return True
    analyze(output_dir)

    hr()
    print("  Path shortening reduces paths for Windows compatibility:")
    print("  - Section folders shortened to code only (e.g. '307-01A')")
    print("  - HTML filenames hashed to 8-char MD5")
    print()
    if ask("  Shorten paths?"):
        shorten_paths(output_dir)
    else:
        if not (output_dir / 'path_mapping.json').exists():
            with open(output_dir / 'path_mapping.json', 'w') as f:
                json.dump({}, f)
        print()

    if not copy_index(output_dir):
        return False
    print()
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    output_dir = Path(sys.argv[1]).expanduser().resolve()
    ok = run(output_dir)
    if ok:
        hr()
        if ask("  Launch viewer now?"):
            serve_py = SCRIPT_DIR / 'serve.py'
            if serve_py.exists():
                subprocess.run([sys.executable, str(serve_py), str(output_dir)])
            else:
                print(f"  Run: cd \"{output_dir}\" && npx serve .")
        else:
            print(f"\n  Run later: python3 serve.py \"{output_dir}\"\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted.")
        sys.exit(0)
