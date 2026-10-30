"""Compare what search engines see on main and on this branch: builds both offline (main in a temporary git worktree,
this branch in the working tree, both as production, not testing) and, for every page both builds have, compares the
title, canonical URL, meta description, robots meta, og:image and JSON-LD @types. Also lists files main builds that this
branch does not (static/app.js and static/style.css are expected to be gone). Prints each difference; exit 1 if any.
Run from the repo root (publish runbook, docs/superpowers/notes/2026-10-27-publish-newsite.md, step 10):
  python tools/seo_diff.py [--main origin/main] [--main-build DIR --new-build DIR]   (the two DIRs: compare existing builds)"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_GONE = {"static/app.js", "static/style.css"}


def _build(cwd: Path) -> Path:
    env = {k: v for k, v in os.environ.items() if k != "DOORPRICE_ENV"}   # production head fields, not the testing noindex
    subprocess.run([sys.executable, "-m", "pricechecker.run", "--build-only", "--offline"], cwd=cwd, env=env, check=True)
    return cwd / "build"


def _attr(h: str, tag_re: str, attr: str) -> str | None:
    for m in re.finditer(tag_re, h, re.IGNORECASE):
        a = re.search(rf'\s{attr}="([^"]*)"', m.group(0))
        if a:
            return html.unescape(a.group(1))
    return None


def _ld_types(h: str) -> list[str]:
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.DOTALL):
        try:
            doc = json.loads(m.group(1).replace("<\\/", "</"))
        except ValueError:
            out.append("(unreadable JSON-LD)")
            continue
        for d in doc if isinstance(doc, list) else doc.get("@graph", [doc]):
            t = d.get("@type") if isinstance(d, dict) else None
            out += t if isinstance(t, list) else [str(t)]
    return sorted(out)


def seo_fields(h: str) -> dict:
    title = re.search(r"<title>(.*?)</title>", h, re.DOTALL)
    return {"title": html.unescape(title.group(1).strip()) if title else None,
            "canonical": _attr(h, r'<link\b[^>]*rel="canonical"[^>]*>', "href"),
            "description": _attr(h, r'<meta\b[^>]*name="description"[^>]*>', "content"),
            "robots": _attr(h, r'<meta\b[^>]*name="robots"[^>]*>', "content"),
            "og:image": _attr(h, r'<meta\b[^>]*property="og:image"[^>]*>', "content"),
            "ld+json": _ld_types(h)}


def compare(main: Path, new: Path) -> list[str]:
    files = lambda root: {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    a, b = files(main), files(new)
    diffs = [f"only on main: {p}" for p in sorted(a - b - EXPECTED_GONE) if not p.startswith("data/")]
    for rel in sorted(p for p in a & b if p.endswith(".html")):
        fa, fb = seo_fields((main / rel).read_text()), seo_fields((new / rel).read_text())
        for k in fa:
            if fa[k] != fb[k]:
                diffs.append(f"{rel}: {k}\n    main:    {fa[k]!r}\n    newsite: {fb[k]!r}")
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--main", default="origin/main", help="the ref to compare against (default origin/main)")
    ap.add_argument("--main-build", type=Path, help="an existing build of main (skips building)")
    ap.add_argument("--new-build", type=Path, help="an existing build of this branch (skips building)")
    args = ap.parse_args()
    root = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        main_build = args.main_build
        if main_build is None:
            wt = Path(tmp) / "main"
            subprocess.run(["git", "worktree", "add", "--detach", str(wt), args.main], check=True)
            try:
                main_build = _build(wt)
                kept = Path(tmp) / "main-build"
                main_build.rename(kept)
                main_build = kept
            finally:
                subprocess.run(["git", "worktree", "remove", "--force", str(wt)], check=False)
        new_build = args.new_build or _build(root)
        diffs = compare(main_build, new_build)
    for d in diffs:
        print(d)
    print(f"{len(diffs)} difference(s)")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
