// Renders each <section class="slide"> of carrusel.html to png/NN.png at 1080x1350.
// Usage: node render.js
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 1500 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'carrusel.html'));
  await page.waitForSelector('body[data-ready="1"]', { state: 'attached' });
  const slides = await page.$$('section.slide');
  for (let i = 0; i < slides.length; i++) {
    const out = path.join(__dirname, 'png', String(i + 1).padStart(2, '0') + '.png');
    await slides[i].screenshot({ path: out });
    console.log(out);
  }
  await browser.close();
})();
