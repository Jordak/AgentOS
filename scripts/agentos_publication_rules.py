"""Shared publication rules for AgentOS validators and export tooling."""

from __future__ import annotations

from pathlib import Path


PUBLIC_EXPORT_ROOT_FILES = {
    ".gitignore",
    ".gitleaks-publication.toml",
    ".gitleaks.toml",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "CLAUDE.md",
    "DOMAIN.md",
    "README.md",
}

PUBLIC_EXPORT_ROOT_DIRS = {
    ".github",
    "docs",
    "os",
    "personal",
    "scripts",
}

PUBLIC_EXPORT_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "output",
    ".venv",
    "venv",
}

PERSONAL_OVERLAY_SKELETON_FILES = {
    "personal/.gitkeep",
    "personal/os/.gitkeep",
    "personal/os/agents/.gitkeep",
    "personal/os/automations/.gitkeep",
    "personal/os/connections/.gitkeep",
    "personal/os/context/.gitkeep",
    "personal/os/identity/.gitkeep",
    "personal/os/memory/.gitkeep",
    "personal/os/memory/compiled-truth/.gitkeep",
    "personal/os/memory/propagation-review/.gitkeep",
    "personal/os/memory/weekly-review/.gitkeep",
    "personal/os/playbook/.gitkeep",
    "personal/os/playbook/github-archive/.gitkeep",
    "personal/os/playbook/github-archive/issues/.gitkeep",
    "personal/os/playbook/github-archive/prs/.gitkeep",
    "personal/os/playbook/github-archive/settings/.gitkeep",
    "personal/os/skills/.gitkeep",
    "personal/os/verification/.gitkeep",
    "personal/os/verification/guidance-eval/.gitkeep",
    "personal/os/verification/guidance-eval/reports/.gitkeep",
    "personal/os/verification/markdown-audit/.gitkeep",
    "personal/os/verification/reports/.gitkeep",
}


def is_personal_overlay_skeleton_path(rel: Path) -> bool:
    return rel.as_posix() in PERSONAL_OVERLAY_SKELETON_FILES


def gitkeep_file_reason(path: Path) -> str | None:
    if path.name != ".gitkeep":
        return None
    if path.is_symlink():
        return "publishable .gitkeep must be an empty regular file, found symbolic link"
    if not path.is_file():
        return "publishable .gitkeep must be an empty regular file"
    try:
        size = path.stat().st_size
    except OSError as error:
        return f"could not inspect publishable .gitkeep: {error}"
    if size != 0:
        return "publishable .gitkeep must be empty"
    return None


def personal_overlay_skeleton_file_reason(path: Path) -> str | None:
    reason = gitkeep_file_reason(path)
    if reason is None:
        return None
    return reason.replace("publishable .gitkeep", "personal overlay skeleton .gitkeep")


CORE_LAYER_PUBLIC_SAFE_FILES = {
    "agents": {"AGENT_TEMPLATE.md", "README.md"},
    "automations": {"AUTOMATIONS.md", "EXAMPLES.md", "README.md"},
    "connections": {"README.md", "SAFETY_RULES.md"},
    "context": {"GLOSSARY.md", "README.md", "SOURCE_MAP.md"},
    "identity": {"README.md"},
    "memory": {"COMPACTION_RULES.md", "DECISIONS_LOG.md", "README.md"},
}

CORE_HIGH_RISK_NESTED_SAFE_FILES = {
    "os/memory/compiled-truth/TEMPLATE.md",
    "os/memory/propagation-review/QUEUE.template.md",
}

CORE_PERSONAL_ONLY_DIRS = {
    ("os", "memory", "compiled-truth"),
    ("os", "memory", "propagation-review"),
}

GENERATED_OUTPUT_PARTS = {"reports", "briefs", "weekly-review", "markdown-audit"}


def github_metadata_reason(rel: Path) -> str | None:
    if not rel.parts or rel.parts[0] != ".github":
        return None

    if rel.as_posix() == ".github/pull_request_template.md":
        return None

    if (
        len(rel.parts) == 3
        and rel.parts[1] == "workflows"
        and rel.suffix in {".yml", ".yaml"}
    ):
        return None

    return "is GitHub metadata outside the public-safe CI workflow allowlist"


def is_template_name(name: str) -> bool:
    return name.endswith(".template.md") or name == "TEMPLATE.md"


def is_core_example_path(rel: Path) -> bool:
    parts = rel.parts
    if len(parts) < 3:
        return False
    if len(parts) == 3:
        return "example" in rel.name.lower()

    first_nested = parts[2].lower()
    return first_nested == "examples" or first_nested.startswith(("example-", "example_"))


def is_core_high_risk_safe_file(rel: Path, safe_files: set[str]) -> bool:
    rel_text = rel.as_posix()
    if rel_text in CORE_HIGH_RISK_NESTED_SAFE_FILES:
        return True

    if len(rel.parts) == 3:
        return (
            rel.name == ".gitkeep"
            or rel.name in safe_files
            or is_template_name(rel.name)
            or is_core_example_path(rel)
        )

    return is_core_example_path(rel)


def live_personal_core_reason(rel: Path) -> str | None:
    parts = rel.parts
    if len(parts) < 2 or parts[0] != "os":
        return None

    if parts[:3] in CORE_PERSONAL_ONLY_DIRS:
        if rel.name == ".gitkeep" or is_template_name(rel.name) or "example" in rel.name.lower():
            return None
        return "is live personal state; use personal/os/ or a sanitized Core template/example"

    if len(parts) >= 3:
        layer = parts[1]
        safe_files = CORE_LAYER_PUBLIC_SAFE_FILES.get(layer)
        if safe_files is None:
            return None
        if is_core_high_risk_safe_file(rel, safe_files):
            return None
        return (
            f"is a live personal {layer} file or nested high-risk Core path; "
            f"use personal/os/{layer}/ or a sanctioned Core template/example"
        )

    return None


def generated_output_reason(rel: Path) -> str | None:
    if rel.parts and rel.parts[0] == "personal":
        return None
    if not any(part in GENERATED_OUTPUT_PARTS for part in rel.parts):
        return None
    if "example" in rel.name.lower() or ".template." in rel.name:
        return None
    return "is generated output; private generated outputs belong in personal/os/"


def publication_path_reason(rel: Path) -> str | None:
    return github_metadata_reason(rel) or live_personal_core_reason(rel) or generated_output_reason(rel)
