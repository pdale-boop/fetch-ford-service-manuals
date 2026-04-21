#!/usr/bin/env python3
"""
FordManual.py — Interactive launcher for the Ford manual scraper.

Usage:
    python3 FordManual.py

Walks you through:
    - Setting up your output directory
    - Collecting PTS parameters from browser DevTools (F12)
    - Collecting your PTS session cookies
    - Running the scraper
    - Setting up and launching the viewer

A session.json file is saved after each step so you can resume
if you close the script partway through.
"""

import os
import sys
import json
import shutil
import subprocess
import urllib.parse
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent.resolve()
SESSION_FILE = SCRIPT_DIR / 'session.json'
CONFIG_FILE  = SCRIPT_DIR / 'config.json'
COOKIE_FILE  = SCRIPT_DIR / 'cookies.txt'

MIN_NODE_VERSION = 18


# ── Helpers ───────────────────────────────────────────────────────────────────

def hr(char='─', width=60):
    print(char * width)

def section(title: str):
    print()
    hr()
    print(f"  {title}")
    hr()
    print()

def ask(prompt: str, default: bool = True) -> bool:
    suffix = ' [Y/n] ' if default else ' [y/N] '
    while True:
        ans = input(prompt + suffix).strip().lower()
        if ans == '':
            return default
        if ans in ('y', 'yes'):
            return True
        if ans in ('n', 'no'):
            return False
        print("  Please enter y or n.")

def pause(msg="  Press Enter when ready..."):
    input(msg)

def load_session() -> dict:
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_session(session: dict):
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(session, f, indent=2)

def clear_session():
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()



# ── Pre-flight: Dependencies ─────────────────────────────────────────────────

