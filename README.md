# fetch-ford-service-manuals

Downloads HTML (and optionally PDF) versions of Ford Service Manuals from PTS.

Bought a 72-hour subscription to Ford's service manuals and want to save it permanently? Here's the repo for you.

These manuals are copyrighted by Ford, so don't share them!

> **Fork notes:** This is a fork of [iamtheyammer/fetch-ford-service-manuals](https://github.com/iamtheyammer/fetch-ford-service-manuals) with bug fixes and improvements. See [Changes from upstream](#changes-from-upstream) for details.

## Table of Contents

- [Quick Start (Guided)](#quick-start-guided)
- [Manual Setup (Advanced)](#manual-setup-advanced)
- [Viewing the Manual](#viewing-the-manual)
- [Results](#results)
- [Changes from upstream](#changes-from-upstream)
- [Common Issues](#common-issues)
- [FAQ](#faq)

## Quick Start (Guided)

`FordManual.py` is an interactive wizard that walks you through the entire process — collecting parameters, cookies, installing dependencies, running the scraper, and optionally setting up the offline viewer.

### Prerequisites

- **Python 3.8+** (usually pre-installed on macOS and Linux)
- **Node.js 18+** from [nodejs.org](https://nodejs.org/) (includes npm)
- **An active Ford PTS subscription** from [Motorcraft](https://www.motorcraftservice.com/Purchase/ViewProduct) (72-hour is fine)
- **A browser with DevTools** (F12) — Firefox or Chrome both work

### Run

1. Clone this repository:
   ```
   git clone https://github.com/pdale-boop/fetch-ford-service-manuals.git
   cd fetch-ford-service-manuals
   ```
2. Run the guided setup:
   ```
   python3 FordManual.py
   ```

The wizard will:
1. Check and install npm dependencies and Playwright automatically
2. Walk you through collecting parameters from PTS using DevTools (F12)
3. Collect your session cookies
4. Let you choose what to download (workshop, wiring, PDF options)
5. Run the scraper with automatic resume support
6. Optionally set up the offline viewer

Progress is saved to `session.json` after each step — if you close the script, just run it again to resume.

## Manual Setup (Advanced)

If you prefer to run the scraper directly without the wizard.

### Dependencies

1. Install [Node.js 18+](https://nodejs.org/)
2. Install npm dependencies:
   ```
   npm install
   ```
3. Install Playwright's browser:
   ```
   npx playwright install chromium
   ```

### Configuration

You need two files in the repo root:

**`config.json`** — vehicle parameters collected from PTS DevTools:

1. Open PTS and navigate to your vehicle
2. Open DevTools (F12) → Network tab
3. Click the **Workshop** tab in PTS
4. Filter for `TreeAndCover` — click the POST request
5. Copy the request payload (Firefox: enable **Raw** toggle first)
6. Click the **Wiring** tab in PTS
7. Filter for `TableofContent` (singular) — copy the `environment`, `bookType`, and `languageCode` query params
8. Filter for `TableOfContents` (plural) — copy the `booktitle` and `book` query params

Structure:
```json
{
  "workshop": {
    "vehicleId": "...",
    "modelYear": "...",
    "book": "...",
    "booktype": "...",
    "bookTitle": "...",
    "WiringBookCode": "...",
    "WiringBookTitle": "...",
    "country": "...",
    "language": "...",
    "contentmarket": "...",
    "contentlanguage": "...",
    "languageOdysseyCode": "...",
    "environment": "..."
  },
  "wiring": {
    "environment": "...",
    "bookType": "...",
    "languageCode": "..."
  }
}
```

Alternatively, copy `templates/params.json.template` to `config.json` and fill in the values.

**`cookies.txt`** — your PTS session cookies (two sources, combined into one file):

1. In DevTools Network tab, find the `TableOfContents` (plural, with 's') request to `fordtechservice.dealerconnection.com`
2. Click it → Request Headers → find the `Cookie:` header
3. Copy everything **after** `Cookie: ` into `cookies.txt`
4. Now find the `TableofContent` (singular, no 's') request to `fordservicecontent.com`
5. Copy its `Cookie:` header value
6. In `cookies.txt`, add `; ` after the first paste, then paste the second set — the file must be **one line** with both blocks
7. **Firefox users:** Enable the **Raw** toggle in Request Headers before copying each time, or you'll get invalid character errors

### Run the scraper

```
npm start -- -c config.json -s cookies.txt -o /path/to/output/
```

Options:
- `--noWorkshop` — skip workshop manual, download wiring only
- `--noWiring` — skip wiring diagrams, download workshop only
- `--pdf` — generate PDFs alongside HTML
- `--pdfonly` — generate PDFs and delete HTML afterward
- `--ignoreSaveErrors` — continue past download errors
- `--noCookieTest` — skip cookie validation on startup

**You will likely need to run this 2-3 times** to get all files. Ford's servers occasionally return errors on individual pages. Already-downloaded files are skipped on re-run.

Run `npm start -- --help` for all options.

## Viewing the Manual

After scraping, you have two options:

### Option 1: Browse files directly

The output directory contains HTML files organized to match the PTS structure. Open any file in a browser. The `cover.html` file has the table of contents, and `toc.json` has the machine-readable version.

### Option 2: Offline viewer

`build_viewer.py` sets up a local viewer with tree navigation and search:

```
python3 build_viewer.py /path/to/output/
```

This will:
- **Shorten paths** for Windows compatibility (section folders shortened to codes like `307-01A`, HTML filenames hashed to 8 characters). A `path_mapping.json` file maps original names to shortened names.
- Copy `index.html` into the output directory
- Optionally launch a local web server

The viewer features include:
- Sidebar tree navigation, wiring diagrams, and connector views
- Full-text search across all workshop pages, connectors, and wiring
- Cmd/Ctrl+scroll zoom with floating zoom controls
- Dark mode (follows system preference)
- Print support (coming soon)
- Cross-links between workshop pages, connectors, and wiring diagrams

The viewer works entirely offline — no internet connection required after setup.

#### Workshop illustration SVGs

Workshop pages with interactive hotspot illustrations reference SVGs hosted on Ford's CDN. During scraping, these are automatically downloaded, CSS-patched (text labels made visible, callout overlays hidden), and saved alongside the HTML files. The HTML is rewritten to use local `<object>` tags — no internet connection needed to view illustrations.

If you need to re-process SVGs on an existing output directory (e.g. after a partial scrape), you can run the step standalone:

```
python3 process_workshop_svgs.py /path/to/output/
```

**Re-scraping after shortening:** If you run the scraper again into a directory that's already been through `build_viewer.py`, the scraper will check `path_mapping.json` to find existing shortened files and skip them correctly.

## Results

### Workshop manual (2003 or newer)

The folder structure mirrors PTS. For example, a page at `General Information → Service Information → 100-00 → About this Manual` will be at `1- General Information/00- Service Information/100-00/About this Manual.html` (or its hashed equivalent if you ran the viewer setup).

#### Truncated filenames

Filenames over 200 characters are truncated with ` (docID truncated)` appended. Search for the docID in `toc.json` to find the full title.

### Workshop manual (2002 or older)

Older vehicles use the alphabetical index. The output is a flat structure with all pages in the output folder.

Browse via `outputpath/AA_Table_Of_Contents.html` — all links work except the letter navigation at the top.

### Wiring diagrams

Wiring diagrams are in `outputpath/Wiring/` with their own `toc.json`.

#### Connector Views

If present, `Wiring/Connector Views/` contains self-contained HTML files for each connector, including:
- Face diagram (SVG)
- Pin table with circuit numbers, gauge, function, and qualifier
- Terminal part numbers with service part sizes
- Available pigtail kits with images and vehicle application info

A `Connectors.csv` file maps every connector to its location in the vehicle.

## Changes from upstream

This fork includes the following fixes and improvements over [iamtheyammer/fetch-ford-service-manuals](https://github.com/iamtheyammer/fetch-ford-service-manuals):

**Bug fixes:**
- Fixed broken wiring SVG fetching: corrected Ford API URL (`fordservicecontent.dealerconnection.com` → `fordservicecontent.com`)
- Fixed wiring page list handling: Ford's API now returns objects instead of strings for some sub-pages; both formats are handled correctly
- Sanitized output filenames for cross-platform compatibility

**Guided setup:**
- `FordManual.py` interactive wizard handles the entire workflow including dependency installation, parameter collection, and scraping
- `build_viewer.py` optional post-processing for offline viewing with path shortening

**Connector and wiring pages rewritten:**
- Upstream used Playwright to navigate PTS pages for connectors and wiring diagrams, which was frequently blocked by Akamai's bot detection
- Connectors and wiring SVGs are now fetched via Ford's API directly, bypassing Akamai
- Each connector is saved as a rich, self-contained HTML file with face SVG, pin table, terminal part numbers, and pigtail details

**Workshop illustration SVGs:**
- Hotspot illustration SVGs are automatically downloaded from Ford's CDN at the end of the workshop scrape
- CSS patched so text labels (`.sttxt`) are visible and callout overlays (`.stcallout`) are hidden
- HTML rewritten from Ford's `data-svg-path` divs to local `<object>` tags for fully offline viewing
- Downloads use `curl` to avoid Akamai TLS fingerprinting blocks
- Also available as a standalone Python script (`process_workshop_svgs.py`) for re-processing existing output

**Output format:**
- Default output is now HTML only (faster, better for browsing, works offline)
- `--pdf` and `--pdfonly` flags for PDF generation

**Resume support:**
- Already-downloaded files are skipped on re-run
- Works with both original and shortened filenames (via `path_mapping.json`)

**Switched from Yarn to npm** for broader compatibility — no `corepack` required.

## Common Issues

### Failed to log in with the provided cookies

Try re-collecting your cookies. Make sure you're copying the value **after** `Cookie: `, not the header name itself. Firefox users must enable the **Raw** toggle before copying.

If you're certain the cookies are correct, add `--noCookieTest` to skip validation.

### Looks like your PTS subscription has expired

Renew your subscription at [Motorcraft](https://www.motorcraftservice.com/Purchase/ViewProduct). This check can be skipped with `--noCookieTest`, but downloads will fail without a valid subscription.

### Expected cookie not found

This is a warning, not an error. If the scraper starts downloading successfully, it's fine. If not, re-collect your cookies.

### `ERR_HTTP2_PROTOCOL_ERROR`

Usually means invalid cookies or Akamai bot detection. Re-collect your cookies. If it persists, open an issue.

### `ERR_BAD_RESPONSE`

Usually means a field in your config is incorrect. Double-check your parameters against the DevTools network requests.

## FAQ

### Which vehicles does this work with?

All the ones we've tested:
- 1995 F-150
- 2002 Taurus
- 2006 Taurus/Sable
- 2008 Mustang
- 2020 MKZ
- 2022 F-150
- 2024 Ford Ranger Raptor (Brazil)
- 2025 Ford Maverick

### Will this work in my country/region?

Probably — we've had success across North America, South America, Europe, and Australia. The script downloads manuals in the language specified in your config. To change languages, update your PTS language setting, re-collect all parameters, and run again.

### How can I support this project?

Contributions via pull requests are welcome. Please:
- Keep everything typed (TypeScript)
- Use `npm` (not Yarn)
- Format with `npm run format` before submitting

### Can I get help/support?

Open a GitHub issue with the error and your config file. **Do not share your cookies** — they contain your session credentials.
