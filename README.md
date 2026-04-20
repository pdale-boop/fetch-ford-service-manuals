# fetch-ford-service-manuals

Downloads HTML (and optionally PDF) versions of Ford Service Manuals from PTS.

Bought a 72-hour subscription to Ford's service manuals and want to save it permanently?
Here's the repo for you.

These manuals are copyrighted by Ford, so don't share them!

> **Fork notes:** This is a fork of [iamtheyammer/fetch-ford-service-manuals](https://github.com/iamtheyammer/fetch-ford-service-manuals) with bug fixes and improvements. See [Changes from upstream](#changes-from-upstream) for details.

## Table of Contents

- [Usage](#usage)
- [Results (what do I get out of this?)](#results)
- [Changes from upstream](#changes-from-upstream)
- [Common Issues](#common-issues)
- [FAQ](#faq)

## Usage

Getting this to work currently requires some knowledge of browser DevTools.
If you're not sure how to use them, ask a friend who does.

This script uses [`playwright`](https://github.com/microsoft/playwright), a headless browser interop library, to optionally save documents as PDFs. By default, pages are saved as HTML only, which is faster and produces better results.

### Browser

Firefox and Chrome both work. If using Firefox, there is one critical difference when copying cookies — see the cookie step below.

### (Avoid) Using Windows

While this script has been verified to work on Windows natively (see [issue #6](https://github.com/iamtheyammer/fetch-ford-service-manuals/issues/6)), it's recommended to run it in WSL. Running in WSL makes installing things like Git and Node far easier.

WSL is a way to run Linux (Ubuntu is recommended for this project) in tandem with Windows. It's far faster than a virtual machine but still uses the real Linux kernel. Learn more and see install instructions [here](https://learn.microsoft.com/en-us/windows/wsl/install).

### Set up Node (>16.3) and Yarn

1. Install Node.js 16.3 or newer (with `corepack`)
2. Run `corepack enable`

### Get code and dependencies

1. Clone this repository with `git clone https://github.com/pdale-boop/fetch-ford-service-manuals.git`, and enter the repository's directory (likely with `cd fetch-ford-service-manuals`)
   - Previously cloned? Run `git pull` to get up to date!
   - If `git pull` does **not** say `Already up to date.`, run the next 2 steps to ensure your dependencies are up-to-date.
   - If you get an error while pulling, try running `git stash`, `git pull`, then `git stash apply` to un-stash your files.
2. Run `yarn` to download dependencies
3. Run `yarn playwright-setup` to download and set up Playwright

### Set up PTS

> **Note:** Ford updates the PTS interface periodically. The visual layout may not match screenshots or descriptions exactly. If something looks different, focus on the network requests in DevTools — those are more reliable than the UI description.

1. If you haven't, purchase a PTS subscription from [here](https://www.motorcraftservice.com/Purchase/ViewProduct). The 72-hour subscription is fine.
2. Once purchased, go to PTS: click [here](https://www.motorcraftservice.com/MySubscriptions), then click on your subscription title. ![how to open PTS](img/open-pts.png)
3. Once PTS opens, navigate to your car.
   - On the left, choose *By Year & Model*, then select your car's year and model.
     - In some countries, *By Year & Model* may not be available. In that case, choose *By VIN* and enter your VIN.
   - Press GO once selected.

### Set up template files

1. In `templates/`, make a copy of `cookieString.txt.template` named `cookieString.txt`
2. Clear the contents of `cookieString.txt`
3. In `templates/`, make a copy of `params.json.template` named `params.json`

### **2003 or newer:** Get data for your car

**If your vehicle was made BEFORE 2003, use [these](#2002-or-older-get-data-for-your-car) instructions.**

This script requires some data about your car that's not available in the PTS GUI in order to fetch the correct manual.

1. Open DevTools, and navigate to the Network tab.
2. Click on the Workshop tab in PTS.
3. Filter for the one POST to `https://www.fordservicecontent.com/Ford_Content/PublicationRuntimeRefreshPTS//publication/prod_1_3_372022/TreeAndCover/workshop/32/~WSLL/{some numbers here}`. It should look similar to the request in [this photo](img/workshop-request.png).
4. Click on that request, and look at the sent form data (i.e. the payload).
5. Open [`templates/params.json`](templates/params.json), and copy/paste information from that request into the values of the JSON `.workshop` field.
   - **Do not add fields. Only change values.**
   - Copy-and-paste values to ensure you don't add typos.
   - Change the values to match. You probably won't need to change anything under the line break.
   - If you can't find the Book Title or Wiring Book Title, look in the query string parameters. **Do not leave them blank!**
6. Get your wiring data: follow instructions [here](#all-vehicles-get-wiring-data).

### **2002 or older:** Get data for your car

**If your vehicle was made IN 2003 or LATER, use [these](#2003-or-newer-get-data-for-your-car) instructions.**

1. Click on the Workshop tab in PTS.
   - You may see a couple manuals, often a "Workshop Manual" and a "Body Collision Repair Manual". You can use this application to download both -- just repeat the process for each manual, remembering to change the output path for each.
   - To proceed, click on either manual.
2. In the sidebar, right click on "Alphabetical Index", and click "Copy Link Address" (see [picture](img/pre-2003-index.jpg)).
3. Open [`templates/params.json`](templates/params.json), and change only:
   - `workshop.modelYear` to the year of your car
   - `pre_2003.alphabeticalIndexURL` to the URL you copied in step 2
   - The rest will be filled in later
   - Copy-and-paste values to ensure you don't add typos.
4. Open DevTools in your browser.
5. Get your wiring data: follow instructions [here](#all-vehicles-get-wiring-data).

### **All Vehicles:** Get wiring data

1. Clear the DevTools Network pane (click on the trash can or circle with a line through it)
2. Click the Wiring tab at the top of PTS.
3. Filter for the GET request to this URL: `https://www.fordservicecontent.com/Ford_Content/PublicationRuntimeRefreshPTS//wiring/TableofContent` (there are query params at the end, that's ok). It should look similar to the request in [this photo](img/wiring-request.png).
   - Make sure that "Content" in the url is SINGULAR: `TableOfContent`, not `TableOfContent`**`s`**
4. Copy the `environment`, `bookType`, and `languageCode` query params into `.wiring` in `params.json`.
   - If `WiringBookTitle` or `WiringBookCode` are still missing, you may need to select a wiring manual. After selecting a manual, you'll find these in another request to `https://www.fordtechservice.dealerconnection.com/wiring/TableOfContents` (with some query params at the end):
   - `booktitle` → `WiringBookTitle`
   - `book` → `WiringBookCode`
   - Use these two requests to fill in `params.json` as best as you can.
5. Save `params.json`.
6. Filter for the GET request to this URL: `https://www.fordtechservice.dealerconnection.com/wiring/TableOfContents` (there are query params at the end, that's ok).
   - Unlike last time, make sure "Contents" in the url is PLURAL: `TableOfContent`**`s`**, not `TableOfContent`
7. Go to the request headers and find the "Cookie:" entry.
8. Copy the cookies from this request (triple-click to select all) and paste into `templates/cookieString.txt`.
   - Do **not** include the name of the header (`cookieString.txt` should **not** include `Cookie:` for example.)
   - **Firefox users:** You MUST enable the *Raw* toggle in the top right of the Request Headers panel before copying. If you skip this, Firefox reformats the cookies and you'll get an invalid character error when the script runs.
9. Save `cookieString.txt`.

### Download the manual!

Run the downloader with:

```
yarn start -c templates/params.json -s templates/cookieString.txt -o /directory/where/you/want/the/downloaded/manual/
```

By default, all pages are saved as **HTML only**. This is faster and produces better output than PDF for browsing.

To also generate PDFs (and keep both):
```
yarn start -c templates/params.json -s templates/cookieString.txt -o /path/to/output/ --pdf
```

To generate PDFs only (HTML is deleted after PDF generation):
```
yarn start -c templates/params.json -s templates/cookieString.txt -o /path/to/output/ --pdfonly
```

**You will likely need to run this 2-3 times to get all files.** Ford's servers occasionally return timeouts or errors on individual pages. The script supports **automatic resume** — already-downloaded files are skipped on re-run, so just run the same command again until the output stabilizes. Add `--ignoreSaveErrors` if you want the script to continue past errors rather than stopping:

```
yarn start -c templates/params.json -s templates/cookieString.txt -o /path/to/output/ --ignoreSaveErrors
```

Make sure that the directory for the downloaded manual is empty the first time you run — it'll have lots of subfolders.

You can get more param information by running `yarn start --help`.

It can take a little while! On a fast computer with a fast internet connection, and more importantly a fast disk drive, over 15 minutes to download the manuals for the 2005 Taurus. Be patient!

Also, the resulting folder is pretty sizeable. The folder for the 2005 Taurus was about 300mb, and the F150 folder was a couple gigabytes.

Having issues? See [Common Issues](#common-issues) or [FAQ](#faq).

## Results

This bot downloads the **entire** workshop manual and **all** wiring diagrams for the vehicle you set up.

### **All vehicles:** Wiring diagrams

Wiring diagrams will be in `outputpath/Wiring`. There's also a `toc.json` file with the table of contents for the wiring diagrams.

#### Connector Views & Component Location Charts

If you have a `Wiring/Connector Views` folder, each connector is saved as a self-contained HTML file including:

- Face diagram (SVG)
- Pin table with circuit numbers, gauge, function, and qualifier
- Terminal part numbers with service part numbers and sizes
- Available pigtail kits with images and vehicle application info

There's also a `Connectors.csv` file that tells you where to find every connector in the car:

| Connector ID | Connector                            | Connector Location Views Page Number | Grid Reference | Location in Vehicle |
|--------------|--------------------------------------|--------------------------------------|----------------|---------------------|
| C168A        | 10R80 Transmission (2.7L)            | 29                                   | F5             | Transmission        |
| C1840        | Line Pressure Control (LPC) solenoid | 34                                   | E8             | Inside transmission |

### **2003 or newer:** Workshop manual

The folder structure in the output directory will mimic the structure on PTS, so if a file has a path like `1: General Information -> 00: Service Information -> 100-00 General Information -> About this Manual`, it will be in the folder `outputpath/1: General Information/00: Service Information/100-00 General Information/About this Manual.html`.

The `cover.html` file contains the book's cover and a table of contents. The `toc.json` file contains the computer-readable table of contents.

#### Truncated filenames

Most operating systems limit filenames to 255 bytes. For filenames over 200 characters (which are fairly rare), the downloader will truncate the name and add ` (docID truncated)` to the end.

If you're having trouble finding a document with a long name, search for it in `toc.json` by its docID.

### **2002 or older:** Workshop manual

Vehicles from 2002 or older have a different structure, so this tool uses the alphabetical index. The output is a flat structure with all pages in the output folder.

You can browse the manual by opening `outputpath/AA_Table_Of_Contents.html` — all the links work except for the letters at the top.

Special files:
- `AA_Table_Of_Contents.html` — processed table of contents where all links work
- `AAA_alphabeticalIndex.json` — JSON version of all links in the alphabetical index
- `AAA_originalTableOfContents.html` — original unmodified table of contents

## Changes from upstream

This fork includes the following fixes and improvements over [iamtheyammer/fetch-ford-service-manuals](https://github.com/iamtheyammer/fetch-ford-service-manuals):

**Bug fixes:**
- Fixed broken wiring SVG fetching: corrected Ford API URL (`fordservicecontent.dealerconnection.com` → `fordservicecontent.com`)
- Fixed wiring page list handling: Ford's API now returns objects instead of strings for some sub-pages; both formats are handled correctly

**Connector pages rewritten:**
- Connectors are now fetched via Ford's API directly (`GetConnectorDetails`, `GetConnectorImages`, `GetPigtailsDetails`, `GetServicePartNumber`, `GetTerminalPartSizes`) rather than driving a headless browser to a live PTS page
- Each connector is saved as a rich, self-contained HTML file including the face SVG, pin table, terminal part numbers with sizes, and pigtail kit details with images
- No longer dependent on Playwright for connector pages in default mode

**Output format:**
- Default output is now HTML only (faster, better for browsing, works offline)
- `--pdf` flag generates PDFs alongside HTML
- `--pdfonly` flag generates PDFs and removes HTML afterward
- Removed `--saveHTML` and `--htmlOnly` flags (superseded by new defaults)

**Resume support:**
- Already-downloaded files are skipped automatically on re-run, so interrupted downloads can be safely resumed

**Added utility:**
- `src/patchConnectorSvgs.ts` — standalone script to retroactively patch face SVGs into connector HTML files from a previous run that had missing diagrams

## Common Issues

### Failed to log in with the provided cookies.

When the script starts, it tries to sign in to PTS to verify that your cookies are working. If this fails, you may not be able to fetch manuals.

Try to [re-collect cookies](#how-do-i-re-collect-my-cookies) and make sure you're using the correct ones. If you're 100% sure that your cookies are correct, you can add `--noCookieTest` to the command.

### Looks like your PTS subscription has expired

Your subscription has expired. You'll need to renew it to download manuals.

This check can also be skipped with `--noCookieTest`, but without a subscription you won't be able to download manuals.

### Expected cookie `...` not found in cookie string. This may affect functionality.

The script auto-checks your cookie file against a list of expected cookies. If it can't find one of the expected cookies, it'll warn you (the script does not stop if this prints out).

If you see this message and the script starts downloading manuals, let it go — it's just a warning. If you see the message and everything downloads fine, please open a GitHub issue so we can fix it for others.

If you're having issues, try [re-collecting your cookies](#how-do-i-re-collect-my-cookies).

### `ERR_HTTP2_PROTOCOL_ERROR`

This can mean that your cookies are invalid or that Ford (actually Akamai) has detected a headless browser.

First, try [re-collecting your cookies](#how-do-i-re-collect-my-cookies). If you still have issues, [reach out](#can-i-get-helpsupport).

### `ERR_BAD_RESPONSE`

This usually means that one of the fields in your `params.json` file is incorrect. Check that all the fields are correct, and if you're still having issues, open a GitHub issue.

## FAQ

### Which vehicles does this work with?

All the ones we've tested. Just for fun:

- 1995 F-150
- 2002 Taurus
- 2006 Taurus/Sable
- 2008 Mustang
- 2020 MKZ
- 2022 F-150
- 2024 Ford Ranger Raptor (Brazil)
- 2025 Ford Maverick

All worked!

### How do I re-collect my cookies?

To re-collect cookies, follow the instructions in [this](#all-vehicles-get-wiring-data) set of instructions, making sure you:

- Remove the `Cookie: ` part of the header, if you copied it
- **Firefox users:** Enable the *Raw* toggle in the top right of Request Headers before copying — this is mandatory or you'll get invalid character errors
- Added a `; ` between the first paste and second paste if combining multiple requests

If you're still having trouble, [reach out](#can-i-get-helpsupport).

### Will this work in my country/region?

Probably! We've had success all across North America, South America, Europe, and Australia.

While the script is in English, it will download manuals in the language specified in `params.json`. Note that Ford must have the manual available in the requested language.

To download manuals in a specific language, **change your PTS language**, re-collect **all** parameters, and run the download again.

### How can I support this project?

As Ford continues to change how manuals are accessed, this project requires continuous maintenance.

Contributions via pull requests are welcome. For the highest chance of getting your PR merged, please:

- Keep everything typed — this project is 100% TypeScript
- Keep using Yarn berry (no `node_modules` folder)
- Format your code with `yarn format` before submitting

### Can I get help/support?

Open a GitHub issue with the error you're getting along with your `params.json`. Do **not** share your `cookieString.txt` publicly — it contains your session credentials.

### Why did you make this?

To have a permanent offline copy of the service manual for a vehicle we're actively modifying.

### Why do you fetch pages one-at-a-time?

Two reasons. Firstly, we don't want to trigger Akamai rate limiting (a ton of parallel requests would absolutely get us blocked). Secondly, it was easier to code synchronously.
