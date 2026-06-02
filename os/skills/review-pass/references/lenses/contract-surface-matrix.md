# Contract Surface Matrix Lens

Use this read-only inspection lens when the target changes skill behavior, workflow semantics, cross-skill ownership, safety rules, state or lifecycle behavior, prompt behavior, artifact schemas, validation policy, privacy boundaries, or filing rules.

Skip it for typo fixes, local prose cleanup, narrow examples, and implementation details that do not change a reusable contract.

## Reviewer Behavior

Check this lightweight matrix:

`Semantic | Owner | Inputs | Outputs | Prompt/Recovery | Ledger/Report | Privacy/Filing | Validation`

Use the matrix to find propagation gaps across affected surfaces:

- owning skill;
- caller or called skills;
- prompt templates;
- recovery prompts;
- packet or report schemas;
- manifest entry;
- source-routing or validator coverage when relevant;
- privacy and filing rules;
- current-machine adapters or exposure;
- final report guidance.

The matrix is not a design doc and does not authorize mutation. Report missing propagation as an issue family with the affected surfaces, not as isolated wording.

## Prompt Snippet

```md
Apply the Contract Surface Matrix as a conditional read-only inspection lens because this target changes skill, workflow, prompt, safety, lifecycle, schema, validation-policy, privacy, filing, or cross-skill ownership semantics. Check `Semantic | Owner | Inputs | Outputs | Prompt/Recovery | Ledger/Report | Privacy/Filing | Validation`, then report missing propagation as an issue family with affected surfaces rather than isolated wording. The matrix is not a design doc and does not authorize mutation.
```
