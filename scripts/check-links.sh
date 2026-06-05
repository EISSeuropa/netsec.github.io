#!/usr/bin/env bash
# scripts/check-links.sh — broken-link checker for launch QA.
#
# Walks every *.html at the repo root, collects:
#   - every internal <a href="…"> target (relative paths)
#   - every external <a href="http(s)://…"> target
# …and verifies each resolves. Internal checks are file-system based
# (does the target file + #fragment exist?). External checks are
# HEAD requests with a fallback to GET for hosts that refuse HEAD.
#
# Usage:
#   ./scripts/check-links.sh                # full check, prints summary
#   ./scripts/check-links.sh --internal     # internal links only (fast)
#   ./scripts/check-links.sh --quiet        # only print failures
#
# Exits non-zero if any link is broken. Safe to run in CI.
#
# Designed for the maintainer's local laptop AND for the launch-QA
# CI workflow (.github/workflows/launch-qa-link-check.yml). No
# dependencies beyond Python 3 (uses urllib).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
cd "$REPO_ROOT"

INTERNAL_ONLY=0
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --internal) INTERNAL_ONLY=1 ;;
    --quiet) QUIET=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

python3 - "$REPO_ROOT" $INTERNAL_ONLY $QUIET <<'PY'
"""Inline-Python link checker. Avoids extra deps; portable across
the maintainer's macOS laptop and Ubuntu CI."""
import os, re, sys, urllib.parse, urllib.request, urllib.error, ssl
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

repo_root = Path(sys.argv[1])
internal_only = sys.argv[2] == "1"
quiet = sys.argv[3] == "1"

