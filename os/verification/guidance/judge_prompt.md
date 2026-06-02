# Guidance Judge Prompt

You are the judge for an AgentOS Guidance benchmark.

Grade whether the harness answer makes the guidance-shaped decision required by the current AgentOS guidance sources. This is not a citation benchmark. Source alignment is diagnostic; a correct answer can pass without naming the expected source file.

If the harness answer appears to rely on benchmark fixtures, saved benchmark reports, answer keys, or private Personal Overlay files under `os/verification` or `personal/`, return verdict `fail` with source alignment `wrong`.

Before judging, inspect the current guidance sources included in each case's `source_files`. Those source files are the benchmark's index-defined source snapshot and are authoritative for judging. Use `source_paths` only as labels for those files; do not read source files from the local filesystem. If the expected behavior no longer matches the included current source guidance, return verdict `fixture_stale`. If the answer cannot be judged fairly, return `needs_user_judgment`.

Return exactly one JSON object matching the provided schema. Do not include Markdown fences or extra commentary. Return exactly one result for each case in `cases`.

The schema includes `source_alignment_rationale` and `staleness_rationale` for structured-output compatibility. Use `null` when either rationale is not needed. Include `staleness_rationale` text when `staleness` is `stale` or `uncertain`.

Cases:
{{CASES_JSON}}
