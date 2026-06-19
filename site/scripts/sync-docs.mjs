#!/usr/bin/env node
// sync-docs.mjs — copies docs/{en,ru}/ → site/{docs,ru/docs}/ before VitePress dev/build.
// Single sync path; runs locally (via npm predev/prebuild) and on CI identically.
// Idempotent: wipes the destination before copy. Fails loud on missing source.

import { cp, rm, mkdir, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(siteDir, "..");

const PAIRS = [
  { src: "docs/en", dst: "docs", label: "EN" },
  { src: "docs/ru", dst: "ru/docs", label: "RU" },
];

let totalFiles = 0;

for (const { src, dst, label } of PAIRS) {
  const srcAbs = path.join(repoRoot, src);
  const dstAbs = path.join(siteDir, dst);

  if (!existsSync(srcAbs)) {
    console.error(`[sync-docs] FATAL: source not found: ${srcAbs}`);
    process.exit(1);
  }
  const srcStat = await stat(srcAbs);
  if (!srcStat.isDirectory()) {
    console.error(`[sync-docs] FATAL: not a directory: ${srcAbs}`);
    process.exit(1);
  }

  await rm(dstAbs, { recursive: true, force: true });
  await mkdir(dstAbs, { recursive: true });
  await cp(srcAbs, dstAbs, { recursive: true });

  console.log(`[sync-docs] ${label}: ${srcAbs} → ${dstAbs}`);
  totalFiles += 1;
}

console.log(`[sync-docs] done · ${totalFiles} locales synced`);
