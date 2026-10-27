// Prints guia.html to guia-6-agentes-ia.pdf (and phone/desktop previews with --shots).
// Google Fonts requests are answered from ../carrusel-6-agentes/fonts so it works offline.
// Usage: node render-pdf.js [--shots]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const FONTS = path.join(__dirname, '..', 'carrusel-6-agentes', 'fonts');
const css = fs.readFileSync(path.join(FONTS, 'fonts.css'), 'utf8')
  .replace(/url\(([^)]+)\)/g, 'url(https://fonts.gstatic.com/local/$1)');
const body = fs.readFileSync(path.join(__dirname, 'guia.html'), 'utf8');
// same skeleton the artifact host wraps the page in
const html = `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>${body}</body></html>`;

(async () => {
  const browser = await chromium.launch();
  const open = async (viewport) => {
    const page = await browser.newPage({ viewport, deviceScaleFactor: 2 });
    await page.route('https://fonts.googleapis.com/**', r => r.fulfill({ contentType: 'text/css', body: css }));
    await page.route('https://fonts.gstatic.com/**', r => {
      const file = path.join(FONTS, path.basename(new URL(r.request().url()).pathname));
      return fs.existsSync(file) ? r.fulfill({ contentType: 'font/woff2', body: fs.readFileSync(file) }) : r.abort();
    });
    await page.setContent(html, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    return page;
  };

  const page = await open({ width: 600, height: 1140 });
  const out = path.join(__dirname, 'guia-6-agentes-ia.pdf');
  await page.pdf({ path: out, printBackground: true, preferCSSPageSize: true });
  console.log(out);

  if (process.argv.includes('--shots')) {
    for (const [name, width] of [['phone', 390], ['desktop', 1280]]) {
      const p = await open({ width, height: 900 });
      const file = path.join(process.env.SHOTS_DIR || __dirname, `preview-${name}.png`);
      await p.screenshot({ path: file, fullPage: true });
      console.log(file, await p.evaluate(() => document.documentElement.scrollWidth));
    }
  }
  await browser.close();
})();
