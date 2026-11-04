#!/usr/bin/env python3
"""Build The Strand Project into public/.

Run:  python3 build.py

What it does, in order:
1. Loads site settings, pages, sources and facts from data/*.yml.
2. Renders every page in data/pages.yml from templates/pages/.
3. Fails the build if a page cites a source or fact that does not exist.
4. Copies static files, then writes sources.json, facts.json, sitemap.xml
   (when the public URL is known) and build-report.json for auditors.

No network access. No tracking code. Output is plain HTML, CSS and JS.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "public"
STATIC = ROOT / "static"
SITE_ROOT = ROOT / "site-root"


class BuildError(Exception):
    """A problem that must stop the build."""


def load_yaml(name: str):
    with open(DATA / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def as_date(value) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def human_date(value) -> str:
    d = as_date(value)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def main() -> int:
    site = load_yaml("site.yml")
    pages = load_yaml("pages.yml")
    sources_list = load_yaml("sources.yml")
    facts = load_yaml("facts.yml")

    errors: list[str] = []
    warnings: list[str] = []

    # ---- Sources: unique ids, required fields --------------------------------
    sources: dict[str, dict] = {}
    required = {"id", "title", "publisher", "url", "kind", "jurisdiction", "checked", "status"}
    for s in sources_list:
        missing = required - set(s)
        if missing:
            errors.append(f"source {s.get('id', '?')}: missing {sorted(missing)}")
            continue
        if s["id"] in sources:
            errors.append(f"duplicate source id: {s['id']}")
        if s["status"] not in {"verified", "secondary", "unverified", "linked"}:
            errors.append(f"source {s['id']}: unknown status {s['status']}")
        sources[s["id"]] = s

    # ---- Facts: every fact must cite known sources --------------------------
    for fid, f in facts.items():
        for sid in f.get("sources", []):
            if sid not in sources:
                errors.append(f"fact {fid}: unknown source {sid}")

    # ---- Where the site lives: Cloudflare Pages, built from GitHub (ADR-0004). --
    env_vars = os.environ
    pages_url = (
        env_vars.get("SITE_URL")             # manual override, for testing another address
        or site.get("public_url")
        or env_vars.get("CF_PAGES_URL")      # Cloudflare's per-deployment address, last resort
        or ""
    )
    # Clean URLs ("/oregon" instead of "/oregon.html") avoid a redirect on hosts
    # that strip ".html", like Cloudflare Pages. Cloudflare sets CF_PAGES=1.
    clean_urls = env_vars.get("CLEAN_URLS") == "1" or env_vars.get("CF_PAGES") == "1"
    base_path = urlparse(pages_url).path if pages_url else "/"
    if not base_path.endswith("/"):
        base_path += "/"
    github_repo = (
        f"{env_vars['GITHUB_SERVER_URL']}/{env_vars['GITHUB_REPOSITORY']}"
        if env_vars.get("GITHUB_SERVER_URL") and env_vars.get("GITHUB_REPOSITORY")
        else ""
    )
    repo_url = (env_vars.get("REPO_URL") or github_repo or site["repo_url"]).rstrip("/")
    issues_url = f"{repo_url}/issues"
    commit = (
        env_vars.get("GITHUB_SHA")
        or env_vars.get("CF_PAGES_COMMIT_SHA")
        or "local"
    )
    build_time = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    fonts_available = (STATIC / "fonts" / "AtkinsonHyperlegibleNext-Regular.woff2").exists()

    # ---- Template environment ----------------------------------------------
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        undefined=StrictUndefined,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["human_date"] = human_date

    state = {"used": [], "page": None}

    def use(sid: str) -> dict:
        if sid not in sources:
            raise BuildError(f"page {state['page']}: unknown source id '{sid}'")
        if sid not in state["used"]:
            state["used"].append(sid)
        return sources[sid]

    def src(sid: str, label: str | None = None) -> Markup:
        """A small 'Source' link to the official page, recorded for the page's source list."""
        s = use(sid)
        short = label or s.get("short") or s["title"]
        note = ""
        if s["status"] == "unverified":
            note = ' <span class="badge badge-unconfirmed">Not confirmed</span>'
        elif s["status"] == "secondary":
            note = ' <span class="badge badge-secondary">Not official</span>'
        return Markup(
            f'<a class="src" href="{escape(s["url"])}" rel="noreferrer">'
            f'<span class="src-label">Source:</span> {escape(short)}</a>{note}'
        )

    def fact(fid: str) -> Markup:
        if fid not in facts:
            raise BuildError(f"page {state['page']}: unknown fact id '{fid}'")
        for sid in facts[fid].get("sources", []):
            use(sid)
        return Markup(escape(str(facts[fid]["value"])))

    def fact_src(fid: str) -> Markup:
        """A fact value followed by its source link(s)."""
        value = fact(fid)
        chips = " ".join(str(src(sid)) for sid in facts[fid].get("sources", []))
        return Markup(f"{value} {chips}")

    def ext(sid: str, text: str | None = None) -> Markup:
        """A normal link to an official page, by source id."""
        s = use(sid)
        label = text or s.get("link_text") or s["title"]
        kind = "official site" if s.get("official", True) else "outside site"
        return Markup(
            f'<a class="ext" href="{escape(s["url"])}" rel="noreferrer">{escape(label)}'
            f'<span class="vh"> ({kind})</span></a>'
        )

    def prefix() -> str:
        # The 404 page can be served at any depth, so it needs absolute links.
        return base_path if state["page"] == "404" else ""

    def page_url(slug: str) -> str:
        known = {p["slug"] for p in pages}
        name, _, anchor = slug.partition("#")
        if name not in known:
            raise BuildError(f"page {state['page']}: link to unknown page '{slug}'")
        if clean_urls:
            path = (prefix() or "./") if name == "index" else f"{prefix()}{name}"
        else:
            path = f"{prefix()}{name}.html"
        return path + (f"#{anchor}" if anchor else "")

    def asset(path: str) -> str:
        if not (STATIC / path).exists():
            raise BuildError(f"page {state['page']}: missing asset '{path}'")
        return f"{prefix()}assets/{path}"

    env.globals.update(
        site=site,
        pages=pages,
        sources=sources,
        sources_list=sources_list,
        facts=facts,
        src=src,
        fact=fact,
        fact_src=fact_src,
        ext=ext,
        page_url=page_url,
        asset=asset,
        repo_url=repo_url,
        issues_url=issues_url,
        base_path=base_path,
        fonts_available=fonts_available,
        build_commit=commit,
        build_time=build_time,
        used_sources=lambda: [sources[i] for i in state["used"]],
    )

    # ---- Render -------------------------------------------------------------
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    page_reports = []
    for p in pages:
        for key in ("slug", "title", "description", "checked", "template"):
            if key not in p:
                errors.append(f"page entry missing '{key}': {p}")
        state["used"] = []
        state["page"] = p["slug"]
        try:
            tpl = env.get_template(f"pages/{p['template']}")
            html = tpl.render(page=p)
        except BuildError as exc:
            errors.append(str(exc))
            continue
        (OUT / f"{p['slug']}.html").write_text(html, encoding="utf-8")
        page_reports.append({"slug": p["slug"], "sources": list(state["used"]), "checked": str(p["checked"])})

    if errors:
        print("BUILD FAILED", file=sys.stderr)
        for e in errors:
            print("  error:", e, file=sys.stderr)
        return 1

    # ---- Static files -------------------------------------------------------
    shutil.copytree(STATIC, OUT / "assets", dirs_exist_ok=True)
    # Files that must sit at the site root, like Cloudflare's _headers.
    if SITE_ROOT.exists():
        shutil.copytree(SITE_ROOT, OUT, dirs_exist_ok=True)

    # ---- Audit outputs ------------------------------------------------------
    today = dt.date.today()
    max_age = int(site.get("max_source_age_days", 120))
    used_anywhere = {sid for r in page_reports for sid in r["sources"]}
    for sid, s in sources.items():
        age = (today - as_date(s["checked"])).days
        if age > max_age:
            warnings.append(f"source {sid} last checked {age} days ago (limit {max_age})")
        if sid not in used_anywhere and not s.get("docs_only"):
            warnings.append(f"source {sid} is not cited on any page")

    def jsonable(obj):
        if isinstance(obj, (dt.date, dt.datetime)):
            return obj.isoformat()
        raise TypeError(type(obj))

    public_sources = [s for s in sources_list if not s.get("docs_only")]
    (OUT / "sources.json").write_text(json.dumps(public_sources, indent=2, default=jsonable), encoding="utf-8")
    (OUT / "facts.json").write_text(json.dumps(facts, indent=2, default=jsonable), encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")

    if pages_url:
        base = pages_url.rstrip("/") + "/"
        def loc(slug: str) -> str:
            if clean_urls:
                return base if slug == "index" else f"{base}{slug}"
            return f"{base}{slug}.html"

        urls = "\n".join(
            f"  <url><loc>{loc(p['slug'])}</loc><lastmod>{p['checked']}</lastmod></url>"
            for p in pages
            if p["slug"] != "404"
        )
        (OUT / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}\n</urlset>\n",
            encoding="utf-8",
        )

    report = {
        "built_at": build_time,
        "commit": commit,
        "public_url": pages_url or None,
        "pages": page_reports,
        "source_count": len(sources),
        "fact_count": len(facts),
        "warnings": warnings,
        "fonts_bundled": fonts_available,
        "clean_urls": clean_urls,
    }
    (OUT / "build-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Built {len(page_reports)} pages, {len(sources)} sources, {len(facts)} facts -> {OUT}")
    for w in warnings:
        print("  warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
