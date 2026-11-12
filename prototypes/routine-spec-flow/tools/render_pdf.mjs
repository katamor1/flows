// Visual QA fallback after export from desktop Microsoft Word.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const [pdfPath, outputDir, packages] = process.argv.slice(2);
if (!pdfPath || !outputDir || !packages) throw Error('Usage: render_pdf.mjs file.pdf output_dir bundled_node_modules');
const require = createRequire(path.join(packages, 'package.json'));
const canvas = require('@napi-rs/canvas');
Object.assign(globalThis, { DOMMatrix: canvas.DOMMatrix, ImageData: canvas.ImageData, Path2D: canvas.Path2D });
const pdfjsPath = require.resolve('pdfjs-dist/legacy/build/pdf.mjs');
const pdfjs = await import(pathToFileURL(pdfjsPath).href);
const pdf = await pdfjs.getDocument({ data: new Uint8Array(fs.readFileSync(pdfPath)), useSystemFonts: true, disableFontFace: true }).promise;
fs.mkdirSync(outputDir, {recursive:true});
const summary=[];
for (let i=1;i<=pdf.numPages;i++) {
  const page=await pdf.getPage(i);
  const viewport=page.getViewport({scale:2.1});
  const surface=canvas.createCanvas(Math.ceil(viewport.width),Math.ceil(viewport.height));
  await page.render({canvasContext:surface.getContext('2d'),viewport,canvas:surface}).promise;
  const filename=path.join(outputDir,`page-${i}.png`);
  fs.writeFileSync(filename,surface.toBuffer('image/png'));
  const text=(await page.getTextContent()).items.map(x=>x.str).join(' ');
  summary.push({page:i,file:`page-${i}.png`,characters:text.length,start:text.slice(0,160),end:text.slice(-170)});
}
fs.writeFileSync(path.join(outputDir,'render-summary.json'),JSON.stringify({renderer:'Microsoft Word PDF export + PDF.js',pages:summary},null,2));
console.log(JSON.stringify({pageCount:pdf.numPages,pages:summary},null,2));
