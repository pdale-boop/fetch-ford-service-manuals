import { WiringFetchPageParams } from "./savePage";
import { WiringTableOfContentsEntry } from "./fetchTableOfContents";
import { Page } from "playwright";
import fetchConnectorList from "./fetchConnectorList";
import client from "../client";
import { sanitizeName } from "../utils";
import { join, resolve } from "path";
import { writeFile, unlink } from "fs/promises";
import { existsSync } from "fs";
import { SaveOptions } from "../workshop/saveEntireManual";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchConnectorDetails(
  params: WiringFetchPageParams,
  cell: string,
  item: string
): Promise<any> {
  const req = await client({
    method: "GET",
    url: "https://www.fordservicecontent.com/Ford_Content/PublicationRuntimeRefreshPTS//wiring/GetConnectorDetails",
    params: {
      environment: params.environment,
      book: params.book,
      cell,
      bookType: params.bookType,
      contentmarket: params.contentmarket,
      contentlanguage: params.contentlanguage,
      item,
      LanguageCode: params.languageCode,
      fromPageBase: "https://www.fordtechservice.dealerconnection.com",
    },
  });
  return req.data;
}

async function fetchConnectorSvg(
  params: WiringFetchPageParams,
  cell: string,
  item: string,
  svgFilename: string
): Promise<string | null> {
  try {
    const req = await client({
      method: "GET",
      url: "https://www.fordservicecontent.com/Ford_Content/PublicationRuntimeRefreshPTS//wiring/GetConnectorImages",
      params: {
        environment: params.environment,
        book: params.book,
        cell,
        bookType: params.bookType,
        languageCode: params.languageCode,
        item,
        svgfilename: svgFilename,
        fromPageBase: "https://www.fordtechservice.dealerconnection.com",
      },
    });
    return req.data as string;
  } catch {
    return null;
  }
}

async function fetchPigtailDetails(
  params: WiringFetchPageParams,
  fpn: string
): Promise<any[]> {
  try {
    const req = await client({
      method: "GET",
      url: "https://www.fordservicecontent.com/Ford_Content/PublicationRuntimeRefreshPTS//wiring/GetPigtailsDetails",
      params: {
        environment: params.environment,
        book: params.book,
        bookType: params.bookType,
        contentmarket: params.contentmarket,
        contentlanguage: params.contentlanguage,
        Fpn: fpn,
        fromPageBase: "https://www.fordtechservice.dealerconnection.com",
      },
    });
    return req.data || [];
  } catch {
    return [];
  }
}

async function fetchServicePartNumber(
  params: WiringFetchPageParams,
  terminalPartNumber: string
): Promise<any> {
  try {
    const req = await client({
      method: "GET",
      url: "https://www.fordservicecontent.com/Ford_Content/PublicationRuntimeRefreshPTS//wiring/GetServicePartNumber",
      params: {
        environment: params.environment,
        book: params.book,
        bookType: params.bookType,
        contentmarket: params.contentmarket,
        contentlanguage: params.contentlanguage,
        Terminalpartnumber: terminalPartNumber,
        fromPageBase: "https://www.fordtechservice.dealerconnection.com",
      },
    });
    return req.data;
  } catch {
    return null;
  }
}

async function fetchTerminalPartSizes(
  params: WiringFetchPageParams,
  servicePartNumber: string
): Promise<any[]> {
  try {
    const req = await client({
      method: "GET",
      url: "https://www.fordservicecontent.com/Ford_Content/PublicationRuntimeRefreshPTS//wiring/GetTerminalPartSizes",
      params: {
        environment: params.environment,
        book: params.book,
        bookType: params.bookType,
        contentmarket: params.contentmarket,
        contentlanguage: params.contentlanguage,
        Servicepartnumber: servicePartNumber,
        fromPageBase: "https://www.fordtechservice.dealerconnection.com",
      },
    });
    return req.data || [];
  } catch {
    return [];
  }
}

