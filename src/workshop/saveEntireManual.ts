import { mkdir, writeFile, unlink } from "fs/promises";
import { existsSync, readFileSync } from "fs";
import { join, resolve, relative } from "path";
import fetchManualPage, { FetchManualPageParams } from "./fetchManualPage";
import client from "../client";
import { Page } from "playwright";
import { CLIArgs } from "../processCLIArgs";
import saveStream, { sanitizeName } from "../utils";

export type SaveOptions = Pick<CLIArgs, "savePDF" | "pdfOnly" | "ignoreSaveErrors">;

export default async function saveEntireManual(
  path: string,
  toc: any,
  fetchPageParams: FetchManualPageParams,
  browserPage: Page,
  options: SaveOptions,
  pathMapping?: Record<string, string>,
  outputRoot?: string
) {
  const exploded = Object.entries(toc);

  for (let i = 0; i < exploded.length; i++) {
    const [name, docID] = exploded[i];

    if (typeof docID === "string" && docID.length > 0) {
      // download and save document
      if (docID.startsWith("http") && docID.includes(".pdf")) {
        console.log(`Downloading manual PDF ${name} ${docID}`);

        try {
          const pdfReq = await client({
            url: docID,
            responseType: "stream",
          });

          const filePath = join(
            path,
            `/${docID.slice(docID.lastIndexOf("/"))}`
          );
          await saveStream(pdfReq.data, filePath);
        } catch (e) {
          console.error(`Error saving file ${name} with url ${docID}: ${e}`);
        }
        continue;
      } else if (docID.includes("/")) {
        console.error(`Skipping relative path ${docID} for name ${name}`);
        continue;
      }

      console.log(`Downloading manual page ${name} (docID: ${docID})`);
      let filename = sanitizeName(name);
      if (filename.length > 200) {
        filename =
          filename.slice(0, 254 - 19 - docID.length) + ` (${docID} truncated)`;
        console.log(`-> Truncating filename, learn more in the README`);
      }

      const htmlPath = resolve(join(path, `/${filename}.html`));
      if (existsSync(htmlPath)) {
        console.log(`Skipping already downloaded: ${name}`);
        continue;
      }
      // Check shortened path from path_mapping.json
      if (pathMapping && outputRoot) {
        const relPath = relative(outputRoot, htmlPath).replace(/\\/g, "/");
        const mappedRel = pathMapping[relPath];
        if (mappedRel) {
          const mappedAbs = resolve(join(outputRoot, mappedRel));
          if (existsSync(mappedAbs)) {
            console.log(`Skipping already downloaded (shortened): ${name}`);
            continue;
          }
        }
      }

      try {
        const pageHTML = await fetchManualPage({
          ...fetchPageParams,
          searchNumber: docID,
        });

        // Always save HTML first
        await writeFile(htmlPath, pageHTML);

        if (options.savePDF) {
          const pdfPath = resolve(join(path, `/${filename}.pdf`));
          await browserPage.goto(`file://${htmlPath}`, { waitUntil: "load" });
          await browserPage.pdf({ path: pdfPath });

          // pdfOnly: delete HTML after PDF generation
          if (options.pdfOnly) {
            await unlink(htmlPath);
          }
        }
      } catch (e) {
        if (options.ignoreSaveErrors) {
          console.error(
            `Continuing to download after error with ${name} (docID ${docID}):`,
            e
          );
        } else {
          console.error(
            `Encountered an error downloading ${name} (docID ${docID})`
          );
          throw e;
        }
      }
    } else {
      // create folder and traverse
      const newPath = join(path, sanitizeName(name));

      try {
        await mkdir(newPath, { recursive: true });
      } catch (e) {
        if ((e as any).code === "EEXIST") {
          console.log(
            `Not creating folder ${newPath} because it already exists.`
          );
        }
      }

      await saveEntireManual(
        newPath,
        docID,
        fetchPageParams,
        browserPage,
        options,
        pathMapping,
        outputRoot
      );
    }
  }
}
