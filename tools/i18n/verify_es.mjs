// Verificación: la app se ve en español en un navegador real.
// Comprueba el título de la pestaña, el lang del documento, el locale que
// react-aria resuelve y el texto visible de la página de login.
//
// Uso: node tools/i18n/verify_es.mjs [http://localhost:8941]
import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';

const BASE = process.argv[2] || 'http://localhost:8941';

/** El Chromium que Playwright ya tiene descargado, si lo hay. */
function installedChromium() {
  const cache = join(process.env.HOME || '', 'Library/Caches/ms-playwright');
  let shells = [];
  try {
    shells = readdirSync(cache).filter((name) => name.startsWith('chromium_headless_shell-'));
  } catch {
    return '';
  }
  for (const name of shells.sort().reverse()) {
    const binary = join(cache, name, 'chrome-headless-shell-mac-arm64', 'chrome-headless-shell');
    try {
      readdirSync(join(cache, name, 'chrome-headless-shell-mac-arm64'));
      return binary;
    } catch {
      continue;
    }
  }
  return '';
}

const executablePath = process.env.CHROME_PATH || installedChromium();
const browser = await chromium.launch(executablePath ? { executablePath } : {});
const page = await browser.newPage({ locale: 'zh-CN' }); // navegador en chino a propósito
await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });

const result = await page.evaluate(() => ({
  title: document.title,
  lang: document.documentElement.lang,
  reactAriaLocale:
    window[Symbol.for('react-aria.i18n.locale')] ?? '(sin fijar)',
  bodyText: document.body.innerText.replace(/\s+/g, ' ').trim().slice(0, 400),
  cjk: (document.body.innerText.match(/[一-鿿]/g) || []).length,
}));

console.log(JSON.stringify(result, null, 2));
await browser.close();

// El smoke falla si queda chino en pantalla o si el documento no se declara
// en español: son las dos señales de que la traducción no llegó.
if (result.cjk > 0 || result.lang !== 'es-ES') {
  console.error('La página de acceso no sale en español.');
  process.exit(1);
}
