#!/usr/bin/env python3
"""Build The Strand Project into public/.

Run:  python3 build.py

What it does, in order:
1. Loads site settings, pages, sources and facts from data/*.yml.
2. Renders every page in data/pages.yml from templates/pages/.
3. Fails the build if a page cites a source or fact that does not exist.
4. Copies static files, then writes sources.json, facts.json, sitemap.xml
   (when the public URL is known) and build-report.json for auditors.
   build-report.json lists, for each page, the sources it cites and the
   facts it renders.

No network access. No tracking code. Output is plain HTML, CSS and JS.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
OUT = ROOT / "public"
STATIC = ROOT / "static"
SITE_ROOT = ROOT / "site-root"
SPACEFAST_DIR = ROOT / "spacefast"

VALID_VERIFIED_BY = {"human", "tool_assisted"}
BADGE_RE = re.compile(r"\bbadge-(secondary|unconfirmed|inference)\b")
CHECKED_P_RE = re.compile(r'(<p class="checked">.*?</p>)', re.S)
LEDE_P_RE = re.compile(r'(<p class="lede">.*?</p>)', re.S)


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


def source_document_date(s: dict) -> str:
    return str(s.get("document_date") or s.get("date") or "No date shown")


def detect_body_badges(html: str) -> list[str]:
    """Return sorted confidence badge kinds used in <main> before the page source list."""
    main = html.split("<main", 1)[-1].split("</main>", 1)[0]
    body = main.split('<section class="page-sources"', 1)[0]
    return sorted(set(BADGE_RE.findall(body)))


def render_label_key(sources_labels_url: str) -> str:
    """Compact collapsible key explaining confidence pills inline on badged pages."""
    return (
        '<details class="label-key">\n'
        '  <summary>What these labels mean</summary>\n'
        '  <div class="label-key-body">\n'
        '    <dl class="label-key-list">\n'
        '      <dt>No label</dt>\n'
        '      <dd>An official law, court form, or government page that we opened and read.</dd>\n'
        '      <dt><span class="badge badge-secondary">Not official</span></dt>\n'
        '      <dd>Read by us, from a legal aid group, advocacy group, or bill tracker, not the government.</dd>\n'
        '      <dt><span class="badge badge-unconfirmed">Not confirmed</span></dt>\n'
        '      <dd>We could not open the source or find the detail in an official source. Check it yourself first.</dd>\n'
        '      <dt><span class="badge badge-inference">Our reading</span></dt>\n'
        '      <dd>Our plain-language reading where the law or page does not say so directly. Not legal advice.</dd>\n'
        '    </dl>\n'
        f'    <p class="label-key-more"><a href="{escape(sources_labels_url)}">See every source and label</a>.</p>\n'
        '  </div>\n'
        '</details>'
    )


def insert_label_key(html: str, sources_labels_url: str) -> str:
    """Place the collapsible label key right after the lede (before checked/Quick facts)."""
    key = render_label_key(sources_labels_url)
    if LEDE_P_RE.search(html):
        return LEDE_P_RE.sub(r"\1\n" + key, html, count=1)
    if CHECKED_P_RE.search(html):
        return CHECKED_P_RE.sub(r"\1\n" + key, html, count=1)
    return html


def md_escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_claims_md(facts: dict, sources: dict, page_reports: list[dict]) -> str:
    """Auto-generated human-readable fact log (mirrors Stasis's docs/claims.md)."""
    usage: dict[str, list[str]] = {}
    for report in page_reports:
        for fid in report.get("facts", []):
            usage.setdefault(fid, []).append(report["slug"])

    lines = [
        "# Fact log (claims summary)",
        "",
        "Generated from `data/facts.yml` and `data/sources.yml` by `build.py`. Do not edit by hand.",
        "",
        "Every number, fee, and key rule rendered via `fact()` or `fact_src()` lives in `data/facts.yml` and cites one or more entries in `data/sources.yml`. The build fails if any page cites an unknown fact or source.",
        "",
        "Labels:",
        "",
        "- **Official (no label)**: Stated directly in an official law, court form, or government page we opened and read.",
        "- **Not official**: Backed by a legal aid group, advocacy group, or bill tracker rather than a government source.",
        "- **Not confirmed**: Could not be opened or confirmed in an official source.",
        "- **Our reading**: Our plain-language interpretation where the law or agency page does not state the point directly. Not legal advice.",
        "",
        "| ID | Value | Label | Sources (Date on it / Checked) | Pages | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for fid, fact_entry in facts.items():
        labels = []
        if fact_entry.get("reading"):
            labels.append("Our reading")
        src_parts = []
        for sid in fact_entry.get("sources", []):
            s = sources[sid]
            if s["status"] == "secondary" and "Not official" not in labels:
                labels.append("Not official")
            elif s["status"] == "unverified" and "Not confirmed" not in labels:
                labels.append("Not confirmed")
            short = s.get("short") or s["title"]
            doc_date = source_document_date(s)
            checked = as_date(s["checked"]).isoformat()
            src_parts.append(
                f"[{md_escape(short)}]({s['url']}) (`{sid}`, {md_escape(doc_date)}, checked {checked})"
            )
        label_str = ", ".join(labels) if labels else "Official"
        pages_str = ", ".join(sorted(usage.get(fid, []))) or "Not used"
        note = fact_entry.get("note", "")
        lines.append(
            f"| `{fid}` | {md_escape(fact_entry['value'])} | {label_str} | "
            f"{'; '.join(src_parts) or 'None'} | {pages_str} | {md_escape(note)} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    env_theme = os.environ.get("SITE_THEME", "default").strip() or "default"
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--theme",
        choices=["default", "spacefast"],
        default=env_theme if env_theme in ("default", "spacefast") else "default",
        help="color theme to build (default: ODHS palette; spacefast: Radix palette override)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output directory (default: public/, or public-spacefast/ when --theme spacefast is used)",
    )
    parser.add_argument(
        "--check-docs",
        action="store_true",
        help="fail if generated docs/claims.md is out of date instead of rewriting it",
    )
    args = parser.parse_args()
    out_dir = args.out if args.out is not None else (ROOT / "public-spacefast" if args.theme == "spacefast" else OUT)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

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
        verified_by = s.get("verified_by", "human")
        if verified_by not in VALID_VERIFIED_BY:
            errors.append(f"source {s['id']}: unknown verified_by {verified_by}")
        s["verified_by"] = verified_by
        s["document_date"] = source_document_date(s)
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

    state = {"used": [], "facts": [], "page": None}

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
        if fid not in state["facts"]:
            state["facts"].append(fid)
        for sid in facts[fid].get("sources", []):
            use(sid)
        value = escape(str(facts[fid]["value"]))
        if facts[fid].get("reading"):
            value += Markup(' <span class="badge badge-inference">Our reading</span>')
        return Markup(value)

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

    spacefast_assets = {
        "css/spacefast-theme.css": SPACEFAST_DIR / "theme.css",
        "licenses/radix-mit.txt": SPACEFAST_DIR / "radix-mit.txt",
    }

    def asset(path: str) -> str:
        exists = (STATIC / path).exists() or (
            args.theme == "spacefast" and path in spacefast_assets and spacefast_assets[path].exists()
        )
        if not exists:
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
        site_theme=args.theme,
        build_commit=commit,
        build_time=build_time,
        used_sources=lambda: [sources[i] for i in state["used"]],
    )

    # ---- Render -------------------------------------------------------------
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    page_reports = []
    effective_checked_by_slug: dict[str, dt.date] = {}
    for p in pages:
        for key in ("slug", "title", "description", "checked", "template"):
            if key not in p:
                errors.append(f"page entry missing '{key}': {p}")
        state["used"] = []
        state["facts"] = []
        state["page"] = p["slug"]
        try:
            tpl = env.get_template(f"pages/{p['template']}")
            html = tpl.render(page=p)
            page_date = as_date(p["checked"])
            cited_dates = [as_date(sources[sid]["checked"]) for sid in state["used"]]
            if p["slug"] == "sources":
                cited_dates.extend(as_date(s["checked"]) for s in sources_list if not s.get("docs_only"))
            effective_date = max([page_date, *cited_dates])
            if effective_date != page_date:
                state["used"] = []
                state["facts"] = []
                html = tpl.render(page={**p, "checked": effective_date})
        except BuildError as exc:
            errors.append(str(exc))
            continue
        effective_checked_by_slug[p["slug"]] = effective_date
        body_badges = detect_body_badges(html)
        if body_badges and p["slug"] not in {"sources", "about", "404"}:
            html = insert_label_key(html, page_url("sources#labels"))
        (out_dir / f"{p['slug']}.html").write_text(html, encoding="utf-8")
        # "facts" lists every fact the page rendered, so tests/evidence_audit.py
        # can name the pages that show a fact whose source changed.
        page_reports.append({
            "slug": p["slug"],
            "sources": list(state["used"]),
            "facts": list(state["facts"]),
            "badges": body_badges,
            "checked": effective_date.isoformat(),
        })

    if errors:
        print("BUILD FAILED", file=sys.stderr)
        for e in errors:
            print("  error:", e, file=sys.stderr)
        return 1

    # ---- Static files -------------------------------------------------------
    shutil.copytree(STATIC, out_dir / "assets", dirs_exist_ok=True)
    if args.theme == "spacefast":
        shutil.copyfile(SPACEFAST_DIR / "theme.css", out_dir / "assets" / "css" / "spacefast-theme.css")
        shutil.copyfile(SPACEFAST_DIR / "favicon.svg", out_dir / "assets" / "favicon.svg")
        licenses_dir = out_dir / "assets" / "licenses"
        licenses_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SPACEFAST_DIR / "radix-mit.txt", licenses_dir / "radix-mit.txt")
    # Files that must sit at the site root, like Cloudflare's _headers.
    if SITE_ROOT.exists():
        shutil.copytree(SITE_ROOT, out_dir, dirs_exist_ok=True)
    if args.theme == "spacefast" and (out_dir / "_headers").exists():
        # Spacefast manages HSTS at the platform edge and rejects it in _headers.
        headers_lines = [
            line for line in (out_dir / "_headers").read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith("Strict-Transport-Security:")
        ]
        (out_dir / "_headers").write_text("\n".join(headers_lines) + "\n", encoding="utf-8")

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

    public_sources = [
        {k: v for k, v in s.items() if k != "internal_note"}
        for s in sources_list
        if not s.get("docs_only")
    ]
    (out_dir / "sources.json").write_text(json.dumps(public_sources, indent=2, default=jsonable), encoding="utf-8")
    (out_dir / "facts.json").write_text(json.dumps(facts, indent=2, default=jsonable), encoding="utf-8")
    (out_dir / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")

    if pages_url:
        base = pages_url.rstrip("/") + "/"
        def loc(slug: str) -> str:
            if clean_urls:
                return base if slug == "index" else f"{base}{slug}"
            return f"{base}{slug}.html"

        urls = "\n".join(
            f"  <url><loc>{loc(p['slug'])}</loc><lastmod>{effective_checked_by_slug[p['slug']].isoformat()}</lastmod></url>"
            for p in pages
            if p["slug"] != "404"
        )
        (out_dir / "sitemap.xml").write_text(
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
    (out_dir / "build-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.theme == "default" and args.out is None:
        claims_md = render_claims_md(facts, sources, page_reports)
        claims_path = DOCS / "claims.md"
        if args.check_docs:
            if not claims_path.exists() or claims_path.read_text(encoding="utf-8") != claims_md:
                print("docs/claims.md is out of date. Run python3 build.py and commit.", file=sys.stderr)
                return 1
        else:
            claims_path.write_text(claims_md, encoding="utf-8")

    print(f"Built {len(page_reports)} pages, {len(sources)} sources, {len(facts)} facts -> {out_dir}")
    for w in warnings:
        print("  warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
