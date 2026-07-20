// Post-build guard for the Vite manifest.
//
// Why this exists: on Windows, vite/rolldown builds can emit manifest keys
// with backslash path separators (e.g. "assets\styles\site-base.css"), while
// django-vite looks assets up with POSIX-style paths — producing a runtime
//   DjangoViteAssetNotFoundError: Cannot find assets/styles/site-base.css ...
// This script rewrites every manifest key to forward slashes and fails the
// build loudly if an entry Django needs is missing, so the error surfaces at
// build time instead of at page render.
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const manifestPath = path.resolve(root, '../static/.vite/manifest.json');

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

const normalized = {};
for (const [key, value] of Object.entries(manifest)) {
  normalized[key.replace(/\\+/g, '/')] = value;
}

// both entry keys and the hashed "file" values must use forward slashes
for (const entry of Object.values(normalized)) {
  if (entry.file) entry.file = entry.file.replace(/\\+/g, '/');
}
writeFileSync(manifestPath, JSON.stringify(normalized, null, 2));

const required = [
  'assets/styles/site-base.css',
  'assets/styles/site-tailwind.css',
  'assets/javascript/site.js',
  'assets/javascript/app.js',
];
const missing = required.filter((key) => !(key in normalized));
if (missing.length) {
  console.error(`✘ static/.vite/manifest.json is missing required entries: ${missing.join(', ')}`);
  process.exit(1);
}
console.log(`✔ Vite manifest OK — ${Object.keys(normalized).length} entries, POSIX-normalized keys.`);
