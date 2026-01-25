// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

/**
 * Fix Next.js production build output.
 *
 * Problem:
 * - In some builds, `.next/build-manifest.json` may include CSS files inside `rootMainFiles`.
 * - Next.js treats `rootMainFiles` as scripts and injects them via `<script src="...">`.
 * - This results in `<script src="/_next/static/css/*.css">`, which throws a syntax error
 *   (e.g. "Invalid or unexpected token") and can cause white screens in some environments.
 *
 * What we do:
 * 1) Remove `*.css` entries from `rootMainFiles` in build manifests.
 * 2) Remove any already-generated `<script src="/_next/static/css/*.css">` tags from
 *    prerendered HTML files.
 *
 * This script is safe to run multiple times.
 */

const fs = require('node:fs')
const path = require('node:path')

const CSS_SCRIPT_TAG_RE =
  /<script\s+src="\/_next\/static\/css\/[^"]+\.css"\s+async(?:="")?\s*><\/script>/g

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8')
}

function fileExists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.F_OK)
    return true
  } catch {
    return false
  }
}

function walkFiles(dirPath, predicate) {
  const results = []
  if (!fileExists(dirPath)) return results

  const entries = fs.readdirSync(dirPath, { withFileTypes: true })
  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name)
    if (entry.isDirectory()) {
      results.push(...walkFiles(fullPath, predicate))
      continue
    }
    if (entry.isFile() && predicate(fullPath)) {
      results.push(fullPath)
    }
  }
  return results
}

function patchBuildManifest(manifestPath) {
  if (!fileExists(manifestPath)) return 0

  const manifest = readJson(manifestPath)
  if (!Array.isArray(manifest.rootMainFiles)) return 0

  const before = manifest.rootMainFiles.length
  manifest.rootMainFiles = manifest.rootMainFiles.filter(f => !String(f).endsWith('.css'))
  const after = manifest.rootMainFiles.length

  if (before !== after) {
    writeJson(manifestPath, manifest)
    return before - after
  }
  return 0
}

function patchHtmlFiles(htmlRoot) {
  const htmlFiles = walkFiles(htmlRoot, filePath => filePath.endsWith('.html'))
  let patchedFiles = 0

  for (const filePath of htmlFiles) {
    const original = fs.readFileSync(filePath, 'utf8')
    const patched = original.replace(CSS_SCRIPT_TAG_RE, '')
    if (patched !== original) {
      fs.writeFileSync(filePath, patched, 'utf8')
      patchedFiles += 1
    }
  }

  return patchedFiles
}

function main() {
  const root = process.cwd()
  const targets = [
    {
      name: '.next',
      buildManifest: path.join(root, '.next', 'build-manifest.json'),
      htmlRoot: path.join(root, '.next', 'server', 'app'),
    },
    {
      name: '.next/standalone/.next',
      buildManifest: path.join(root, '.next', 'standalone', '.next', 'build-manifest.json'),
      htmlRoot: path.join(root, '.next', 'standalone', '.next', 'server', 'app'),
    },
  ]

  let removedRootMainCss = 0
  let patchedHtmlCount = 0

  for (const target of targets) {
    removedRootMainCss += patchBuildManifest(target.buildManifest)
    patchedHtmlCount += patchHtmlFiles(target.htmlRoot)
  }

  if (removedRootMainCss || patchedHtmlCount) {
    console.log(
      `[fix-next-build-output] removed ${removedRootMainCss} css entries from rootMainFiles; patched ${patchedHtmlCount} html files`
    )
  } else {
    console.log('[fix-next-build-output] no changes needed')
  }
}

main()
