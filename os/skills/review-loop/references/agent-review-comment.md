# Agent Review Comment Guidance

The orchestrator, not individual reviewers or `review-pass`, posts PR comments. Use this structure when posting a consolidated comment is appropriate.

```md
Agent Review

Scope: <base..head, PR number, commit SHA>
Pass: <cycle number and mode: fresh | verification>
Review packet: <chat status, temp packet path, or none>
Reviewers: <aliases and optional lenses when supplied by review-pass>

Issue families:
1. [<issue-family-id>] Severity: <P0|P1|P2|P3> - <short title>
   Found by: <reviewer aliases and review-pass reviewer finding IDs>
   Evidence: <file:line or commit/diff reference>
   Issue family: <generalized failure mode or invariant>
   Related occurrences or sweep: <siblings found, search performed, or why none expected>
   Why it matters: <risk>
   Decision: <accepted | declined | fixed | unresolved>
   Suggested fix or fix commit: <concrete fix or commit SHA>

Declined issue families:
- [<issue-family-id>] <short rationale; include reviewer finding IDs only as provenance when useful>

Validation notes:
- <commands run or inspection limits>
```

If a pass has no accepted issue families, do not post a clean-pass comment unless the parent explicitly wants a final readiness comment.
