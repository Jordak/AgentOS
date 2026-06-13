# Review Loop Report Guidance

Use this when creating the final temporary HTML report for a review-loop run. The report should help the user understand what the loop found, how fixes converged, and whether the PR is ready without reading every comment chronologically.

## Required Structure

1. Executive summary:
   - PR link, final status, base, head branch, final head commit, merge state when known, commit count, review-pass count, reviewer count, issue-family count, terminal condition, unresolved ask-user blockers, user-declined/accepted-risk decisions, and residual risks.
   - For readiness-preflight blocked runs with no reviewer panel, include check-only mode, source reviewed, readiness verdict, missing consensus evidence, gate-skip state, label state, next repair owner, and confirmation that no reviewers spawned.
   - One short paragraph explaining the overall pattern the review loop uncovered.
   - A short readiness note with the final consolidated comment link when available.

2. Aggregated issue families:
   - Group findings by underlying failure mode rather than reviewer chronology.
   - For each family include: family name, failure mode, generalized rule, representative findings or comments, autopilot classification, autopilot rationale, complexity posture, smallest closing move or lazy-human decision, fix strategy, sibling sweep performed, validation signal, and related commit links.
   - For semantic contract changes, include the Contract Surface Matrix summary or explain why it was skipped as a local non-contractual fix.
   - Keep concrete examples, but make the family-level invariant visible.

3. Source-to-family crosswalk:
   - Map each reviewer finding, PR comment, PR review, or proposal to an issue family.
   - Include source links, review-pass packet references when available, summarized issue text, category, autopilot classification, and resolution.

4. Commit map by family:
   - Group representative commits under the issue family they fixed.
   - Explain what changed at the family level, not only at the individual commit level.

5. Review-loop convergence:
   - Show review-pass cycles, reviewer aliases, reviewer continuity mode and opaque handle availability for verification passes, auto-fix issue families, user-approved-fix ask-user decisions, unresolved ask-user blockers, user-declined/accepted-risk decisions, autopilot classification counts, complexity posture summaries, fix commits, and final adjudicated-clean status. Include source aliases when useful, but never expose opaque reviewer handles.
   - Name the final fresh review-pass packet and terminal condition.

6. Validation evidence:
   - List final validation commands and results.
   - Include environment caveats, skipped checks, or substitutes such as direct commands when a tool like `pre-commit` is unavailable.

7. Final state:
   - Repository, PR, base, head branch, final head SHA, GitHub state, ready marker, and final consolidated comment link.

## Commit Links

- Link every commit hash, short or long, to GitHub when the repository is hosted on GitHub.
- Prefer the label shown in the source material, usually the short hash, but use the full SHA in the URL: `https://github.com/<owner>/<repo>/commit/<full-sha>`.
- Derive `<owner>/<repo>` from the PR URL when available. Otherwise derive it from `git remote get-url origin`.
- Resolve short hashes with `git rev-parse <short>` when possible. If a hash cannot be resolved locally, leave it as code text and note that it could not be linked.
- Use commit links in cards, chips, tables, and prose wherever hashes appear. Do not leave bare linked URLs visible when a concise hash label is clearer.

## Issue-Family Style

- Write families as reusable lessons: "suffixless publishable files skipped privacy scans" is better than "`.gitignore` had a bug."
- Include a sibling-sweep note: what related files, paths, suffixes, validators, fixtures, or commands were checked after the representative issue was found.
- Distinguish fixed families, declined issue families, follow-up proposals, and residual risks.
- If an issue family led to several commits, tell the family story once and put the commit sequence in chips or a table.

## Efficiency Notes

- Include loop economics when relevant: elapsed time, panel cycles, commit count, accepted families, and where batching helped or failed.
- If the loop took unusually long, call out which families caused repeated rediscovery and how future loops should generalize them earlier.
