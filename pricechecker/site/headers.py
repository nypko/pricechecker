"""build/_headers for Cloudflare Pages: cache rules for the hashed assets, and security headers on every response.

The Content-Security-Policy is sent as Report-Only first (browsers log violations in the console and block nothing),
so a missed case can't break the site; switch the header name to Content-Security-Policy once it has run clean.
Inline scripts are allowed by hash only, and the hashes are worked out here from the pages just rendered (today: the
pages.dev -> doorprice.app redirect in templates/base.html), so a changed script or base_url can't leave a stale hash.
JSON data blocks (application/json, application/ld+json) are not scripts to the browser and need no hash."""
import base64
import hashlib
import re
from collections.abc import Iterable

# an inline <script> that runs: no src, and not a JSON data block
_INLINE = re.compile(r'<script(?![^>]*\ssrc=)(?![^>]*\stype="application/(?:ld\+)?json")[^>]*>(.*?)</script>', re.DOTALL)

CACHE = ("/static/d.css\n  Cache-Control: public, max-age=31536000, immutable\n"
         "/static/js/*\n  Cache-Control: public, max-age=31536000, immutable\n"
         "/static/fonts/*\n  Cache-Control: public, max-age=2592000\n"
         "/static/icons/*\n  Cache-Control: public, max-age=2592000\n"
         "/data/v1/*\n  Cache-Control: public, max-age=31536000, immutable\n")   # names carry a content hash


def inline_script_hashes(pages: Iterable[str]) -> list[str]:
    """'sha256-...' for every distinct inline script in the pages, sorted."""
    return sorted({"sha256-" + base64.b64encode(hashlib.sha256(m.group(1).encode()).digest()).decode()
                   for h in pages for m in _INLINE.finditer(h)})


def csp(hashes: list[str]) -> str:
    """Scripts and styles from the site itself (plus the inline scripts by hash, and Cloudflare Web Analytics' beacon
    when it is switched on); inline style="" attributes stay allowed (blocks.js and several templates set --n, flex,
    colours), <style> elements do not; no framing, no plugins, forms post to the site only."""
    script = " ".join(["'self'", *(f"'{h}'" for h in hashes), "https://static.cloudflareinsights.com"])
    return ("default-src 'self'; "
            f"script-src {script}; "
            "style-src 'self'; style-src-attr 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; "
            "connect-src 'self' https://cloudflareinsights.com; "
            "form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'")


def security(hashes: list[str]) -> str:
    # upgrade-insecure-requests is left out while the policy is Report-Only: browsers ignore it there (and say so)
    return ("/*\n"
            "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n"
            "  X-Content-Type-Options: nosniff\n"
            "  Referrer-Policy: strict-origin-when-cross-origin\n"
            "  X-Frame-Options: DENY\n"
            "  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()\n"
            f"  Content-Security-Policy-Report-Only: {csp(hashes)}\n")


def headers(pages: Iterable[str]) -> str:
    """The whole _headers file for the rendered pages' HTML."""
    return security(inline_script_hashes(pages)) + CACHE
