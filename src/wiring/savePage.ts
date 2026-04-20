import { Page } from "playwright";
import { JSDOM } from "jsdom";
import fetchPageList from "./fetchPageList";
import {
  WiringFetchParams,
  WiringTableOfContentsEntry,
} from "./fetchTableOfContents";
import fetchSvg from "./fetchSvg";
import { join, resolve } from "path";
import { writeFile, unlink } from "fs/promises";
import { existsSync, readdirSync } from "fs";
import { sanitizeName } from "../utils";
import fetchBasicPage from "./fetchBasicPage";
import { SaveOptions } from "../workshop/saveEntireManual";

export interface WiringFetchPageParams extends WiringFetchParams {
  vehicleId: string;
  country: string;
}

export default async function savePage(
  params: WiringFetchPageParams,
  doc:
    | (WiringTableOfContentsEntry & { Type: "Page" })
    | (WiringTableOfContentsEntry & { Type: "BasicPage" }),
  browserPage: Page,
  folderPath: string,
  options: SaveOptions = { savePDF: false, pdfOnly: false, ignoreSaveErrors: false }
): Promise<void> {
  const pageList = await fetchPageList({
    ...params,
    cell: doc.Number,
    title: doc.Title,
    page: "1",
  });

  await writeFile(
    join(folderPath, "pageList.json"),
    JSON.stringify(pageList, null, 2)
  );

  // Read directory once so skip checks don't re-stat on every page
  const existingFiles = readdirSync(folderPath);

  for (const subPage of pageList) {
    console.log(`Saving page ${subPage} of ${doc.Title}...`);

    if (typeof subPage !== "string") {
      // Ford API returned object instead of string - extract cell/page and treat as SVG page
      const cell = (subPage as any).cell as string;
      const page = (subPage as any).page as string;
      if (!cell || !page) {
        console.error("Unrecognized subPage format:", JSON.stringify(subPage));
        continue;
      }
      const svgPath = join(folderPath, `${cell}_${page}.svg`);
      const pdfPath = join(folderPath, `${cell}_${page}.pdf`);

      // Skip if already downloaded
      if (options.pdfOnly) {
        if (existsSync(pdfPath)) {
          console.log(`Skipping already downloaded: ${cell}_${page}`);
          continue;
        }
      } else {
        if (existsSync(svgPath)) {
          console.log(`Skipping already downloaded: ${cell}_${page}`);
          continue;
        }
      }

      const svg = await fetchSvg(
        cell, page, params.environment, params.vehicleId,
        params.book, params.languageCode
      );
      await writeFile(svgPath, svg);

      if (options.savePDF) {
        await browserPage.goto(`file:///${resolve(svgPath)}`);
        await browserPage.pdf({ path: pdfPath, landscape: true });

        if (options.pdfOnly) {
          await unlink(svgPath);
        }
      }
      continue;
    }

    // String subPage: final filename is unknown until after SVG fetch (title gets appended).
    // Use the directory snapshot to check for any existing file starting with this subPage.
    const svgBaseName = subPage;
    if (options.pdfOnly) {
      if (existingFiles.some(f => f.startsWith(svgBaseName) && f.endsWith(".pdf"))) {
        console.log(`Skipping already downloaded: ${svgBaseName}`);
        continue;
      }
    } else {
      if (existingFiles.some(f => f.startsWith(svgBaseName) && f.endsWith(".svg"))) {
        console.log(`Skipping already downloaded: ${svgBaseName}`);
        continue;
      }
    }

    const svg = await fetchSvg(
      doc.Number,
      subPage,
      params.environment,
      params.vehicleId,
      params.book,
      params.languageCode
    );

    // Parse the SVG into a DOM for manipulation
    const dom = new JSDOM(svg);
    const svgElement = dom.window.document.querySelector("svg");
    if (!svgElement) {
      console.error(
        `No SVG element found in Wiring SVG for ${doc.Title} ${subPage}`
      );
      continue;
    }

    svgElement.setAttribute("xmlns", "http://www.w3.org/2000/svg");

    let title = subPage;

    const headerElement = dom.window.document.getElementById("Header");
    if (headerElement) {
      const child = headerElement.firstElementChild;
      if (child && child.textContent) {
        title += ` ${sanitizeName(child.textContent)}`;
      }
    }

    const svgString = dom.serialize();

    // Save the SVG
    const svgPath = join(folderPath, `${title}.svg`);
    await writeFile(svgPath, svgString);

    if (options.savePDF) {
      const finalPdfPath = join(folderPath, `${title}.pdf`);
      await browserPage.goto(`file:///${resolve(svgPath)}`);
      await browserPage.pdf({ path: finalPdfPath, landscape: true });

      if (options.pdfOnly) {
        await unlink(svgPath);
      }
    }
  }
}