async function fetchGifAsBase64(wptNumber: string): Promise<string | null> {
  try {
    const req = await client({
      method: "GET",
      url: `https://www.fordservicecontent.com/pubs/content/connectors/images/WPT${wptNumber}.gif`,
      responseType: "arraybuffer",
    });
    const b64 = Buffer.from(req.data).toString("base64");
    return `data:image/gif;base64,${b64}`;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// CSS
// ---------------------------------------------------------------------------

const CONNECTOR_CSS = `
body { font-family: Arial, sans-serif; font-size: 11px; margin: 0; padding: 10px; }
h2 { font-size: 14px; margin: 0 0 6px 0; }
.header-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
.header-table th, .header-table td { border: 1px solid #999; padding: 4px 8px; text-align: center; }
.header-table th { background: #ccc; font-weight: bold; }
.face-pin-row { display: flex; gap: 16px; margin-bottom: 12px; align-items: flex-start; }
.face-col { flex: 0 0 280px; }
.face-col svg { width: 280px; height: auto; }
.pin-col { flex: 1; }
.pintable { width: 100%; border-collapse: collapse; font-size: 11px; }
.pintable th { background: #ccc; border: 1px solid #999; padding: 4px 6px; text-align: center; }
.pintable td { border: 1px solid #999; padding: 3px 6px; }
.pintable tr:nth-child(even) td { background: #eee; }
.section-label { font-weight: bold; margin: 10px 0 4px 0; font-size: 12px; }
.termtable { width: 60%; border-collapse: collapse; font-size: 11px; margin-bottom: 12px; }
.termtable th { background: #ccc; border: 1px solid #999; padding: 4px 6px; }
.termtable td { border: 1px solid #999; padding: 3px 6px; }
.pigtail-block { display: flex; gap: 12px; border: 1px solid #999; padding: 8px; margin-bottom: 8px; align-items: flex-start; }
.pigtail-img { flex: 0 0 140px; }
.pigtail-img img { max-width: 140px; max-height: 120px; }
.pigtail-kit-header { font-weight: bold; margin-bottom: 4px; }
.pigtail-info { flex: 1; font-size: 11px; line-height: 1.8; }
`;

// ---------------------------------------------------------------------------
// HTML builders
// ---------------------------------------------------------------------------

function pinTableHtml(pins: any[]): string {
  if (!pins.length)
    return "<p style='color:#999;font-size:10px'>(no pin data)</p>";
  const rows = pins
    .map((p: any) => {
      const circuit = p.CircuitNumber
        ? `${p.CircuitNumber} (${p.Color})`
        : "*";
      const gauge = p.Guage || p.Gauge || "*";
      const func = p.Function || "Not Used";
      return `<tr><td>${p.Cavity || ""}</td><td>${circuit}</td><td>${gauge}</td><td>${func}</td><td>${p.Qualifier || ""}</td></tr>`;
    })
    .join("");
  return `<table class="pintable">
<thead><tr><th>Pin</th><th>Circuit</th><th>Gauge</th><th>Circuit Function</th><th>Qualifier</th></tr></thead>
<tbody>${rows}</tbody></table>`;
}

async function buildConnectorHtml(
  params: WiringFetchPageParams,
  cell: string,
  connectorData: any,
  connectorName: string,
  faceView: string
): Promise<string> {
  const c = connectorData.Connector;
  if (!c) {
    return `<!DOCTYPE html><html><body><h2>${connectorName}</h2><p>No data available.</p></body></html>`;
  }

  const faceList: any[] = c.Faces?.FaceList || [];
  const pinList: any[] = c.Pins?.PinList || [];
  const harnessIds = faceList
    .map((f: any) => f.HarnessId)
    .filter(Boolean)
    .join(", ");
  const isMultiFace = faceList.length === 2;

  // Fetch SVG for first face
  let svgHtml = "<p style='color:#999'>(face diagram unavailable)</p>";
  if (faceList.length > 0 && faceList[0].File) {
    const svg = await fetchConnectorSvg(params, cell, faceView, faceList[0].File);
    if (svg) svgHtml = svg;
  }

  // Collect unique terminal part numbers
  const allPins: any[] =
    pinList.length > 0
      ? pinList
      : faceList.flatMap((f: any) => f.Pins?.PinList || []);

  const seenTp = new Set<string>();
  const tpNumbers: string[] = [];
  for (const p of allPins) {
    const raw: string = p.TerminalPartNumber || "";
    for (const part of raw.replace(/\*/g, "").split("|")) {
      const t = part.trim();
      if (t && t !== "N/A" && t !== "NA" && t !== "NULL" && !seenTp.has(t)) {
        seenTp.add(t);
        tpNumbers.push(t);
      }
    }
  }

  // Fetch terminal part rows
  interface TermRow { terminal: string; service: string; size: string; }
  const terminalRows: TermRow[] = [];
  for (const tp of tpNumbers) {
    const svcData = await fetchServicePartNumber(params, tp);
    const svcList = svcData?.ServicePart?.ServicePartList || [];
    if (svcList.length > 0) {
      for (const svc of svcList) {
        const spn = `${svc.Prefix}-${(svc.Base || "").trim()}-${svc.Suffix}`;
        const sizes = await fetchTerminalPartSizes(params, spn);
        if (sizes.length > 0) {
          for (const sz of sizes) {
            terminalRows.push({ terminal: tp, service: spn, size: sz.Size || "" });
          }
        } else {
          terminalRows.push({ terminal: tp, service: spn, size: "" });
        }
      }
    } else {
      terminalRows.push({ terminal: tp, service: "Not Available", size: "" });
    }
  }

  // Fetch pigtail data
  interface PigtailRow {
    number: string; gauge: string; material: string;
    cavities: string; servicePart: string; apps: string; imgB64: string | null;
  }
  const pigtailRows: PigtailRow[] = [];
  for (const face of faceList) {
    if (!face.Fpn) continue;
    const pigs = await fetchPigtailDetails(params, face.Fpn);
    for (const pg of pigs) {
      if (pg.EUProductId != null) continue;
      const imgB64 = pg.Number ? await fetchGifAsBase64(pg.Number) : null;
      pigtailRows.push({
        number: pg.Number || "",
        gauge: pg.Gauge || "",
        material: pg.Material || "",
        cavities: pg.Cavities || "",
        servicePart: pg.ServicePart || "",
        apps: (pg.ApplicationsName || "").replace(/\|/g, "<br>&nbsp;&nbsp;"),
        imgB64,
      });
    }
  }

  const hasPigtails = pigtailRows.length > 0;

  let html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>${CONNECTOR_CSS}</style></head><body>
<h2>${c.CNumber || connectorName} — ${c.Description || ""}</h2>
<table class="header-table">
  <thead><tr>
    <th>Connector</th><th>Description</th><th>Color</th>
    <th>Harness</th><th>Base Part #</th><th>Service Pigtail</th>
  </tr></thead>
  <tr>
    <td>${c.CNumber || ""}</td>
    <td>${c.Description || ""}</td>
    <td>${c.Color || ""}</td>
    <td>${harnessIds}</td>
    <td>${c.BasePartNumber || ""}</td>
    <td>${hasPigtails ? "See Below" : "Not Available"}</td>
  </tr>
</table>
`;

  if (!isMultiFace) {
    const pins = pinList.length > 0 ? pinList : faceList[0]?.Pins?.PinList || [];
    html += `<div class="face-pin-row">
  <div class="face-col">${svgHtml}</div>
  <div class="pin-col">
    <div class="section-label">Pin Information</div>
    ${pinTableHtml(pins)}
  </div>
</div>\n`;
  } else {
    html += `<div class="face-pin-row">
  <div class="face-col">${svgHtml}</div>
  <div class="pin-col">\n`;
    for (const face of faceList) {
      const facePins = face.Pins?.PinList || [];
      html += `<div class="section-label">${face.Gender || "Face"} — Harness ${face.HarnessId || ""}</div>`;
      html += pinTableHtml(facePins);
      html += "<br/>\n";
    }
    html += `  </div>
</div>\n`;
  }

  if (terminalRows.length > 0) {
    html += `<div class="section-label">Terminal Part Numbers</div>
<table class="termtable">
  <thead><tr><th>Terminal Part #</th><th>Service Part #</th><th>Size</th></tr></thead>
  <tbody>
`;
    for (const row of terminalRows) {
      html += `    <tr><td>${row.terminal}</td><td>${row.service}</td><td>${row.size}</td></tr>\n`;
    }
    html += `  </tbody></table>\n`;
  }

  if (hasPigtails) {
    html += `<div class="section-label">Available Pigtail Kits</div>\n`;
    for (const pg of pigtailRows) {
      const imgHtml = pg.imgB64
        ? `<img src="${pg.imgB64}"/>`
        : `<span style="color:#999;font-style:italic;font-size:10px">no image</span>`;
      html += `<div class="pigtail-block">
  <div class="pigtail-img">
    <div class="pigtail-kit-header">WPT-${pg.number}</div>
    ${imgHtml}
  </div>
  <div class="pigtail-info">
    Service Part Number: <b>${pg.servicePart}</b><br>
    Gauge: <b>${pg.gauge}</b><br>
    Pin material: <b>${pg.material}</b><br>
    Cavities: <b>${pg.cavities}</b><br><br>
    Vehicle Uses:<br>&nbsp;&nbsp;<b>${pg.apps}</b>
  </div>
</div>\n`;
    }
  }

  html += `</body></html>`;
  return html;
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export default async function saveConnector(
  params: WiringFetchPageParams,
  doc: WiringTableOfContentsEntry & { Type: "Connectors" },
  browserPage: Page,
  folderPath: string,
  options: SaveOptions = { savePDF: false, pdfOnly: false, ignoreSaveErrors: false }
): Promise<void> {
  const connectors = await fetchConnectorList(params);

  await writeFile(
    join(folderPath, "connectors.json"),
    JSON.stringify(connectors, null, 2)
  );

  for (const connector of connectors) {
    console.log(`Saving connector ${connector.Desc} (${connector.Name})...`);

    let title = sanitizeName(connector.Desc) + " - " + connector.Name;
    if (title.length > 200) {
      title = title.slice(0, 150) + " (truncated) - " + connector.Name;
    }

    const htmlPath = join(folderPath, title + ".html");
    const pdfPath = join(folderPath, title + ".pdf");

    // Skip if already downloaded
    if (options.pdfOnly) {
      if (existsSync(pdfPath)) {
        console.log(`Skipping already downloaded: ${connector.Name}`);
        continue;
      }
    } else {
      if (existsSync(htmlPath)) {
        console.log(`Skipping already downloaded: ${connector.Name}`);
        continue;
      }
    }

    try {
      const data = await fetchConnectorDetails(params, doc.Number, connector.FaceView);

      // Always build and save rich HTML
      const html = await buildConnectorHtml(
        params,
        doc.Number,
        data,
        connector.Name,
        connector.FaceView
      );
      await writeFile(htmlPath, html);

      if (options.savePDF) {
        await browserPage.goto("file:///" + resolve(htmlPath));
        await browserPage.pdf({ path: pdfPath, landscape: true });

        if (options.pdfOnly) {
          await unlink(htmlPath);
        }
      }
    } catch (e) {
      console.error(
        `Error saving connector ${connector.Desc} (${connector.Name}):`,
        e
      );
    }
  }
}
