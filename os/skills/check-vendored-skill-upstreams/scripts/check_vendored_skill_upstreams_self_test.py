"""No-network self-tests for check_vendored_skill_upstreams.py."""

from __future__ import annotations

import json
import tempfile
import urllib.parse
from dataclasses import asdict
from pathlib import Path
from typing import Any

import check_vendored_skill_upstreams as checker


def run() -> int:
    old_sha = "1" * 40
    latest_sha = "2" * 40
    snapshot_sha = "3" * 40

    with tempfile.TemporaryDirectory(prefix="agentos-upstream-check-") as temp_dir:
        root = make_root(Path(temp_dir), old_sha)
        metadata = checker.discover_upstream_metadata(root)
        assert len(metadata) == 1
        assert_metadata(metadata[0], old_sha)
        assert_parse_github_source()
        assert_exit_codes(metadata[0])

        original_request_json = checker.request_json
        try:
            checker.request_json = fake_request_json(old_sha, latest_sha, snapshot_sha)
            results = run_cases(old_sha, latest_sha, snapshot_sha)
            assert_result(results["needs-update"], "update-available", latest_sha, "upstream path has changed")
            assert results["needs-update"].compare_url == checker.compare_url("owner", "repo", old_sha, latest_sha)
            assert_result(results["current"], "up-to-date", latest_sha, "latest path-touching")
            assert_result(results["snapshot"], "up-to-date", latest_sha, "already contains")
            assert_result(results["directory"], "update-available", latest_sha, "/tree/main/skills/directory/")
            assert_result(results["bad-ref"], "check-failed", None, "malformed Vendored ref")
            assert_result(results["bad-latest"], "check-failed", None, "malformed commit SHA")
            assert_result(results["missing-source"], "check-failed", None, "missing Source")
            assert_result(results["missing-path"], "check-failed", None, "missing Path")
            assert_result(results["malformed-github-source"], "check-failed", None, "malformed Source")
            assert_result(results["unsupported-source"], "manual-check-required", None, "check upstream freshness manually")
            assert_result(results["unsupported-missing-path"], "check-failed", None, "missing Path")
            assert_report_shapes(root, results["needs-update"])
        finally:
            checker.request_json = original_request_json

    print("Self-tests passed.")
    return 0


def make_root(root: Path, vendored_ref: str) -> Path:
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
                f"Vendored ref: `{vendored_ref}`",
                "Branch: `main`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root


def assert_metadata(item: checker.UpstreamMetadata, vendored_ref: str) -> None:
    assert item.skill == "example-skill"
    assert item.owner == "owner"
    assert item.repo == "repo"
    assert item.path == "skills/example/SKILL.md"
    assert item.vendored_ref == vendored_ref
    assert item.branch == "main"


def assert_parse_github_source() -> None:
    cases = [
        ("https://github.com/mattpocock/skills", ("mattpocock", "skills")),
        ("github.com/mattpocock/skills", ("mattpocock", "skills")),
        ("https://gitlab.com/acme/skill", (None, None)),
        ("gitlab.com/acme/skill", (None, None)),
    ]
    for source, expected in cases:
        assert checker.parse_github_source(source) == expected


def assert_exit_codes(item: checker.UpstreamMetadata) -> None:
    assert checker.exit_code([checker.failed(item, "boom")], strict=False) == 1
    assert checker.exit_code([checker.manual_check_required(item, "manual")], strict=False) == 0
    assert checker.exit_code([checker.manual_check_required(item, "manual")], strict=True) == 0
    assert checker.exit_code([result_fixture("update-available")], strict=False) == 0
    assert checker.exit_code([result_fixture("update-available")], strict=True) == 1


def run_cases(old_sha: str, latest_sha: str, snapshot_sha: str) -> dict[str, checker.UpstreamResult]:
    cases = [
        ("needs-update", old_sha, "skills/update/SKILL.md", "owner/repo", "owner", "repo"),
        ("current", latest_sha, "skills/current/SKILL.md", "owner/repo", "owner", "repo"),
        ("snapshot", snapshot_sha, "skills/snapshot/SKILL.md", "owner/repo", "owner", "repo"),
        ("directory", old_sha, "skills/directory/", "owner/repo", "owner", "repo"),
        ("bad-ref", "abc123", "skills/update/SKILL.md", "owner/repo", "owner", "repo"),
        ("bad-latest", old_sha, "skills/malformed-latest/SKILL.md", "owner/repo", "owner", "repo"),
        ("missing-source", old_sha, "skills/unsupported/SKILL.md", "", None, None),
        ("missing-path", old_sha, None, "owner/repo", "owner", "repo"),
        ("malformed-github-source", old_sha, "skills/unsupported/SKILL.md", "github.com/owner", None, None),
        ("unsupported-source", old_sha, "skills/unsupported/SKILL.md", "installed-global-skill", None, None),
        ("unsupported-missing-path", old_sha, None, "installed-global-skill", None, None),
    ]
    return {
        skill: checker.check_upstream(metadata_fixture(skill, ref, path, source, owner, repo), timeout=0.1)
        for skill, ref, path, source, owner, repo in cases
    }


def assert_result(
    result: checker.UpstreamResult,
    status: str,
    upstream_ref: str | None,
    expected_text: str,
) -> None:
    assert result.status == status
    assert result.upstream_ref == upstream_ref
    assert expected_text in ((result.note or "") + (result.upstream_url or ""))


def assert_report_shapes(root: Path, result: checker.UpstreamResult) -> None:
    text_output = checker.format_text_report(root, [result])
    assert "update-available" in text_output
    assert result.compare_url in text_output

    json_payload = json.loads(json.dumps([asdict(result)]))
    assert json_payload[0]["status"] == "update-available"
    assert json_payload[0]["compare_url"] == result.compare_url


def result_fixture(status: str) -> checker.UpstreamResult:
    return checker.UpstreamResult(
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


def metadata_fixture(
    skill: str,
    vendored_ref: str,
    path: str | None,
    source: str = "owner/repo",
    owner: str | None = "owner",
    repo: str | None = "repo",
) -> checker.UpstreamMetadata:
    return checker.UpstreamMetadata(
        skill=skill,
        source=source,
        owner=owner,
        repo=repo,
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
            path = urllib.parse.parse_qs(parsed.query).get("path", [""])[0]
            if path in {"skills/update/SKILL.md", "skills/directory/", "skills/current/SKILL.md", "skills/snapshot/SKILL.md"}:
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
        raise checker.CheckError(f"unexpected self-test URL: {url}")

    return _fake_request_json