# Collect every <a href="…">. We're permissive on the HTML — the
# regex matches single OR double quotes and ignores attribute order.
HREF_RE = re.compile(r'<a\s+[^>]*?\bhref\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

# Strip <script>...</script> content before the HREF scan. Links
# inside JavaScript string literals (e.g. inline error fallbacks
# that build innerHTML with an <a href="…">) are not page links;
# they are code. Treating them as page links produced a false
# positive when about.html's founding-contributors renderer
# error-fallback referenced https://github.com/.../blob/main/data/
# founding-proposers.json — a URL that 404s until the PR carrying
# the file merges to main. Same logic applies to <style>: any
# `url(...)` inside CSS is handled by the browser, not a navigation
# target.
SCRIPT_STYLE_RE = re.compile(
    r'<(script|style)\b[^>]*>.*?</\1>', re.IGNORECASE | re.DOTALL
)

# Hosts that refuse HEAD and need GET instead. Add to this list when
# we see a 405 / 403 / 404 from a known-good URL that responds 200 on
# GET. Formspree's CDN returns 404 to HEAD on the privacy-policy
# page even though GET returns 200; the site links to the page from
# its own homepage, so the URL is canonical.
GET_HOSTS = {
    "docs.google.com", "forms.google.com",
    "formspree.io",
}

# Hosts we deliberately skip (auth-gated, bot-blocked, internal-only):
SKIP_HOSTS = {
    "e-services.cost.eu",       # e-COST portal — login required
    "docs.google.com",          # Google Forms require user auth; the
                                # form works for real visitors but
                                # returns 401 to unauthenticated HEAD
                                # /GET from this checker.
    "indico.eiss-europa.com",   # Indico HEADs return 400; works for
                                # visitors. Real-URL health is
                                # confirmed manually.
    "simpleicons.org",          # Bot-blocks GitHub-Actions IP ranges
                                # with HTTP 403 on both HEAD and GET
                                # using any Mozilla-style UA. The
                                # site is reachable for real users;
                                # confirmed manually 2026-05-27.
    "eur-lex.europa.eu",        # EU institutional sites return HTTP
    "commission.europa.eu",     # 403 to the Actions-runner IP on both
                                # HEAD and GET, but 200 in a real
                                # browser. Linked from the
                                # accessibility, licensing and privacy
                                # pages; confirmed reachable 2026-06-03.
    "bsky.app",                 # Profile routes throttle the
                                # Actions-runner IP: HEAD returns 404,
                                # GET times out. Reachable for real
                                # users (GET 200 from a browser) and
                                # the handle netsec-cost.eu resolves to
                                # a real DID; confirmed 2026-06-03.
}

# Domains skipped together with every subdomain (suffix match, not exact
# hostname). Use this when a whole institution rate-limits or bot-blocks the
# Actions-runner IP across many hosts rather than one fixed URL.
SKIP_DOMAIN_SUFFIXES = {
    "su.se",                    # Stockholm University. Member-affiliation
                                # links (synced into bios.json) spread across
                                # www.su.se and department subdomains, which
                                # intermittently return 403 / time out for the
                                # Actions-runner IP while resolving fine in a
                                # real browser. Confirmed reachable 2026-06-05.
    "sl.se",                    # Stockholm public transport (linked from the
                                # ESSC practical-info travel section, e.g.
                                # sl.se/en/in-english). Returns HTTP 403 to the
                                # Actions-runner IP on HEAD and GET, but loads in
                                # a real browser. Confirmed reachable 2026-06-05.
}

def host_skipped(hostname):
    """True when a hostname is on the exact skip list or under a skipped
    domain (so su.se covers www.su.se and every department subdomain)."""
    if not hostname:
        return False
    if hostname in SKIP_HOSTS:
        return True
    return any(hostname == d or hostname.endswith("." + d)
               for d in SKIP_DOMAIN_SUFFIXES)

internal_links = {}  # (file, target) — for de-dupe display
external_links = {}  # (url) → first-seen source file
broken_internal = []
broken_external = []

# Cache of directory slugs loaded from data/bios.json — populated
# lazily on first use. Directory deep-links (people.{lang}.html#slug)
# are resolved at runtime via JS that reads bios.json, so they don't
# appear as static id= attributes anywhere; the slug-existence check
# has to look at the data file instead.
import json as _json
_bio_slugs_cache = None
def _is_known_bio_slug(repo_root, frag):
    global _bio_slugs_cache
    if _bio_slugs_cache is None:
        bios_path = repo_root / "data" / "bios.json"
        try:
            data = _json.loads(bios_path.read_text(encoding="utf-8"))
            _bio_slugs_cache = {m.get("id") for m in data.get("members", [])}
        except Exception:
            _bio_slugs_cache = set()
    # Also accept the legacy salutation-prefix form (#dr-arthur-laudrain
    # resolves to the slug arthur-laudrain after the JS strip).
    bare = re.sub(r"^(?:dr|prof|mr|ms|mrs)-", "", frag, flags=re.IGNORECASE)
    return frag in _bio_slugs_cache or bare in _bio_slugs_cache

html_files = sorted(p for p in repo_root.glob("*.html") if p.is_file())
print(f"→ scanning {len(html_files)} HTML files at the repo root...")

for f in html_files:
    text = f.read_text(encoding="utf-8", errors="replace")
    # Strip <script>/<style> bodies before the regex scan; links
    # inside JavaScript or CSS string literals aren't page links.
    text = SCRIPT_STYLE_RE.sub("", text)
    for m in HREF_RE.finditer(text):
        href = m.group(1).strip()
        # Schemes that the checker has nothing useful to say about:
        #   mailto: + tel:     — no URL to fetch
        #   javascript:        — not a navigation target
        #   webcal:            — calendar subscribe; only honoured by
        #                        the OS, not a fetchable HTTP URL
        #   #anchor            — pure same-page fragment; the browser
        #                        handles it without a navigation
        if not href or href.startswith((
                "mailto:", "tel:", "javascript:", "webcal:", "#")):
            continue
        if href.startswith(("http://", "https://")):
            external_links.setdefault(href, str(f.name))
        else:
            # Strip query/fragment for FS check; remember fragment
            url, _, frag = href.partition("#")
            if url.startswith(("//", "data:")):
                continue
            internal_links[(str(f.name), href)] = (url, frag)

# ---- Internal link resolution ----
print(f"  internal targets: {len(internal_links)}")
for (src, href), (url, frag) in internal_links.items():
    if not url:
        # purely #fragment — must exist on the same page
        target_path = repo_root / src
    else:
        # Strip query, then resolve relative to the file
        url_no_q = url.split("?")[0]
        # A leading "/" means repo-root absolute (GitHub Pages serves
        # the root from /). Drop the leading slash before joining so
        # we don't resolve against the host file-system root.
        url_no_q = url_no_q.lstrip("/")
        target_path = (repo_root / url_no_q).resolve()
    if not target_path.exists():
        broken_internal.append(f"  ✗ {src} → {href}  (file not found: {target_path})")
        continue
    # If there's a fragment, see if any element has id="frag" or name="frag".
    if frag and target_path.suffix.lower() == ".html":
        body = target_path.read_text(encoding="utf-8", errors="replace")
        ok = (
            re.search(rf'\b(?:id|name)\s*=\s*["\']{re.escape(frag)}["\']', body)
            # Members directory deep-links resolve at runtime: people.{lang}.html#<slug>
            # corresponds to a member id in data/bios.json. Validate against that.
            or (target_path.name.startswith("people")
                and _is_known_bio_slug(repo_root, frag))
        )
        if not ok:
            broken_internal.append(
                f"  ✗ {src} → {href}  (anchor #{frag} not found in {target_path.name})"
            )

# ---- External link checks ----
def _make_ssl_ctx(verify=True):
    """Build an SSL context. Default uses the system CA store; if
    that fails (typical on macOS where Python's default trust store
    can be empty until the certificates are installed), the caller
    can retry with verify=False — we're checking link health, not
    authenticating the server."""
    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()

def check_external(url):
    parsed = urllib.parse.urlparse(url)
    if host_skipped(parsed.hostname):
        return (url, "skip")
    method = "GET" if parsed.hostname in GET_HOSTS else "HEAD"
    headers = {
        "User-Agent": "Mozilla/5.0 (NetSec link checker; +https://netsec-cost.eu)",
        "Accept": "*/*",
    }
    def _do(method, ctx):
        req = urllib.request.Request(url, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return resp.status
    try:
        return (url, _do(method, _make_ssl_ctx(verify=True)))
    except urllib.error.HTTPError as e:
        # 4xx + 5xx are errors; 3xx is followed by urllib by default.
        # Some hosts 403/405 on HEAD but 200 on GET — retry with GET.
        if method == "HEAD" and e.code in (403, 405) and parsed.hostname not in GET_HOSTS:
            try:
                return (url, _do("GET", _make_ssl_ctx(verify=True)))
            except Exception as e2:
                return (url, f"err: {e2}")
        return (url, f"HTTP {e.code}")
    except urllib.error.URLError as e:
        # On macOS the default Python install often ships with an
        # empty trust store, so every https:// fetch trips
        # CERTIFICATE_VERIFY_FAILED. CI (Linux) doesn't have this
        # problem. Retry once with verification off — we're not
        # trying to authenticate the server, only see if the URL
        # responds. Print a one-line warning the first time it
        # happens so the user knows what's going on.
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            global _ssl_warned
            try:
                _ssl_warned
            except NameError:
                _ssl_warned = True
                print(
                    "  ⚠ local Python trust store rejected the server cert "
                    "(common on macOS); retrying with verification off. "
                    "Install certificates with /Applications/Python\\ 3.*/"
                    "Install\\ Certificates.command to fix this.",
                    file=sys.stderr,
                )
            try:
                return (url, _do(method, _make_ssl_ctx(verify=False)))
            except Exception as e2:
                return (url, f"err: {e2.__class__.__name__}: {e2}")
        return (url, f"err: {e.__class__.__name__}: {e}")
    except Exception as e:
        return (url, f"err: {e.__class__.__name__}: {e}")

_ssl_warned = None  # forward declaration; first SSL failure flips it

if not internal_only and external_links:
    print(f"  external targets: {len(external_links)}")
    # Concurrency set to 3, not 8 — GitHub rate-limits unauth'd
    # HEADs from one IP and starts timing out / RST'ing when we burst.
    # 3 parallel requests at ~15 s timeout each means a worst-case
    # full-batch wall time of (N / 3) × 15 s, which for ~70 external
    # links is ~6 minutes. Acceptable for a launch-QA run.
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(check_external, url): url for url in external_links}
        for fut in as_completed(futures):
            url, status = fut.result()
            if status == "skip":
                if not quiet:
                    print(f"  - {url}  (skipped: auth-gated)")
            elif isinstance(status, int) and 200 <= status < 400:
                if not quiet:
                    print(f"  ✓ {url}  ({status})")
            else:
                broken_external.append(
                    f"  ✗ {external_links[url]} → {url}  ({status})"
                )

# ---- Summary ----
print()
if broken_internal:
    print(f"INTERNAL BROKEN ({len(broken_internal)}):")
    for line in broken_internal:
        print(line)
if broken_external:
    print(f"EXTERNAL BROKEN ({len(broken_external)}):")
    for line in broken_external:
        print(line)
if not broken_internal and not broken_external:
    print(f"✓ All links resolved ({len(internal_links)} internal, "
          f"{len(external_links) if not internal_only else 0} external).")
    sys.exit(0)
sys.exit(1)
PY
