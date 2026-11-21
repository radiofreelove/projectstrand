"""Verify the live site matches the locally built public/ directory."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import fnmatch
import json
from http.client import HTTPResponse
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

DEFAULT_BASE = "https://projectstrand.pages.dev/"
USER_AGENT = "StrandLiveCheck/1.0 (+https://github.com/radiofreelove/projectstrand)"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


def fetch(url: str, timeout: float = 20.0) -> Response:
    opener = build_opener(_NoRedirect())
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        resp: HTTPResponse = opener.open(req, timeout=timeout)
        with resp:
            return Response(
                status=resp.status,
                headers={k.lower(): v for k, v in resp.headers.items()},
                body=resp.read(),
            )
    except HTTPError as exc:
        body = exc.read() if exc.fp else b""
        return Response(
            status=exc.code,
            headers={k.lower(): v for k, v in exc.headers.items()},
            body=body,
        )


def parse_headers(path: Path) -> list[tuple[str, dict[str, str]]]:
    if not path.is_file():
        return []
    rules: list[tuple[str, dict[str, str]]] = []
    current_pattern: str | None = None
    current_headers: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line[0].isspace():
            if current_pattern is not None:
                rules.append((current_pattern, current_headers))
            current_pattern = raw_line.strip()
            current_headers = {}
        elif current_pattern is not None and ":" in raw_line:
            name, value = raw_line.split(":", 1)
            current_headers[name.strip()] = value.strip()
    if current_pattern is not None:
        rules.append((current_pattern, current_headers))
    return rules


def _pattern_matches(pattern: str, url_path: str) -> bool:
    if pattern == "/*":
        return True
    if pattern.endswith("/*"):
        return url_path.startswith(pattern[:-1])
    if "*" in pattern:
        return fnmatch.fnmatch(url_path, pattern)
    return url_path == pattern


def headers_for(rules: list[tuple[str, dict[str, str]]], url_path: str) -> dict[str, str]:
    merged: dict[str, str] = {}
    for pattern, hdrs in rules:
        if _pattern_matches(pattern, url_path):
            merged.update(hdrs)
    return merged


def url_path_for(public_dir: Path, file_path: Path) -> str:
    rel = file_path.relative_to(public_dir).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    if rel.endswith(".html"):
        return "/" + rel[: -len(".html")]
    return "/" + rel


def check_headers(actual: dict[str, str], expected: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for name, want in expected.items():
        got = actual.get(name.lower())
        if got is None:
            problems.append(f"missing header {name}")
        elif name.lower() == "strict-transport-security":
            if want not in got:
                problems.append(f"header {name}: got {got!r}, expected to contain {want!r}")
        elif got != want:
            problems.append(f"header {name}: got {got!r}, expected {want!r}")
    return problems


def wait_until_matches(base: str, public_dir: Path, max_wait: int) -> None:
    if max_wait <= 0:
        return
    expected = (public_dir / "index.html").read_bytes()
    deadline = time.monotonic() + max_wait
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            resp = fetch(base)
            if resp.status == 200 and resp.body == expected:
                return
            print(f"[wait #{attempt}] / status={resp.status} len={len(resp.body)} != {len(expected)}")
        except URLError as exc:
            print(f"[wait #{attempt}] error: {exc}")
        time.sleep(min(15, max(1, int(deadline - time.monotonic()))))


def run(base: str, public_dir: Path, report_path: Path | None) -> int:
    if not public_dir.is_dir():
        print(f"error: {public_dir} is not a directory", file=sys.stderr)
        return 2

    rules = parse_headers(public_dir / "_headers")
    failures: list[str] = []
    checked = 0

    for path in sorted(public_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(public_dir).as_posix()
        if rel in {"_headers", "_redirects", "404.html"}:
            continue
        url_path = url_path_for(public_dir, path)
        url = urljoin(base, url_path.lstrip("/"))
        try:
            resp = fetch(url)
        except URLError as exc:
            failures.append(f"{url_path}: request failed: {exc}")
            continue
        checked += 1
        if resp.status != 200:
            failures.append(f"{url_path}: expected 200, got {resp.status}")
            continue
        want_bytes = path.read_bytes()
        if rel == "build-report.json":
            try:
                live_report = json.loads(resp.body)
                local_report = json.loads(want_bytes)
            except ValueError as exc:
                failures.append(f"{url_path}: invalid JSON: {exc}")
            else:
                live_report.pop("built_at", None)
                local_report.pop("built_at", None)
                if live_report != local_report:
                    failures.append(f"{url_path}: report mismatch (excluding built_at)")
        elif resp.body != want_bytes:
            failures.append(f"{url_path}: body mismatch (live {len(resp.body)} B vs local {len(want_bytes)} B)")
        for problem in check_headers(resp.headers, headers_for(rules, url_path)):
            failures.append(f"{url_path}: {problem}")

    not_found_path = public_dir / "404.html"
    if not_found_path.is_file():
        resp404 = fetch(urljoin(base, "this-address-does-not-exist"))
        if resp404.status != 404:
            failures.append(f"/this-address-does-not-exist: expected 404, got {resp404.status}")
        elif resp404.body != not_found_path.read_bytes():
            failures.append("/this-address-does-not-exist: body does not match public/404.html")
        for problem in check_headers(resp404.headers, headers_for(rules, "/this-address-does-not-exist")):
            failures.append(f"/this-address-does-not-exist: {problem}")

    for p in sorted(public_dir.rglob("*.html")):
        rel_html = p.relative_to(public_dir).as_posix()
        if rel_html not in {"index.html", "404.html"}:
            target_path = url_path_for(public_dir, p)
            resp_redir = fetch(urljoin(base, rel_html))
            loc = resp_redir.headers.get("location", "")
            loc_path = urlparse(loc).path if loc else ""
            if resp_redir.status not in (301, 302, 307, 308) or loc_path != target_path:
                failures.append(
                    f"/{rel_html}: expected redirect to {target_path}, got status={resp_redir.status} location={loc!r}"
                )
            break

    resp_hdr = fetch(urljoin(base, "_headers"))
    if resp_hdr.status == 200:
        failures.append("/_headers: must not be served publicly (got 200)")

    summary = f"Checked {checked} files against {base}: {len(failures)} failure(s)"
    lines = [summary, *[f"FAIL: {f}" for f in failures]]
    output = "\n".join(lines) + "\n"
    print(output, end="")
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(output, encoding="utf-8")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify live site against public/")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Live site base URL")
    parser.add_argument("--dir", type=Path, default=Path("public"), help="Local build directory")
    parser.add_argument("--report", type=Path, default=None, help="Optional path to write report")
    parser.add_argument("--wait", type=int, default=0, help="Max seconds to wait for / to match")
    args = parser.parse_args(argv)
    base = args.base if args.base.endswith("/") else args.base + "/"
    wait_until_matches(base, args.dir, args.wait)
    return run(base, args.dir, args.report)


if __name__ == "__main__":
    sys.exit(main())
