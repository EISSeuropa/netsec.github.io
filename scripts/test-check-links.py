"""check_external() in scripts/check-links.sh: an HTTP error answered to the
retry without certificate checks keeps the "HTTP <code>" shape, so a 503
there is reported as unreachable rather than failing the run
(EISSeuropa/EISSeuropa.github.io#2220). No network: urlopen is replaced.

Run: python3 -m pytest scripts/test-check-links.py -q
"""
from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

SRC = (Path(__file__).resolve().parent / "check-links.sh").read_text(encoding="utf-8")
INLINE = SRC.split("<<'PY'\n", 1)[1].rsplit("\nPY\n", 1)[0]


def _check_external():
    """check_external and its helpers, without the site scan around them."""
    start = INLINE.index("def _make_ssl_ctx")
    end = INLINE.index("_ssl_warned = None")
    ns = {"ssl": ssl, "urllib": urllib, "sys": __import__("sys"), "_ssl_warned": True,
          "GET_HOSTS": set(), "host_skipped": lambda host: False}
    exec(compile(INLINE[start:end], "check-links-inline", "exec"), ns)
    return ns["check_external"]


def _unreachable():
    return re.compile(re.search(r'UNREACHABLE = re\.compile\(r"([^"]+)"\)', INLINE).group(1))


def _cert_then(code):
    def urlopen(req, context=None, **kw):
        if context is not None and context.verify_mode != ssl.CERT_NONE:
            raise urllib.error.URLError(ssl.SSLCertVerificationError(
                1, "[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer"))
        raise urllib.error.HTTPError(req.full_url, code, "Backend fetch failed", {}, None)
    return urlopen


def test_a_503_on_the_unverified_retry_is_reported_unreachable(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _cert_then(503))
    _, status = _check_external()("https://example.invalid/")
    assert status == "HTTP 503"
    assert _unreachable().search(status)


def test_a_404_on_the_unverified_retry_stays_broken(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _cert_then(404))
    _, status = _check_external()("https://example.invalid/")
    assert status == "HTTP 404"
    assert not _unreachable().search(status)