def check_dependencies():
    """Verify Node, npm, node_modules, and Playwright Chromium."""
    errors = []

    # Node.js
    node = shutil.which('node')
    if not node:
        errors.append('node_missing')
    else:
        try:
            out = subprocess.run([node, '--version'], capture_output=True, text=True)
            node_ver = int(out.stdout.strip().lstrip('v').split('.')[0])
            if node_ver < MIN_NODE_VERSION:
                errors.append(f'node_old:{node_ver}')
        except Exception:
            errors.append('node_version_unknown')

    # npm
    npm = shutil.which('npm')
    if not npm:
        errors.append('npm_missing')

    if errors:
        print()
        hr()
        print('  Dependency Check Failed')
        hr()
        print()
        for e in errors:
            if e == 'node_missing':
                print('  ✗  Node.js is not installed.')
                print()
                print('  Install it from: https://nodejs.org/')
                print('  Or use nvm: https://github.com/nvm-sh/nvm')
                print()
                print('  Arch Linux:      sudo pacman -S nodejs npm')
                print('  Ubuntu/Debian:   sudo apt install nodejs npm')
                print('  macOS (brew):    brew install node')
                print('  Windows:         https://nodejs.org/ (includes npm)')
            elif e.startswith('node_old:'):
                v = e.split(':')[1]
                print(f'  ✗  Node.js v{v} found, but v{MIN_NODE_VERSION}+ is required.')
                print()
                print('  Update from: https://nodejs.org/')
            elif e == 'node_version_unknown':
                print('  ✗  Could not determine Node.js version.')
            elif e == 'npm_missing':
                print('  ✗  npm not found (usually included with Node.js).')
                print()
                print('  Reinstall Node from: https://nodejs.org/')
        print()
        sys.exit(1)

    # node_modules
    node_modules = SCRIPT_DIR / 'node_modules'
    if not node_modules.exists():
        print('  Installing npm dependencies...')
        result = subprocess.run([npm, 'install'], cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print()
            print('  ✗  npm install failed. Check the output above.')
            sys.exit(1)
        print('  ✓  Dependencies installed')

    # Playwright Chromium (idempotent — fast no-op if already present)
    npx = shutil.which('npx')
    result = subprocess.run(
        [npx or 'npx', 'playwright', 'install', 'chromium'],
        cwd=SCRIPT_DIR,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        print('  ⚠️  Playwright browser install failed.')
        print('  Try manually: npx playwright install chromium')
        if not ask('  Continue anyway?', default=False):
            sys.exit(1)

    print('  ✓  Dependencies OK')


# ── Step 0: Resume ────────────────────────────────────────────────────────────

def maybe_resume() -> dict:
    session = load_session()
    if not session:
        return {}

    section("Resume Previous Session")
    print("  A previous session was found with the following data:")
    print()

    if 'output_dir' in session:
        print(f"  Output directory:  {session['output_dir']}")
    if 'workshop' in session:
        ws = session['workshop']
        print(f"  Vehicle:           {ws.get('modelYear', '?')} (vehicleId: {ws.get('vehicleId', '?')})")
        print(f"  Workshop book:     {ws.get('book', '?')}")
        print(f"  Wiring book:       {ws.get('WiringBookCode', '?')}")
    if 'wiring' in session:
        print(f"  Wiring env:        {session['wiring'].get('environment', '?')}")
    if 'cookies_saved' in session:
        print(f"  Cookies:           saved")
    print()

    if ask("  Resume this session?"):
        return session
    else:
        clear_session()
        return {}


# ── Step 1: Output directory ──────────────────────────────────────────────────

def get_output_dir(session: dict) -> Path:
    if 'output_dir' in session:
        p = Path(session['output_dir'])
        print(f"  Using saved output directory: {p}")
        return p

    section("Step 1 of 5 — Output Directory")
    print("  Where do you want to save the manual?")
    print("  Enter a full path, or press Enter to use ./manual-output")
    print()

    while True:
        raw = input("  Output directory: ").strip()
        if not raw:
            raw = str(SCRIPT_DIR / 'manual-output')
        p = Path(raw).expanduser().resolve()

        if p.exists() and any(p.iterdir()):
            print(f"\n  Directory exists and is not empty: {p}")
            choice = input("  (s)kip scrape and go to viewer setup, (r)escrape, or (c)ancel? [s/r/c] ").strip().lower()
            if choice == 's':
                session['output_dir'] = str(p)
                session['skip_scrape'] = True
                save_session(session)
                return p
            elif choice == 'r':
                session['output_dir'] = str(p)
                save_session(session)
                return p
            else:
                continue
        else:
            p.mkdir(parents=True, exist_ok=True)
            session['output_dir'] = str(p)
            save_session(session)
            return p


# ── Step 2: Workshop params ───────────────────────────────────────────────────

REQUIRED_WORKSHOP_FIELDS = [
    'vehicleId', 'modelYear', 'book', 'booktype',
    'WiringBookCode', 'country', 'language',
    'contentmarket', 'contentlanguage', 'languageOdysseyCode',
]

def parse_workshop_payload(raw: str) -> dict:
    """Parse URL-encoded form data from the TreeAndCover request payload.
    Also handles accidental POST URL prefix or query string format."""
    raw = raw.strip()
    # Strip POST/GET prefix if user accidentally copied the request line
    for prefix in ('POST ', 'GET '):
        if raw.upper().startswith(prefix):
            raw = raw[len(prefix):].strip()
    # Take only first line in case of multi-line paste with method + URL
    raw = raw.splitlines()[0].strip()
    # If it looks like a URL, try to extract query string
    if raw.startswith('http'):
        if '?' in raw:
            raw = raw.split('?', 1)[1]
        else:
            return {}
    try:
        params = dict(urllib.parse.parse_qsl(raw.strip(), keep_blank_values=True))
        return params
    except Exception:
        return {}

def validate_workshop(params: dict) -> list:
    missing = [f for f in REQUIRED_WORKSHOP_FIELDS if not params.get(f)]
    return missing

def get_workshop_params(session: dict) -> dict:
    if 'workshop' in session:
        print(f"  Using saved workshop params (vehicleId: {session['workshop'].get('vehicleId')})")
        return session['workshop']

    section("Step 2 of 5 — Workshop Parameters (F12)")
    print("  We need to capture some parameters from Ford PTS.")
    print()
    print("  Instructions:")
    print("  1. Open PTS: https://www.fordtechservice.dealerconnection.com")
    print("  2. Navigate to your vehicle using By Year & Model, press GO")
    print("  3. Open DevTools (F12) → Network tab")
    print("  4. Clear the network log (trash can or circle-with-line icon)")
    print("  5. Click the Workshop tab in PTS")
    print("  6. In the Network filter box, type: TreeAndCover")
    print("  7. Click the POST request that appears in the list")
    print("  8. A panel opens on the right. Look for a tab called:")
    print("     'Request' or 'Payload' (Firefox) / 'Payload' (Chrome)")
    print("  9. Click that tab. You will see a long line of text that starts with:")
    print("     isMobile=no&vin=&vehicleId=...")
    print("     That is what you need to copy — NOT the URL at the top of the panel.")
    print()
    print("  ⚠️  FIREFOX USERS: Before copying, look for a 'Raw' toggle in the")
    print("     top-right of that panel and turn it ON. Then select all and copy.")
    print()
    pause()
    print()

    while True:
        print("  Paste the request payload below, then press Enter twice:")
        lines = []
        while True:
            line = input()
            if line == '' and lines:
                break
            lines.append(line)
        raw = ' '.join(lines).strip()

        params = parse_workshop_payload(raw)
        missing = validate_workshop(params)

        if missing:
            print(f"\n  ⚠️  Could not find these required fields: {', '.join(missing)}")
            print("  Make sure you copied the full payload and try again.")
            print()
            continue

        print(f"\n  ✓  Found: vehicleId={params['vehicleId']}, modelYear={params['modelYear']}, book={params['book']}")

        # bookTitle will be filled in from the TableOfContents URL in the wiring step
        # Remove fields we don't need in config
        for field in ['isMobile', 'vin', 'category', 'CategoryDescription',
                      'fromPageBase', 'strVehLine', 'strProdType', 'WiringFormat', 'contentgroup']:
            params.pop(field, None)

        session['workshop'] = params
        save_session(session)
        return params


# ── Step 3: Wiring params ─────────────────────────────────────────────────────

def parse_wiring_url(raw: str) -> dict:
    """Extract query params from the TableofContent or TableOfContents URL."""
    raw = raw.strip()
    # Strip "GET " prefix if user accidentally copied it
    if raw.upper().startswith('GET '):
        raw = raw[4:].strip()
    # Take only the first line in case of accidental newline
    raw = raw.splitlines()[0].strip()
    if '?' in raw:
        qs = raw.split('?', 1)[1]
    else:
        qs = raw
    try:
        return dict(urllib.parse.parse_qsl(qs, keep_blank_values=True))
    except Exception:
        return {}

def get_wiring_params(session: dict) -> dict:
    if 'wiring' in session:
        print(f"  Using saved wiring params (env: {session['wiring'].get('environment')})")
        return session['wiring']

    section("Step 3 of 5 — Wiring Parameters (F12)")
    print("  Now we need the wiring diagram parameters.")
    print()
    print("  Instructions:")
    print("  1. In DevTools Network tab, clear the log again")
    print("  2. Click the Wiring tab in PTS")
    print("  3. In the Network filter box, type: TableofContent  (singular — no 's')")
    print("  4. Click the GET request that appears")
    print("  5. Copy the full URL from the request — it looks like:")
    print("     https://www.fordservicecontent.com/.../wiring/TableofContent?environment=prod_1_3_...")
    print()
    pause()
    print()

    while True:
        print("  Paste the full URL or just the query string:")
        raw = input("  > ").strip()

        params = parse_wiring_url(raw)
        required = ['environment', 'bookType', 'languageCode']
        missing  = [f for f in required if not params.get(f)]

        if missing:
            print(f"\n  ⚠️  Could not find: {', '.join(missing)}")
            print("  Make sure you copied the full URL including the ? and parameters.")
            print()
            continue

        wiring = {
            'environment':   params['environment'],
            'bookType':      params['bookType'],
            'languageCode':  params['languageCode'],
        }

        # Also try to get WiringBookCode from TableOfContents (plural) request
        print(f"\n  ✓  Found environment: {wiring['environment']}")
        print()
        print("  One more request needed for the wiring book code.")
        print("  Instructions:")
        print("  1. In Network tab, filter for: TableOfContents  (plural — with 's')")
        print("  2. If you don't see it, select a wiring diagram section in PTS")
        print("  3. Copy the full URL of that GET request")
        print()
        pause()
        print()

        while True:
            print("  Paste the TableOfContents URL (or press Enter to skip):")
            raw2 = input("  > ").strip()

            if not raw2:
                # Fallback if user skipped — prompt manually
                if not session['workshop'].get('bookTitle'):
                    session['workshop']['bookTitle'] = input("  Enter a book title (e.g. '2025 Maverick'): ").strip()
                    session['workshop']['WiringBookTitle'] = session['workshop']['bookTitle']
                break

            params2 = parse_wiring_url(raw2)
            if not params2.get('book') and not params2.get('booktitle'):
                print("  ⚠️  Could not parse that URL. Make sure you copied the full URL with query params.")
                print("     It should look like: https://www.fordtechservice.dealerconnection.com/Wiring/TableOfContents?booktitle=...")
                print()
                continue

            if params2.get('booktitle'):
                session['workshop']['WiringBookTitle'] = params2['booktitle']
                session['workshop']['bookTitle']       = params2['booktitle']
                print(f"  ✓  Book title: {params2['booktitle']}")
            if params2.get('book'):
                session['workshop']['WiringBookCode'] = params2['book']
                print(f"  ✓  Wiring book code: {params2['book']}")
            break

        # Grab cookies from fordservicecontent.com
        print()
        hr()
        print("  Now we need cookies from the fordservicecontent.com request.")
        print("  This is required for wiring diagram downloads.")
        print()
        print("  Instructions:")
        print("  1. Go back to the Network tab and find the TableofContent")
        print("     (singular, no 's') request to fordservicecontent.com")
        print("  2. Click it → Request Headers")
        print()
        print("  ⚠️  FIREFOX USERS: Enable the Raw toggle before copying.")
        print()
        print("  3. Find the Cookie: header")
        print("  4. Copy everything AFTER 'Cookie: '")
        print(f"  5. Open cookies.txt in a text editor:")
        print(f"       {COOKIE_FILE}")
        print(f"  6. At the END of the existing content, add '; ' then paste the new cookies")
        print(f"     The file must be ONE LINE: <block1>; <block2>")
        print()
        print("  TIP: On Windows:  notepad \"" + str(COOKIE_FILE) + "\"")
        print("  On Mac:           open -e '" + str(COOKIE_FILE) + "'")
        print()
        pause("  Press Enter once you've saved cookies.txt with both blocks...")
        print()

        session['wiring'] = wiring
        save_session(session)
        return wiring


# ── Step 4: Cookies ───────────────────────────────────────────────────────────

EXPECTED_COOKIES = ['Ford.TSO.PTSSuite', 'TPS%2DMEMBERSHIP', 'PERSISTENT']

def validate_cookies(raw: str) -> list:
    missing = [c for c in EXPECTED_COOKIES if c not in raw]
    return missing

def get_cookies(session: dict) -> str:
    if session.get('cookies_saved') and COOKIE_FILE.exists():
        print("  Using saved cookies.")
        with open(COOKIE_FILE, encoding='utf-8') as f:
            return f.read().strip()

    section("Step 4 of 5 — Verify Cookies")
    print("  Verifying your cookie file...")
    print()

    # Create empty file so the editor can open it
    if not COOKIE_FILE.exists():
        COOKIE_FILE.write_text('')

    while True:
        pause("  Press Enter once you've saved the cookie string to the file...")
        print()

        if not COOKIE_FILE.exists() or not COOKIE_FILE.read_text().strip():
            print("  ⚠️  File is empty or missing. Please save your cookies to:")
            print(f"       {COOKIE_FILE}")
            continue

        raw = COOKIE_FILE.read_text().strip()

        # Strip "Cookie: " prefix if they accidentally included it
        if raw.lower().startswith('cookie:'):
            raw = raw[7:].strip()
            COOKIE_FILE.write_text(raw)

        missing = validate_cookies(raw)
        if missing:
            print(f"  ⚠️  Expected cookies not found: {', '.join(missing)}")
            print("  This may cause login issues.")
            if not ask("  Continue anyway?", default=False):
                continue

        session['cookies_saved'] = True
        save_session(session)
        print(f"  ✓  Cookies loaded from {COOKIE_FILE.name}")
        return raw


# ── Step 5: Scrape options ────────────────────────────────────────────────────

def get_scrape_options(session: dict) -> dict:
    if 'scrape_options' in session:
        return session['scrape_options']

    section("Step 5 of 5 — Scrape Options")

    opts = {}

    print("  Download options:")
    print()
    opts['workshop'] = ask("  Download workshop manual?")
    opts['wiring']   = ask("  Download wiring diagrams?")
    print()

    print("  Output format:")
    print("  (HTML is default — faster, smaller, works in the viewer)")
    print("  (PDF takes much longer and produces larger files)")
    print()
    pdf = ask("  Also generate PDFs?", default=False)
    if pdf:
        opts['pdfonly'] = ask("  PDF only (delete HTML after)?", default=False)
        opts['pdf']     = not opts['pdfonly']
    else:
        opts['pdf']     = False
        opts['pdfonly'] = False

    print()
    opts['ignore_errors'] = ask("  Continue past download errors?")

    session['scrape_options'] = opts
    save_session(session)
    return opts


# ── Write config ──────────────────────────────────────────────────────────────

def write_config(workshop: dict, wiring: dict):
    # Workshop page fetcher needs the environment string too
    workshop_with_env = {**workshop, "environment": wiring.get("environment", "prod_1_3_4202026")}
    config = {
        "workshop": workshop_with_env,
        "wiring":   wiring,
        "pre_2003": {
            "alphabeticalIndexURL": "https://www.fordservicecontent.com/pubs/content/....."
        }
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


# ── Run scraper ───────────────────────────────────────────────────────────────

def count_missing_pages(output_dir: Path) -> int:
    """Count how many workshop HTML pages from toc.json are missing on disk."""
    toc_path = output_dir / 'toc.json'
    if not toc_path.exists():
        return 0

    # Load path_mapping.json if it exists (shortened paths)
    mapping_path = output_dir / 'path_mapping.json'
    mapping = {}
    if mapping_path.exists():
        try:
            with open(mapping_path, encoding='utf-8') as f:
                mapping = json.load(f)
        except Exception:
            pass

    with open(toc_path, encoding='utf-8') as f:
        toc = json.load(f)

    missing = 0

    def walk(node, parts):
        nonlocal missing
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and value and '/' not in value:
                    rel_path = '/'.join(parts + [key]) + '.html'
                    # Check mapped (shortened) path first, then original
                    mapped = mapping.get(rel_path, rel_path)
                    if not (output_dir / mapped).exists() and not (output_dir / rel_path).exists():
                        missing += 1
                elif isinstance(value, dict):
                    walk(value, parts + [key])

    walk(toc, [])
    return missing


def run_scraper(output_dir: Path, opts: dict):
    section("Running Scraper")

    npm = shutil.which('npm')

    cmd = [npm, 'start', '--',
           '-c', str(CONFIG_FILE),
           '-s', str(COOKIE_FILE),
           '-o', str(output_dir)]

    if not opts.get('workshop'):
        cmd.append('--noWorkshop')
    if not opts.get('wiring'):
        cmd.append('--noWiring')
    if opts.get('pdf'):
        cmd.append('--pdf')
    if opts.get('pdfonly'):
        cmd.append('--pdfonly')
    if opts.get('ignore_errors'):
        cmd.append('--ignoreSaveErrors')

    print(f"  Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    return result.returncode == 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║     Ford Service Manual Downloader           ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print("  This tool will walk you through downloading your")
    print("  Ford PTS service manual for offline viewing.")
    print()
    print("  You'll need:")
    print("  - An active Ford PTS subscription")
    print("    (https://www.motorcraftservice.com/Purchase/ViewProduct)")
    print("  - A browser with DevTools (F12)")
    print()

    session = maybe_resume()

    check_dependencies()

    # If workshop params missing but config files exist, offer to reuse
    if 'workshop' not in session and CONFIG_FILE.exists() and COOKIE_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding='utf-8') as f:
                prev_config = json.load(f)
            ws = prev_config.get('workshop', {})
            wr = prev_config.get('wiring', {})
            if ws:
                section("Previous Configuration Found")
                print(f"  Vehicle:  {ws.get('modelYear', '?')} (book: {ws.get('book', '?')})")
                print(f"  Wiring:   {wr.get('environment', '?')}")
                print()
                if ask("  Reuse this configuration?"):
                    session['workshop'] = ws
                    session['wiring'] = wr
                    session['cookies_saved'] = True
                    save_session(session)
        except Exception:
            pass

    # Collect all inputs
    output_dir = get_output_dir(session)

    skip_scrape = session.get('skip_scrape', False)

    if not skip_scrape:
        workshop = get_workshop_params(session)
        wiring   = get_wiring_params(session)
        cookies  = get_cookies(session)
        opts     = get_scrape_options(session)

        # Write config and run
        write_config(workshop, wiring)

        section("Ready to Download")
        print(f"  Output:   {output_dir}")
        print(f"  Vehicle:  {workshop.get('modelYear')} (book: {workshop.get('book')})")
        print(f"  Wiring:   {wiring.get('environment')}")
        print()

        if not ask("  Start downloading now?"):
            print()
            print("  You can run the scraper manually with:")
            print(f"    npm start -- -c config.json -s cookies.txt -o \"{output_dir}\"")
            print()
            sys.exit(0)

        success = run_scraper(output_dir, opts)

        if not success:
            print()
            print("  ⚠️  Scraper exited with errors.")
            if not ask("  Continue to viewer setup anyway?", default=False):
                sys.exit(1)

        # Check for missing pages and offer retry
        while True:
            missing_pages = count_missing_pages(output_dir)
            if missing_pages == 0:
                break
            print()
            print(f"  ⚠️  {missing_pages:,} pages are missing from the output.")
            if ask(f"  Re-scrape now to fill them in?", default=True):
                success = run_scraper(output_dir, opts)
                if not success:
                    print("  ⚠️  Scraper exited with errors.")
                    if not ask("  Continue anyway?", default=False):
                        sys.exit(1)
            else:
                print(f"  Continuing with {missing_pages:,} missing pages.")
                break
    else:
        print(f"\n  Skipping scrape — using existing output at {output_dir}")

    # Viewer setup
    section("Viewer Setup")
    print("  The scrape is complete. Now let's set up the viewer.")
    print()

    if ask("  Run viewer setup now?"):
        build_viewer = SCRIPT_DIR / 'build_viewer.py'
        if build_viewer.exists():
            result = subprocess.run([sys.executable, str(build_viewer), str(output_dir)])
        else:
            print(f"  build_viewer.py not found at {build_viewer}")
            print(f"  Run manually: python3 build_viewer.py \"{output_dir}\"")
    else:
        print()
        print("  To set up the viewer later, run:")
        print(f"    python3 build_viewer.py \"{output_dir}\"")
        print()

    # Offer cleanup of session files
    section("Cleanup")
    print("  The following session files can be removed:")
    print(f"    {SESSION_FILE.name}  (resume state)")
    print(f"    {CONFIG_FILE.name}   (vehicle parameters)")
    print(f"    {COOKIE_FILE.name}   (PTS session cookies)")
    print()
    print("  Keep them to re-run the scraper without re-entering everything.")
    print("  Remove them if you're done — cookies contain session credentials.")
    print()
    if ask("  Remove session files?", default=False):
        for f in [SESSION_FILE, CONFIG_FILE, COOKIE_FILE]:
            if f.exists():
                f.unlink()
        print("  ✓  Cleaned up.")
    else:
        clear_session()  # Always clear session.json (resume state)
        print("  ✓  Kept config.json and cookies.txt for future runs.")
    print()
    print("  Done.")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Progress saved to session.json — run again to resume.")
        print()
        sys.exit(0)
