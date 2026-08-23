#!/usr/bin/env node
/**
 * Static file server for the Lighthouse audit (#1617).
 *
 * Replaces `python3 -m http.server`, which serves HTTP/1.0 with no
 * compression and no range support. GitHub Pages does both, so auditing
 * against http.server measured a transport the site never runs on:
 * `uses-text-compression` showed as the home page's single largest
 * opportunity at 2.8s (production already gzips), and the ESSC recap
 * video reported a 24.9MB transfer because a metadata-only preload
 * cannot range-request its way to the moov atom (#1614).
 *
 * Deliberately dependency-free. The workflow has Node for lhci, and a
 * static server with gzip and single-range support is about eighty lines,
 * which is cheaper than pinning and auditing an npm package for it.
 *
 * Not a production server. No caching headers, no HTTP/2, no directory
 * listing, no symlink hardening. It exists to make one measurement
 * representative and runs only inside the audit job.
 *
 * Usage: node scripts/serve-static.cjs [port] [rootDir]
 */
'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const PORT = Number(process.argv[2] || 8080);
const ROOT = path.resolve(process.argv[3] || '.');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.ics': 'text/calendar; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.mp4': 'video/mp4',
  '.pdf': 'application/pdf',
};

// Compress what Pages compresses: text, not already-compressed binaries.
const COMPRESSIBLE = /^(text\/|application\/(json|xml|javascript))/;

http.createServer((req, res) => {
  let rel;
  try {
    rel = decodeURIComponent(req.url.split('?')[0]);
  } catch {
    res.writeHead(400).end('bad request');
    return;
  }
  if (rel.endsWith('/')) rel += 'index.html';

  const file = path.join(ROOT, rel);
  // Keep the server inside ROOT even if a request tries to climb out.
  if (!file.startsWith(ROOT + path.sep) && file !== ROOT) {
    res.writeHead(403).end('forbidden');
    return;
  }

  fs.stat(file, (err, stat) => {
    if (err || !stat.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain' }).end('404');
      return;
    }
    const type = TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream';
    const range = req.headers.range;

    // Range wins over compression, the way a real server behaves: a client
    // asking for bytes wants those exact bytes. This is the path that keeps
    // a `preload="metadata"` video from pulling the whole file.
    const m = range && /^bytes=(\d*)-(\d*)$/.exec(range.trim());
    if (m) {
      const size = stat.size;
      let start = m[1] === '' ? size - Number(m[2]) : Number(m[1]);
      let end = m[1] === '' || m[2] === '' ? size - 1 : Number(m[2]);
      start = Math.max(0, start);
      end = Math.min(size - 1, end);
      if (Number.isNaN(start) || Number.isNaN(end) || start > end) {
        res.writeHead(416, { 'Content-Range': `bytes */${size}` }).end();
        return;
      }
      res.writeHead(206, {
        'Content-Type': type,
        'Content-Length': end - start + 1,
        'Content-Range': `bytes ${start}-${end}/${size}`,
        'Accept-Ranges': 'bytes',
      });
      fs.createReadStream(file, { start, end }).pipe(res);
      return;
    }

    const wantsGzip = /\bgzip\b/.test(req.headers['accept-encoding'] || '');
    const headers = { 'Content-Type': type, 'Accept-Ranges': 'bytes' };
    if (wantsGzip && COMPRESSIBLE.test(type)) {
      headers['Content-Encoding'] = 'gzip';
      headers['Vary'] = 'Accept-Encoding';
      res.writeHead(200, headers);
      fs.createReadStream(file).pipe(zlib.createGzip()).pipe(res);
    } else {
      headers['Content-Length'] = stat.size;
      res.writeHead(200, headers);
      fs.createReadStream(file).pipe(res);
    }
  });
}).listen(PORT, () => {
  console.log(`serving ${ROOT} on http://localhost:${PORT} (gzip + ranges)`);
});
