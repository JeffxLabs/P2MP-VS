#!/usr/bin/env python3
"""Stamp the dashboard's static data scripts with their content hashes.

Run after building translations or weeks. Week versions are already maintained
by build_week.py; this tool only edits the three script URLs in index.html.
"""

import hashlib
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode


BASE = Path(__file__).resolve().parent.parent
ASSETS = ("data/site.js", "data/i18n.js", "data/manifest.js", "data/stages.js")


def _hash(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:10]


def stamp():
    """Update index.html in place, returning the versions that were stamped."""
    index = BASE / "index.html"
    html = index.read_text(encoding="utf-8")
    versions = {}
    for asset in ASSETS:
        version = _hash(BASE / asset)
        # Accept both quote styles, bare URLs and previously stamped URLs.
        # Keep unrelated query parameters and any fragment intact.
        pattern = re.compile(
            r"(?P<quote>[\"'])(?P<path>" + re.escape(asset)
            + r")(?P<query>\?[^\"'#]*)?(?P<fragment>\#[^\"']*)?(?P=quote)"
        )

        def replace(match):
            query = (match.group("query") or "").lstrip("?")
            params = [(key, value) for key, value in parse_qsl(query, keep_blank_values=True) if key != "v"]
            params.append(("v", version))
            quote = match.group("quote")
            return quote + asset + "?" + urlencode(params) + (match.group("fragment") or "") + quote

        html, count = pattern.subn(replace, html)
        if not count:
            raise ValueError(f"index.html does not reference {asset}")
        versions[asset] = version
    if html != index.read_text(encoding="utf-8"):
        index.write_text(html, encoding="utf-8")
    return versions


if __name__ == "__main__":
    for asset, version in stamp().items():
        print(f"Stamped {asset}?v={version}")
