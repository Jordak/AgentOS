# Managed Path Resolution Interface

AgentOS trusted scripts should share path-safety behavior through public path-resolution modules, not through caller-composed path primitives.

The first public module is `scripts/path_resolution/managed.py`. It owns one policy-shaped interface: a managed path must stay under its declared root, must not traverse symbolic-link components, and must have the expected final kind when the caller asks for one.

The package may contain a private implementation layer, currently `scripts/path_resolution/_primitives.py`, for lexical absolute paths, relative containment, `lstat()` facts, and no-follow component walking. That private layer exists for implementation locality across path-resolution modules. It is not a caller interface.

Callers outside `scripts/path_resolution/` should import from the package or a public path-resolution module:

```python
from path_resolution.managed import managed_path_problem_text
```

They should not import or compose private primitives:

```python
from path_resolution._primitives import lexical_absolute
```

If future AgentOS scripts need a genuinely different path-resolution interface, add another public module beside `managed.py` and let both public modules depend on `_primitives.py` internally. Promote a primitive into a public interface only when the caller need is itself policy-shaped and the deletion test shows that keeping it private would force meaningful complexity to reappear across multiple callers.

This keeps the public modules deep. Callers ask for a managed-path safety result instead of learning the ordering and error modes of normalization, containment, parent walking, symlink rejection, and final-kind validation. Maintainers still get locality for the tricky filesystem mechanics because those mechanics live in one private implementation layer.

This also preserves local policy ownership. The Privacy Validator owns managed-tree and publication-precheck checks. The public export script owns publication-candidate safety. The mirror skill owns mirror discovery, sync, and prune policy. The path-resolution package reports path-safety facts; callers decide labels, FAIL versus WARN, and domain wording.

The rejected alternative was a general public helper module for primitives such as `lexical_absolute`, `is_relative_to`, and final-kind checks. That would reduce visible duplication, but it would make each caller compose the safety policy itself. Under the deletion test, such a module would be shallow: deleting it would mostly move small helper code around while leaving the important sequencing and safety decisions spread across callers.

Package integrity is owned by AgentOS validation and publication tooling, not by every caller. Scripts such as the mirror skill should import the public path-resolution module as a normal dependency and keep their local path checks focused on their own inputs and outputs. Until AgentOS has a first-class import convention for nested scripts, mirror-skills uses a small local import bridge; issue #51 tracks replacing that bridge with the repo-wide convention.

Readiness evidence: `docs/adr/0008-managed-path-resolution-interface.md`

Readiness verdict: Ready to Implement
