#!/usr/bin/env python3
"""Check vendored AgentOS skills against their upstream GitHub paths."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z ]+):\s*(.*?)\s*$")
COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
DEFAULT_TIMEOUT_SECONDS = 20
GITHUB_API = "https://api.github.com"


@dataclass
class UpstreamMetadata:
    skill: str
    upstream_file: str
    source: str
    owner: str | None
    repo: str | None
    path: str | None
    vendored_ref: str | None
    branch: str | None


@dataclass
class UpstreamResult:
    skill: str
    status: str
    source: str | None
    path: str | None
    vendored_ref: str | None
    upstream_ref: str | None
    upstream_branch: str | None
    compare_url: str | None
    upstream_url: str | None
    note: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agentos-root",
        type=Path,
        default=None,
        help="AgentOS checkout root. Defaults to discovery from the current directory.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero when updates are available as well as when checks fail.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run local parser/discovery self-tests without network access.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        return run_self_tests()

    root = resolve_agentos_root(args.agentos_root)
    metadata = discover_upstream_metadata(root)
    results = [check_upstream(item, timeout=args.timeout) for item in metadata]
    if args.format == "json":
        print(json.dumps([asdict(result) for result in results], indent=2, sort_keys=True))
    else:
        print_text_report(root, results)
    return exit_code(results, strict=args.strict)


def resolve_agentos_root(requested_root: Path | None) -> Path:
    if requested_root is not None:
        root = lexical_absolute(requested_root)
        require_agentos_root(root)
        return root
    for path in [Path.cwd(), *Path.cwd().parents]:
        if (path / "os/skills/MANIFEST.md").is_file():
            return lexical_absolute(path)
    raise SystemExit("Could not find AgentOS root containing os/skills/MANIFEST.md")


def lexical_absolute(path: Path) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.abspath(expanded))


def require_agentos_root(root: Path) -> None:
    if not root.is_dir():
        raise SystemExit(f"AgentOS root is not a directory: {root}")
    if not (root / "os/skills/MANIFEST.md").is_file():
        raise SystemExit(f"AgentOS root is missing os/skills/MANIFEST.md: {root}")


def discover_upstream_metadata(root: Path) -> list[UpstreamMetadata]:
    skills_root = root / "os/skills"
    items: list[UpstreamMetadata] = []
    for upstream_file in sorted(skills_root.glob("*/UPSTREAM.md")):
        skill = upstream_file.parent.name
        items.append(parse_upstream_file(skill, upstream_file, root))
    return items


def parse_upstream_file(skill: str, upstream_file: Path, root: Path) -> UpstreamMetadata:
    fields: dict[str, str] = {}
    try:
        text = upstream_file.read_text(encoding="utf-8")
    except OSError as error:
        return UpstreamMetadata(
            skill=skill,
            upstream_file=relative_display(upstream_file, root),
            source="",
            owner=None,
            repo=None,
            path=None,
            vendored_ref=None,
            branch=None,
        )
    for line in text.splitlines():
        match = FIELD_RE.match(line)
        if match:
            fields[normalize_field(match.group(1))] = clean_value(match.group(2))
    source = fields.get("source", "")
    owner, repo = parse_github_source(source)
    return UpstreamMetadata(
        skill=skill,
        upstream_file=relative_display(upstream_file, root),
        source=source,
        owner=owner,
        repo=repo,
        path=fields.get("path"),
        vendored_ref=fields.get("vendored ref"),
        branch=fields.get("branch") or fields.get("upstream branch"),
    )


def normalize_field(field: str) -> str:
    return " ".join(field.lower().split())


def clean_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        value = value[1:-1]
    return value.strip()


def parse_github_source(source: str) -> tuple[str | None, str | None]:
    clean = clean_value(source)
    if not clean:
        return None, None
    if clean.startswith("https://github.com/") or clean.startswith("http://github.com/"):
        parsed = urllib.parse.urlparse(clean)
        parts = [part for part in parsed.path.split("/") if part]
    else:
        parts = [part for part in clean.split("/") if part]
    if len(parts) < 2:
        return None, None
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        return None, None
    return owner, repo


def check_upstream(metadata: UpstreamMetadata, timeout: float) -> UpstreamResult:
    if not metadata.owner or not metadata.repo:
        return failed(metadata, "unsupported or malformed Source; expected owner/repo or github.com URL")
    if not metadata.path:
        return failed(metadata, "missing Path")
    if not metadata.vendored_ref:
        return failed(metadata, "missing Vendored ref")
    if not is_commit_sha(metadata.vendored_ref):
        return failed(metadata, "malformed Vendored ref; expected full 40-character commit SHA")

    try:
        branch = metadata.branch or fetch_default_branch(metadata.owner, metadata.repo, timeout)
        latest = fetch_latest_path_commit(metadata.owner, metadata.repo, metadata.path, branch, timeout)
        status, note = classify_ref_status(metadata.owner, metadata.repo, metadata.vendored_ref, latest, timeout)
        return UpstreamResult(
            skill=metadata.skill,
            status=status,
            source=metadata.source,
            path=metadata.path,
            vendored_ref=metadata.vendored_ref,
            upstream_ref=latest,
            upstream_branch=branch,
            compare_url=compare_url(metadata.owner, metadata.repo, metadata.vendored_ref, latest),
            upstream_url=upstream_path_url(metadata.owner, metadata.repo, branch, metadata.path),
            note=note,
        )
    except CheckError as error:
        return failed(metadata, str(error))


def fetch_default_branch(owner: str, repo: str, timeout: float) -> str:
    data = request_json(f"{GITHUB_API}/repos/{owner}/{repo}", timeout)
    branch = data.get("default_branch")
    if not isinstance(branch, str) or not branch:
        raise CheckError("GitHub response missing default_branch")
    return branch


def fetch_latest_path_commit(owner: str, repo: str, path: str, branch: str, timeout: float) -> str:
    query = urllib.parse.urlencode({"sha": branch, "path": path, "per_page": "1"})
    data = request_json(f"{GITHUB_API}/repos/{owner}/{repo}/commits?{query}", timeout)
    if not isinstance(data, list):
        raise CheckError("GitHub commits response was not a list")
    if not data:
        raise CheckError(f"no upstream commits found for path on {branch}: {path}")
    sha = data[0].get("sha")
    if not isinstance(sha, str) or not sha:
        raise CheckError("GitHub commits response missing sha")
    if not is_commit_sha(sha):
        raise CheckError("GitHub commits response returned a malformed commit SHA")
    return sha


def classify_ref_status(owner: str, repo: str, vendored_ref: str, latest_path_ref: str, timeout: float) -> tuple[str, str]:
    if not is_commit_sha(vendored_ref):
        return "check-failed", "malformed Vendored ref; expected full 40-character commit SHA"
    if not is_commit_sha(latest_path_ref):
        return "check-failed", "upstream latest path commit was not a full 40-character commit SHA"
    if vendored_ref.lower() == latest_path_ref.lower():
        return "up-to-date", "vendored ref is the latest path-touching upstream commit"
    compare = fetch_compare(owner, repo, vendored_ref, latest_path_ref, timeout)
    status = compare.get("status")
    if status in {"behind", "identical"}:
        return "up-to-date", "vendored snapshot already contains the latest path-touching upstream commit"
    if status == "ahead":
        return "update-available", "upstream path has changed after the vendored ref"
    if status == "diverged":
        return "check-failed", "vendored ref and latest path commit diverged"
    return "check-failed", f"unexpected GitHub compare status: {status!r}"


def is_commit_sha(ref: str) -> bool:
    return bool(COMMIT_SHA_RE.fullmatch(ref))


def fetch_compare(owner: str, repo: str, base: str, head: str, timeout: float) -> dict[str, Any]:
    safe_base = urllib.parse.quote(base, safe="")
    safe_head = urllib.parse.quote(head, safe="")
    data = request_json(f"{GITHUB_API}/repos/{owner}/{repo}/compare/{safe_base}...{safe_head}", timeout)
    if not isinstance(data, dict):
        raise CheckError("GitHub compare response was not an object")
    return data


def request_json(url: str, timeout: float) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AgentOS-vendored-skill-upstream-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise CheckError(f"GitHub HTTP {error.code} for {url}: {trim(body)}") from error
    except urllib.error.URLError as error:
        raise CheckError(f"network error for {url}: {error.reason}") from error
    except TimeoutError as error:
        raise CheckError(f"timeout fetching {url}") from error
    except json.JSONDecodeError as error:
        raise CheckError(f"invalid JSON from {url}: {error}") from error


def failed(metadata: UpstreamMetadata, note: str) -> UpstreamResult:
    return UpstreamResult(
        skill=metadata.skill,
        status="check-failed",
        source=metadata.source or None,
        path=metadata.path,
        vendored_ref=metadata.vendored_ref,
        upstream_ref=None,
        upstream_branch=metadata.branch,
        compare_url=None,
        upstream_url=None,
        note=note,
    )


def compare_url(owner: str, repo: str, vendored_ref: str, latest: str) -> str:
    return f"https://github.com/{owner}/{repo}/compare/{vendored_ref}...{latest}"


def upstream_path_url(owner: str, repo: str, branch: str, path: str) -> str:
    quoted_path = "/".join(urllib.parse.quote(part) for part in path.split("/"))
    quoted_branch = urllib.parse.quote(branch, safe="")
    view = "tree" if path.endswith("/") else "blob"
    return f"https://github.com/{owner}/{repo}/{view}/{quoted_branch}/{quoted_path}"


def print_text_report(root: Path, results: list[UpstreamResult]) -> None:
    print(f"AgentOS root: {root}")
    if not results:
        print("No vendored skill upstream files found.")
        return
    rows = [
        [
            result.status,
            result.skill,
            short_ref(result.vendored_ref),
            short_ref(result.upstream_ref),
            result.upstream_branch or "-",
            result.note,
        ]
        for result in results
    ]
    headers = ["status", "skill", "vendored", "upstream", "branch", "note"]
    widths = [max(len(str(row[index])) for row in [headers, *rows]) for index in range(len(headers))]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row, result in zip(rows, results):
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))
        if result.status == "update-available" and result.compare_url:
            print(f"  compare: {result.compare_url}")


def short_ref(ref: str | None) -> str:
    if not ref:
        return "-"
    return ref[:12]


def relative_display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def trim(value: str, limit: int = 240) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "..."


def exit_code(results: list[UpstreamResult], strict: bool) -> int:
    if any(result.status == "check-failed" for result in results):
        return 1
    if strict and any(result.status == "update-available" for result in results):
        return 1
    return 0


class CheckError(Exception):
    """Expected upstream check failure."""


def run_self_tests() -> int:
    old_sha = "1" * 40
    latest_sha = "2" * 40
    snapshot_sha = "3" * 40

    with tempfile.TemporaryDirectory(prefix="agentos-upstream-check-") as temp_dir:
        root = Path(temp_dir)
        skill_root = root / "os/skills/example-skill"
        skill_root.mkdir(parents=True)
        (root / "os/skills/MANIFEST.md").write_text("# manifest\n", encoding="utf-8")
        (skill_root / "UPSTREAM.md").write_text(
            "\n".join(
                [
                    "# Upstream Provenance",
                    "",
                    "Source: `owner/repo`",
                    "Path: `skills/example/SKILL.md`",
                    f"Vendored ref: `{old_sha}`",
                    "Branch: `main`",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        metadata = discover_upstream_metadata(root)
        assert len(metadata) == 1
        item = metadata[0]
        assert item.skill == "example-skill"
        assert item.owner == "owner"
        assert item.repo == "repo"
        assert item.path == "skills/example/SKILL.md"
        assert item.vendored_ref == old_sha
        assert item.branch == "main"
        assert parse_github_source("https://github.com/mattpocock/skills") == ("mattpocock", "skills")
        assert exit_code([failed(item, "boom")], strict=False) == 1
        assert exit_code([result_fixture("update-available")], strict=False) == 0
        assert exit_code([result_fixture("update-available")], strict=True) == 1

        original_request_json = request_json
        try:
            globals()["request_json"] = fake_request_json(old_sha, latest_sha, snapshot_sha)
            update_result = check_upstream(
                metadata_fixture("needs-update", old_sha, path="skills/update/SKILL.md"),
                timeout=0.1,
            )
            assert update_result.status == "update-available"
            assert update_result.upstream_ref == latest_sha
            assert update_result.compare_url == f"https://github.com/owner/repo/compare/{old_sha}...{latest_sha}"

            current_result = check_upstream(
                metadata_fixture("current", latest_sha, path="skills/current/SKILL.md"),
                timeout=0.1,
            )
            assert current_result.status == "up-to-date"
            assert current_result.note == "vendored ref is the latest path-touching upstream commit"

            snapshot_result = check_upstream(
                metadata_fixture("snapshot", snapshot_sha, path="skills/snapshot/SKILL.md"),
                timeout=0.1,
            )
            assert snapshot_result.status == "up-to-date"
            assert "already contains" in snapshot_result.note

            directory_result = check_upstream(
                metadata_fixture("directory", old_sha, path="skills/directory/"),
                timeout=0.1,
            )
            assert directory_result.status == "update-available"
            assert "/tree/main/skills/directory/" in (directory_result.upstream_url or "")

            malformed_ref_result = check_upstream(
                metadata_fixture("bad-ref", "abc123", path="skills/update/SKILL.md"),
                timeout=0.1,
            )
            assert malformed_ref_result.status == "check-failed"
            assert "malformed Vendored ref" in malformed_ref_result.note

            malformed_latest_result = check_upstream(
                metadata_fixture("bad-latest", old_sha, path="skills/malformed-latest/SKILL.md"),
                timeout=0.1,
            )
            assert malformed_latest_result.status == "check-failed"
            assert "malformed commit SHA" in malformed_latest_result.note

            missing_path_result = check_upstream(
                metadata_fixture("missing-path", old_sha, path=None),
                timeout=0.1,
            )
            assert missing_path_result.status == "check-failed"
            assert missing_path_result.note == "missing Path"

            text_buffer = io.StringIO()
            with contextlib.redirect_stdout(text_buffer):
                print_text_report(root, [update_result])
            text_output = text_buffer.getvalue()
            assert "update-available" in text_output
            assert update_result.compare_url in text_output

            json_payload = json.loads(json.dumps([asdict(update_result)]))
            assert json_payload[0]["status"] == "update-available"
            assert json_payload[0]["compare_url"] == update_result.compare_url
        finally:
            globals()["request_json"] = original_request_json
    print("Self-tests passed.")
    return 0


def result_fixture(status: str) -> UpstreamResult:
    return UpstreamResult(
        skill="fixture",
        status=status,
        source="owner/repo",
        path="skills/fixture/SKILL.md",
        vendored_ref="1" * 40,
        upstream_ref="2" * 40,
        upstream_branch="main",
        compare_url=None,
        upstream_url=None,
        note="fixture",
    )


def metadata_fixture(skill: str, vendored_ref: str, path: str | None) -> UpstreamMetadata:
    return UpstreamMetadata(
        skill=skill,
        upstream_file=f"os/skills/{skill}/UPSTREAM.md",
        source="owner/repo",
        owner="owner",
        repo="repo",
        path=path,
        vendored_ref=vendored_ref,
        branch=None,
    )


def fake_request_json(old_sha: str, latest_sha: str, snapshot_sha: str):
    def _fake_request_json(url: str, timeout: float) -> Any:
        parsed = urllib.parse.urlparse(url)
        if parsed.path == "/repos/owner/repo":
            return {"default_branch": "main"}
        if parsed.path == "/repos/owner/repo/commits":
            query = urllib.parse.parse_qs(parsed.query)
            path = query.get("path", [""])[0]
            if path in {"skills/update/SKILL.md", "skills/directory/"}:
                return [{"sha": latest_sha}]
            if path == "skills/current/SKILL.md":
                return [{"sha": latest_sha}]
            if path == "skills/snapshot/SKILL.md":
                return [{"sha": latest_sha}]
            if path == "skills/malformed-latest/SKILL.md":
                return [{"sha": "abc123"}]
            return []
        compare_prefix = "/repos/owner/repo/compare/"
        if parsed.path.startswith(compare_prefix):
            base_head = parsed.path[len(compare_prefix) :]
            if base_head == f"{old_sha}...{latest_sha}":
                return {"status": "ahead"}
            if base_head == f"{snapshot_sha}...{latest_sha}":
                return {"status": "behind"}
            return {"status": "diverged"}
        raise CheckError(f"unexpected self-test URL: {url}")

    return _fake_request_json


if __name__ == "__main__":
    raise SystemExit(main())
